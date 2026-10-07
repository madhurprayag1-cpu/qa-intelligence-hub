import time
import uuid
import logging
from collections import deque
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("qahub.observability")


class RuntimeMetrics:
    """Best-effort per-process request telemetry for production diagnostics.

    Serverless instances are ephemeral, so these metrics are explicitly scoped to
    the current process and must not be treated as durable monitoring history.
    """

    started_at = datetime.now(timezone.utc).isoformat()
    total_requests = 0
    error_requests = 0
    latencies_ms = deque(maxlen=500)

    @classmethod
    def record(cls, duration_ms: float, status_code: int) -> None:
        cls.total_requests += 1
        if status_code >= 500:
            cls.error_requests += 1
        cls.latencies_ms.append(float(duration_ms))

    @classmethod
    def snapshot(cls) -> dict:
        values = sorted(cls.latencies_ms)
        if values:
            idx = max(0, min(len(values) - 1, round(0.95 * (len(values) - 1))))
            p95 = round(values[idx], 2)
            avg = round(sum(values) / len(values), 2)
        else:
            p95 = avg = 0.0
        return {
            "scope": "process_instance",
            "started_at": cls.started_at,
            "total_requests": cls.total_requests,
            "error_requests_5xx": cls.error_requests,
            "error_rate": round(cls.error_requests / cls.total_requests, 4) if cls.total_requests else 0.0,
            "latency_sample_size": len(values),
            "avg_latency_ms": avg,
            "p95_latency_ms": p95,
        }


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
        RuntimeMetrics.record(duration_ms, response.status_code)

        return response
