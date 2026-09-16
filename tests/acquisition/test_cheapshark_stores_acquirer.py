from datetime import UTC, datetime

from market_pipeline.acquisition.cheapshark_stores_acquirer import (
    CheapSharkStoresAcquirer,
)
from market_pipeline.acquisition.http_transport import (
    HttpResponseSnapshot,
    HttpTransportResult,
)
from market_pipeline.acquisition.models import (
    AcquisitionFailure,
    AcquisitionFailureOutcome,
    AcquisitionMethod,
    AcquisitionSuccess,
)

STORES_ENDPOINT = "https://www.cheapshark.com/api/1.0/stores"
USER_AGENT = "MarketPipelineTest/0.1"
STARTED_AT = datetime(2026, 9, 15, 16, 28, tzinfo=UTC)
FINISHED_AT = datetime(2026, 9, 15, 16, 29, tzinfo=UTC)


def _make_acquisition_failure(**overrides: object) -> AcquisitionFailure:
    data = {
        "requested_url": "https://www.cheapshark.com/api/1.0/stores",
        "method": AcquisitionMethod.HTTP,
        "started_at": STARTED_AT,
        "finished_at": FINISHED_AT,
        "outcome": AcquisitionFailureOutcome.NETWORK_ERROR,
        "diagnostic_message": "HTTP connection failed",
        "final_url": None,
        "status_code": None,
        "content_type": None,
        "retry_after_seconds": None,
    }
    data.update(overrides)
    return AcquisitionFailure(**data)


def _make_http_snapshot(**overrides: object) -> HttpResponseSnapshot:
    data = {
        "requested_url": "https://www.cheapshark.com/api/1.0/stores",
        "started_at": STARTED_AT,
        "finished_at": FINISHED_AT,
        "final_url": "https://www.cheapshark.com/api/1.0/stores",
        "status_code": 200,
        "headers": {"Content-Type": "application/json"},
        "content": '[{"storeID": "1", "storeName": "Steam"}]',
    }
    data.update(overrides)
    return HttpResponseSnapshot(**data)


class FakeTransport:
    def __init__(self, http_result: HttpTransportResult) -> None:
        self.http_result = http_result

    def get(
        self,
        url,
        *,
        params=None,
        headers,
    ) -> HttpTransportResult:
        self.called_url = url
        self.called_params = params
        self.called_headers = headers
        return self.http_result


def test_cheapshark_stores_acquirer_returns_acquisition_success() -> None:
    user_agent = USER_AGENT

    http_result = HttpResponseSnapshot(
        requested_url="https://www.cheapshark.com/api/1.0/stores",
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        final_url="https://www.cheapshark.com/api/1.0/stores",
        status_code=200,
        headers={"Content-Type": "application/json"},
        content='[{"storeID": "1", "storeName": "Steam"}]',
    )

    fake_transport = FakeTransport(http_result)

    acquirer = CheapSharkStoresAcquirer(
        fake_transport,
        user_agent,
    )

    result = acquirer.acquire()

    assert fake_transport.called_url == STORES_ENDPOINT
    assert fake_transport.called_params is None
    assert fake_transport.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }

    assert isinstance(result, AcquisitionSuccess)
    assert result.requested_url == STORES_ENDPOINT
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.final_url == STORES_ENDPOINT
    assert result.status_code == 200
    assert result.content_type == "application/json"
    assert result.content == '[{"storeID": "1", "storeName": "Steam"}]'


def test_cheapshark_stores_acquirer_returns_transport_failure_unchanged() -> None:
    user_agent = USER_AGENT

    failure = AcquisitionFailure(
        requested_url="https://www.cheapshark.com/api/1.0/stores",
        method=AcquisitionMethod.HTTP,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        outcome=AcquisitionFailureOutcome.NETWORK_ERROR,
        diagnostic_message="HTTP connection failed",
        final_url=None,
        status_code=None,
        content_type=None,
    )

    fake_transport = FakeTransport(failure)

    acquirer = CheapSharkStoresAcquirer(
        fake_transport,
        user_agent,
    )

    result = acquirer.acquire()
    assert fake_transport.called_url == STORES_ENDPOINT
    assert fake_transport.called_params is None
    assert fake_transport.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert result is failure


def test_cheapshark_stores_acquirer_returns_http_failure_for_non_success_status() -> None:
    user_agent = USER_AGENT

    http_result = _make_http_snapshot(
        status_code=503,
        content='{"error": "Service unavailable"}',
    )

    fake_transport = FakeTransport(http_result)

    acquirer = CheapSharkStoresAcquirer(
        fake_transport,
        user_agent,
    )
    expected_failure = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.HTTP_ERROR,
        diagnostic_message="HTTP request returned status 503",
        final_url=STORES_ENDPOINT,
        status_code=503,
        content_type=http_result.headers.get("Content-Type"),
    )
    actual_failure = acquirer.acquire()

    assert actual_failure == expected_failure


def test_cheapshark_stores_acquirer_rejects_missing_content_type() -> None:
    user_agent = USER_AGENT

    http_result = _make_http_snapshot(headers={})

    fake_transport = FakeTransport(http_result)

    expected_failure = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
        diagnostic_message="Missing Content-Type header",
        final_url=STORES_ENDPOINT,
        status_code=200,
        content_type=None,
    )

    acquirer = CheapSharkStoresAcquirer(
        fake_transport,
        user_agent,
    )

    actual_failure = acquirer.acquire()

    assert actual_failure == expected_failure


