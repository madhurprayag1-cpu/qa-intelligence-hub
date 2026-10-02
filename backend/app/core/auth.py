import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, List, Optional
from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from app.core.config import settings

def _jwt_secret() -> str:
    configured = os.getenv("JWT_SECRET", settings.jwt_secret)
    if settings.environment.lower() in {"production", "prod"}:
        if len(configured) < 32 or configured == "change-me":
            raise RuntimeError("JWT_SECRET must contain at least 32 characters in production")
        return configured
    # Local-only ephemeral fallback; configure JWT_SECRET for stable development tokens.
    return configured or secrets.token_urlsafe(48)


JWT_SECRET = _jwt_secret()
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRY_SECONDS = 3600 * 24  # 24 hours

security_bearer = HTTPBearer(auto_error=False)


class User(BaseModel):
    id: int
    email: str
    name: str
    role: str  # passenger, qa_engineer, release_manager, admin


# Synthetic deterministic demo users for portfolio testing
DEMO_USERS: Dict[str, Dict[str, Any]] = {
    "passenger@qahub.io": {
        "id": 101,
        "email": "passenger@qahub.io",
        "name": "Alice Passenger",
        "password": "passenger123",
        "role": "passenger",
    },
    "qa@qahub.io": {
        "id": 201,
        "email": "qa@qahub.io",
        "name": "Bob QE",
        "password": "qa123",
        "role": "qa_engineer",
    },
    "release@qahub.io": {
        "id": 301,
        "email": "release@qahub.io",
        "name": "Carol Release Manager",
        "password": "release123",
        "role": "release_manager",
    },
    "admin@qahub.io": {
        "id": 401,
        "email": "admin@qahub.io",
        "name": "Dave Administrator",
        "password": "admin123",
        "role": "admin",
    },
}


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_decode(data_str: str) -> bytes:
    padding = 4 - (len(data_str) % 4)
    if padding and padding < 4:
        data_str += "=" * padding
    return base64.urlsafe_b64decode(data_str.encode("utf-8"))


def create_access_token(user: User, custom_claims: Optional[Dict[str, Any]] = None) -> str:
    """Generates a standard HS256 signed JSON Web Token."""
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "iat": now,
        "exp": now + TOKEN_EXPIRY_SECONDS,
    }
    if custom_claims:
        payload.update(custom_claims)

    header_b64 = _b64_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Validates signature and expiration of an access token."""
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()

    try:
        actual_sig = _b64_decode(sig_b64)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature encoding",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature or tampered credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = json.loads(_b64_decode(payload_b64).decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if "exp" not in payload or payload["exp"] < int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> Optional[User]:
    """Extracts authenticated user if token is supplied, otherwise returns None."""
    if not credentials or not credentials.credentials:
        return None

    payload = decode_access_token(credentials.credentials)
    return _user_from_payload(payload)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> User:
    """Enforces valid authentication token presence."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    return _user_from_payload(payload)


async def get_current_domain_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    x_user_role: Optional[str] = Header(default=None, alias="X-User-Role"),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
) -> User:
    """
    Resolves the active user context for multi-domain SUT operations:
    1. If Bearer token is provided: decodes and verifies token. (Raises 401 if invalid/expired).
    2. If no Bearer token and X-User-Role in {'unauthorized', 'guest', 'foreign_user'}: returns synthetic unauthorized identity.
    3. If no Bearer token: defaults to standard synthetic demo identity (passenger@qahub.io, id=101)
       for backwards compatibility with hermetic/in-memory test executions.
    """
    if credentials and credentials.credentials:
        payload = decode_access_token(credentials.credentials)
        return _user_from_payload(payload)

    if x_user_role in {"unauthorized", "guest", "foreign_user"}:
        return User(
            id=9999,
            email=f"{x_user_role}@qahub.io",
            name=f"Demo {x_user_role.capitalize()}",
            role=x_user_role,
        )

    demo_rec = DEMO_USERS["passenger@qahub.io"]
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else demo_rec["id"]
    role = x_user_role if x_user_role and x_user_role not in {"account_owner", "practitioner_assigned"} else demo_rec["role"]
    if x_user_role == "practitioner_assigned":
        role = "practitioner"

    return User(
        id=user_id,
        email=demo_rec["email"],
        name=demo_rec["name"],
        role=role,
    )


def _user_from_payload(payload: Dict[str, Any]) -> User:
    try:
        return User(
            id=int(payload["sub"]),
            email=str(payload["email"]),
            name=str(payload["name"]),
            role=str(payload["role"]),
        )
    except (KeyError, TypeError, ValueError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token claims",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


def require_roles(allowed_roles: List[str]):
    """Role-based access control (RBAC) dependency factory."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Insufficient privileges. Required one of: {allowed_roles}, your role: '{current_user.role}'",
            )
        return current_user

    return role_checker
