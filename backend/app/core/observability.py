import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("qahub.observability")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Observability & Correlation Tracking Middleware (AGENTS.md Section 22).
    - Ensures every HTTP request has an observable X-Request-ID.
    - Measures end-to-end latency in milliseconds and attaches X-Response-Time-Ms.
    - Logs structured request metadata without exposing credentials or secrets.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()

        # Propagate upstream correlation ID or generate new unique request ID
        request_id = (
            request.headers.get("x-request-id")
            or request.headers.get("x-correlation-id")
            or f"req_{uuid.uuid4().hex[:12]}"
        )

        # Store on request state for downstream handlers and agent traces
        request.state.request_id = request_id

        # Execute downstream pipeline
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "Unhandled request failure",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(exc),
                },
            )
            raise exc

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Attach observability headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)

        return response
