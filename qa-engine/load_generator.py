"""High-Concurrency Load & Stress Testing Generator.

Adheres to AGENTS.md Section 5, 22, and 25:
- Validates system scalability, latency degradation, and throughput under concurrent load
- Collects statistical latency distributions (p50, p90, p95, p99)
- Analyzes error rates and HTTP response code distributions
"""

import asyncio
import math
import statistics
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional
import httpx


@dataclass
class LoadBenchmarkResult:
    total_requests: int
    successful_requests: int
    failed_requests: int
    duration_seconds: float
    requests_per_second: float
    p50_latency_ms: float
    p90_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    avg_latency_ms: float
    status_codes: Dict[int, int] = field(default_factory=dict)
    error_summary: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


async def execute_load_test(
    request_fn: Callable[[], Any],
    total_requests: int = 100,
    concurrency: int = 10,
) -> LoadBenchmarkResult:
    """
    Executes a high-concurrency benchmark by distributing `total_requests`
    across `concurrency` asynchronous workers.
    """
    latencies_ms: List[float] = []
    status_codes: Dict[int, int] = {}
    error_summary: Dict[str, int] = {}
    queue: asyncio.Queue[int] = asyncio.Queue()

    for i in range(total_requests):
        queue.put_nowait(i)

    start_global = time.perf_counter()

    async def worker():
        while not queue.empty():
            try:
                _ = queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            t0 = time.perf_counter()
            try:
                res = await request_fn()
                elapsed = (time.perf_counter() - t0) * 1000.0
                latencies_ms.append(elapsed)

                # Track status code
                code = getattr(res, "status_code", 200)
                status_codes[code] = status_codes.get(code, 0) + 1
            except Exception as exc:
                elapsed = (time.perf_counter() - t0) * 1000.0
                latencies_ms.append(elapsed)
                err_type = type(exc).__name__
                error_summary[err_type] = error_summary.get(err_type, 0) + 1
            finally:
                queue.task_done()

    workers = [asyncio.create_task(worker()) for _ in range(min(concurrency, total_requests))]
    await asyncio.gather(*workers)
    total_duration = time.perf_counter() - start_global

    if not latencies_ms:
        latencies_ms = [0.0]

    latencies_sorted = sorted(latencies_ms)
    n = len(latencies_sorted)

    def percentile(p: float) -> float:
        idx = min(int(math.ceil(p * n)) - 1, n - 1)
        return latencies_sorted[max(0, idx)]

    successful = sum(count for code, count in status_codes.items() if 200 <= code < 400)
    failed = total_requests - successful

    p50 = percentile(0.50)
    p90 = percentile(0.90)
    p95 = percentile(0.95)
    p99 = percentile(0.99)
    min_lat = latencies_sorted[0]
    max_lat = latencies_sorted[-1]
    avg_lat = statistics.mean(latencies_sorted)
    rps = total_requests / total_duration if total_duration > 0 else 0.0

    return LoadBenchmarkResult(
        total_requests=total_requests,
        successful_requests=successful,
        failed_requests=failed,
        duration_seconds=round(total_duration, 3),
        requests_per_second=round(rps, 2),
        p50_latency_ms=round(p50, 2),
        p90_latency_ms=round(p90, 2),
        p95_latency_ms=round(p95, 2),
        p99_latency_ms=round(p99, 2),
        min_latency_ms=round(min_lat, 2),
        max_latency_ms=round(max_lat, 2),
        avg_latency_ms=round(avg_lat, 2),
        status_codes=status_codes,
        error_summary=error_summary,
    )
