from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.core.auth import (
    DEMO_USERS,
    User,
    create_access_token,
    get_current_user,
)
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    """Authenticate with email and password, issuing a JWT access token."""
    if settings.environment.lower() in {"production", "prod"}:
        raise HTTPException(status_code=503, detail="Demo authentication is disabled in production")
    email_clean = payload.email.lower()
    user_record = DEMO_USERS.get(email_clean)

    if not user_record or user_record["password"] != payload.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = User(
        id=user_record["id"],
        email=user_record["email"],
        name=user_record["name"],
        role=user_record["role"],
    )

    token = create_access_token(user)
    return TokenResponse(access_token=token, token_type="bearer", user=user)


@router.get("/demo-users")
async def list_demo_users():
    """List non-sensitive synthetic demo personas; credentials are never returned."""
    if settings.environment.lower() in {"production", "prod"}:
        raise HTTPException(status_code=404, detail="Not found")
    return [
        {"role": user["role"], "name": user["name"], "email": user["email"]}
        for user in DEMO_USERS.values()
    ]


@router.post("/demo-session", response_model=TokenResponse)
async def create_demo_session():
    """
    Issues a server-controlled, scoped demo passenger identity JWT token
    for friction-free public portfolio exploration without requiring user credentials.
    """
    demo_rec = DEMO_USERS["passenger@qahub.io"]
    user = User(
        id=demo_rec["id"],
        email=demo_rec["email"],
        name=demo_rec["name"],
        role=demo_rec["role"],
    )
    token = create_access_token(user)
    return TokenResponse(access_token=token, token_type="bearer", user=user)


@router.get("/me", response_model=User)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Retrieve currently authenticated user profile and assigned role."""
    return current_user

