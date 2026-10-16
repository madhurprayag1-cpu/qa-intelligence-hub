"""Fail-closed safety boundary for the public production demo.

The production demo is intentionally browseable without a login wall. Only a
small, reviewed allowlist of non-persistent POST operations is available.
State-changing and sensitive data endpoints are denied at the application edge.
The in-process limiter is defense-in-depth; use Vercel Firewall for distributed
edge rate limiting across serverless instances.
"""
from collections import defaultdict, deque
import re
import threading
import time

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings


# Public POSTs are intentionally limited to computation/query operations that
# do not write database records or change shared application state.
PUBLIC_READ_ONLY_POST_PATHS = frozenset(
    {
        "/auth/demo-session",
        "/ai/evaluate/groundedness",
        "/ai/rag/query",
        "/ai/rca",
        "/qa/regression/impact",
        "/qa/reporting/release-report",
        "/qa/self-heal/selector",
        "/healthcare/dosage/calculate",
        "/fintech/kyc/verify",
        "/fintech/fraud/evaluate",
        "/fintech/exchange/calculate",
        "/ecommerce/cart/validate",
        "/telecom/cdr/rate",
    }
)

# Deny public reads that could expose user, financial, clinical, or operational
# records. Public catalogs and synthetic reference data remain accessible.
_SENSITIVE_GET_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"^/bookings/(?:[0-9]+|reference/.+)$",
        r"^/payments/[0-9]+$",
        r"^/healthcare/(?:patients|observations|appointments)(?:/.*)?$",
        r"^/fintech/(?:accounts|transactions)(?:/.*)?$",
        r"^/ecommerce/orders(?:/.*)?$",
        r"^/telecom/subscribers(?:/.*)?$",
        r"^/qa/production/incidents(?:/.*)?$",
        r"^/qa/requirements/[^/]+(?:/test-plan)?$",
        r"^/qa/runtime/metrics$",
    )
)

_BLOCKED_HEADERS = {b"x-simulate-defect", b"x-user-role", b"x-user-id"}


class ProductionSafetyMiddleware(BaseHTTPMiddleware):
    """Apply public-demo access policy and per-process request throttling."""

    WINDOW_SECONDS = 60.0
    MAX_REQUESTS_PER_WINDOW = 30
    _windows: dict[str, deque[float]] = defaultdict(deque)
    _lock = threading.Lock()

    @classmethod
    def reset_rate_limits(cls) -> None:
        """Clear limiter state; intended for deterministic automated tests."""
        with cls._lock:
            cls._windows.clear()

    @staticmethod
    def _secure_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response

    @classmethod
    def _rate_limited(cls, request: Request, path: str) -> bool:
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{path}"
        now = time.monotonic()
        with cls._lock:
            window = cls._windows[key]
            while window and now - window[0] >= cls.WINDOW_SECONDS:
                window.popleft()
            if len(window) >= cls.MAX_REQUESTS_PER_WINDOW:
                return True
            window.append(now)
            return False

    async def dispatch(self, request: Request, call_next):
        is_production = settings.environment.strip().lower() in {"production", "prod"}
        if not is_production:
            return self._secure_headers(await call_next(request))

        method = request.method.upper()
        path = request.url.path

        # Never honor test-only defect or caller-supplied role headers in prod.
        request.scope["headers"] = [
            (name, value)
            for name, value in request.scope.get("headers", [])
            if name.lower() not in _BLOCKED_HEADERS
        ]

        if method == "GET" and any(pattern.fullmatch(path) for pattern in _SENSITIVE_GET_PATTERNS):
            return self._secure_headers(
                JSONResponse(status_code=404, content={"detail": "Not found"})
            )

        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            if method != "POST" or path not in PUBLIC_READ_ONLY_POST_PATHS:
                return self._secure_headers(
                    JSONResponse(
                        status_code=403,
                        content={"detail": "This operation is disabled in the public production demo."},
                    )
                )
            if self._rate_limited(request, path):
                return self._secure_headers(
                    JSONResponse(
                        status_code=429,
                        content={"detail": "Request limit exceeded. Please retry later."},
                        headers={"Retry-After": str(int(self.WINDOW_SECONDS))},
                    )
                )

        return self._secure_headers(await call_next(request))
