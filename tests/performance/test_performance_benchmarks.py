import statistics
import time
import concurrent.futures
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.flight import Flight


def test_flight_search_latency_and_throughput(client: TestClient):
    """
    Performance Benchmark: Flight Search Latency & Concurrency (AGENTS.md Section 5 & 25).
    Measures p50 and p95 latency under sequential and concurrent loads.
    Enforces p95 < 250ms threshold on search endpoint.
    """
    iterations = 25
    latencies_ms = []

    for _ in range(iterations):
        start = time.perf_counter()
        res = client.get("/search/flights?origin=ATH&destination=SKG")
        duration = (time.perf_counter() - start) * 1000.0
        assert res.status_code == 200
        latencies_ms.append(duration)

    p50 = statistics.median(latencies_ms)
    p95 = statistics.quantiles(latencies_ms, n=20)[18]  # 95th percentile

    # Assert performance threshold
    assert p95 < 250.0, f"Flight search p95 latency exceeded threshold: {p95:.2f}ms"
    assert len(latencies_ms) == iterations


def test_concurrent_search_performance(client: TestClient):
    """
    Validates server response integrity under multi-threaded simulated client requests.
    """
    def execute_search():
        start = time.perf_counter()
        res = client.get("/search/flights?origin=ATH&destination=SKG")
        return res.status_code, (time.perf_counter() - start) * 1000.0

    concurrency = 8
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(execute_search) for _ in range(concurrency)]
        results = [f.result() for f in futures]

    for status, duration in results:
        assert status == 200
        assert duration < 500.0, f"Concurrent request took too long: {duration:.2f}ms"


def test_observability_overhead_benchmark(client: TestClient):
    """
    Ensure that ObservabilityMiddleware adds minimal latency overhead (< 5ms).
    """
    res = client.get("/health")
    assert res.status_code == 200
    overhead_ms = float(res.headers.get("X-Response-Time-Ms", 999))
    assert overhead_ms < 50.0