def test_cheapshark_stores_acquirer_rejects_unsupported_content_type() -> None:
    user_agent = USER_AGENT

    http_result = _make_http_snapshot(
        headers={"Content-Type": "text/html"},
    )

    fake_transport = FakeTransport(http_result)

    content_type = http_result.headers.get("Content-Type")
    expected_failure = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
        diagnostic_message=f"Unsupported Content-Type: {content_type}",
        final_url=STORES_ENDPOINT,
        status_code=200,
        content_type=content_type,
    )

    acquirer = CheapSharkStoresAcquirer(
        fake_transport,
        user_agent,
    )

    actual_failure = acquirer.acquire()

    assert actual_failure == expected_failure


def test_cheapshark_stores_acquirer_accepts_json_content_type_with_charset() -> None:
    http_result = _make_http_snapshot(
        headers={"Content-Type": "application/json; charset=UTF-8"},
    )
    fake_transport = FakeTransport(http_result)
    acquirer = CheapSharkStoresAcquirer(
        fake_transport,
        USER_AGENT,
    )

    result = acquirer.acquire()

    assert isinstance(result, AcquisitionSuccess)
    assert result.requested_url == STORES_ENDPOINT
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.final_url == STORES_ENDPOINT
    assert result.status_code == 200
    assert result.content_type == "application/json; charset=UTF-8"
    assert result.content == '[{"storeID": "1", "storeName": "Steam"}]'


def test_cheapshark_stores_acquirer_rejects_blank_body() -> None:
    user_agent = USER_AGENT

    http_result = _make_http_snapshot(content=" ")

    fake_transport = FakeTransport(http_result)

    content_type = http_result.headers.get("Content-Type")
    expected_failure = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
        diagnostic_message="HTTP response body is blank",
        final_url=STORES_ENDPOINT,
        status_code=200,
        content_type=content_type,
    )

    acquirer = CheapSharkStoresAcquirer(
        fake_transport,
        user_agent,
    )

    actual_failure = acquirer.acquire()

    assert actual_failure == expected_failure


def test_cheapshark_stores_acquirer_rejects_invalid_json() -> None:
    http_result = _make_http_snapshot(
        content='[{"storeID": "1", "storeName": "Steam"}',
    )
    fake_transport = FakeTransport(http_result)
    content_type = http_result.headers.get("Content-Type")
    expected_failure = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
        diagnostic_message="HTTP response body is not valid JSON",
        final_url=STORES_ENDPOINT,
        status_code=200,
        content_type=content_type,
    )
    acquirer = CheapSharkStoresAcquirer(
        fake_transport,
        USER_AGENT,
    )

    actual_failure = acquirer.acquire()

    assert actual_failure == expected_failure


def test_cheapshark_stores_acquirer_normalizes_numeric_retry_after_for_429() -> None:
    user_agent = USER_AGENT

    http_result = _make_http_snapshot(
        status_code=429,
        headers={
            "Content-Type": "application/json",
            "Retry-After": "30",
        },
        content='{"error": "too many requests"}',
    )

    fake_transport = FakeTransport(http_result)

    content_type = http_result.headers.get("Content-Type")
    expected_failure = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.HTTP_ERROR,
        diagnostic_message="HTTP request returned status 429",
        final_url=STORES_ENDPOINT,
        status_code=429,
        content_type=content_type,
        retry_after_seconds=30,
    )

    acquirer = CheapSharkStoresAcquirer(
        fake_transport,
        user_agent,
    )

    actual_failure = acquirer.acquire()

    assert actual_failure == expected_failure


def test_cheapshark_stores_acquirer_handles_missing_retry_after_for_429() -> None:
    user_agent = USER_AGENT

    http_result = _make_http_snapshot(
        status_code=429,
        content='{"error": "too many requests"}',
    )

    fake_transport = FakeTransport(http_result)

    content_type = http_result.headers.get("Content-Type")
    expected_failure = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.HTTP_ERROR,
        diagnostic_message="HTTP request returned status 429",
        final_url=STORES_ENDPOINT,
        status_code=429,
        content_type=content_type,
        retry_after_seconds=None,
    )
    acquirer = CheapSharkStoresAcquirer(
        fake_transport,
        user_agent,
    )

    actual_failure = acquirer.acquire()

    assert actual_failure == expected_failure


def test_cheapshark_stores_acquirer_ignores_non_numeric_retry_after_for_429() -> None:
    user_agent = USER_AGENT

    http_result = _make_http_snapshot(
        status_code=429,
        headers={
            "Content-Type": "application/json",
            "Retry-After": "invalid",
        },
        content='{"error": "too many requests"}',
    )

    fake_transport = FakeTransport(http_result)

    content_type = http_result.headers.get("Content-Type")
    expected_failure = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.HTTP_ERROR,
        diagnostic_message="HTTP request returned status 429",
        final_url=STORES_ENDPOINT,
        status_code=429,
        content_type=content_type,
        retry_after_seconds=None,
    )
    acquirer = CheapSharkStoresAcquirer(
        fake_transport,
        user_agent,
    )

    actual_failure = acquirer.acquire()

    assert actual_failure == expected_failure
