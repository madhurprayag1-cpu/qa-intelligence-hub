import asyncio
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from load_generator import execute_load_test


@pytest.mark.anyio
async def test_load_generator_statistical_metrics():
    """
    Validates statistical percentile calculation, throughput, and error aggregation.
    """
    counter = 0

    async def mock_endpoint():
        nonlocal counter
        counter += 1
        await asyncio.sleep(0.001)
        class MockResp:
            status_code = 200
        return MockResp()

    res = await execute_load_test(
        request_fn=mock_endpoint,
        total_requests=40,
        concurrency=8,
    )

    assert res.total_requests == 40
    assert res.successful_requests == 40
    assert res.failed_requests == 0
    assert res.requests_per_second > 0
    assert res.min_latency_ms <= res.p50_latency_ms <= res.p95_latency_ms <= res.p99_latency_ms <= res.max_latency_ms
    assert res.status_codes.get(200) == 40


@pytest.mark.anyio
async def test_flight_search_stress_simulation(client: TestClient):
    """
    Validates server throughput and sub-100ms p95 latency under concurrent flight search queries.
    """
    async def run_search():
        loop = asyncio.get_running_loop()
        travel_date = (date.today() + timedelta(days=1)).isoformat()
        resp = await loop.run_in_executor(
            None,
            lambda: client.get(
                f"/search/flights?origin=ATH&destination=SKG&travel_date={travel_date}"
            ),
        )
        return resp

    res = await execute_load_test(
        request_fn=run_search,
        total_requests=30,
        concurrency=6,
    )

    assert res.total_requests == 30
    assert res.successful_requests == 30
    assert res.p95_latency_ms < 200.0, f"Concurrent flight search p95 too high: {res.p95_latency_ms}ms"
    assert res.status_codes.get(200) == 30


@pytest.mark.anyio
async def test_load_generator_error_resilience():
    """
    Validates that client-side and server-side errors are cleanly aggregated into error_summary.
    """
    async def failing_endpoint():
        class MockResp:
            status_code = 503
        return MockResp()

    res = await execute_load_test(
        request_fn=failing_endpoint,
        total_requests=20,
        concurrency=4,
    )

    assert res.total_requests == 20
    assert res.successful_requests == 0
    assert res.failed_requests == 20
    assert res.status_codes.get(503) == 20
