from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from market_pipeline.acquisition.cheapshark_game_search_acquirer import (
    CheapSharkGameSearchAcquirer,
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

QUERY = "Batman"
GAMES_ENDPOINT = "https://www.cheapshark.com/api/1.0/games"
USER_AGENT = "MarketPipelineTest/0.1"
WARSAW = ZoneInfo("Europe/Warsaw")
STARTED_AT = datetime(
    2026, 9, 24, 10, 2, tzinfo=WARSAW,
)
FINISHED_AT = datetime(
    2026, 9, 24, 10, 2, tzinfo=WARSAW,
)


def _make_http_snapshot(**overrides: object) -> HttpResponseSnapshot:
    data = {
        "requested_url": "https://www.cheapshark.com/api/1.0/games?title=Batman",
        "started_at": STARTED_AT,
        "finished_at": FINISHED_AT,
        "final_url": "https://www.cheapshark.com/api/1.0/games?title=Batman",
        "status_code": 200,
        "headers": {"Content-Type": "application/json"},
        "content": '[{"gameID": "1", "external": "Batman"}]',
    }
    data.update(overrides)
    return HttpResponseSnapshot(**data)


def _make_acquisition_failure(**overrides: object) -> AcquisitionFailure:
    data = {
        "requested_url": "https://www.cheapshark.com/api/1.0/games?title=Batman",
        "method": AcquisitionMethod.HTTP,
        "started_at": STARTED_AT,
        "finished_at": FINISHED_AT,
        "outcome": AcquisitionFailureOutcome.HTTP_ERROR,
        "diagnostic_message": "HTTP request returned status 403",
        "status_code": 403,
        "final_url": "https://www.cheapshark.com/api/1.0/games?title=Batman",
        "content_type": "application/json",
        "retry_after_seconds": None,
    }
    data.update(overrides)
    return AcquisitionFailure(**data)


class FakeTransport:
    def __init__(self, result: HttpTransportResult) -> None:
        self.result = result

    def get(
        self,
        url,
        *,
        params,
        headers,
    ) -> HttpTransportResult:
        self.called_url = url
        self.called_params = params
        self.called_headers = headers
        return self.result


def test_cheapshark_game_search_acquirer_returns_acquisition_success() -> None:
    query = "Batman"
    content = (
        '['
        '{"gameID": "1", "external": "Batman"},'
        '{"gameID": "2", "external": "LEGO Batman"}'
        ']'
    )
    snapshot = HttpResponseSnapshot(
        requested_url="https://www.cheapshark.com/api/1.0/games?title=Batman",
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        final_url="https://www.cheapshark.com/api/1.0/games?title=Batman",
        status_code=200,
        headers={"Content-Type": "application/json"},
        content=content,
    )

    fake_transport = FakeTransport(snapshot)

    acquirer = CheapSharkGameSearchAcquirer(
        fake_transport,
        user_agent=USER_AGENT,
    )

    result = acquirer.acquire(query)

    assert fake_transport.called_url == GAMES_ENDPOINT
    assert fake_transport.called_params == {"title": "Batman"}
    assert fake_transport.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1",
    }

    assert isinstance(result, AcquisitionSuccess)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?title=Batman"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.final_url == (
        "https://www.cheapshark.com/api/1.0/games?title=Batman"
    )
    assert result.status_code == 200
    assert result.content_type == "application/json"
    assert result.content == content


def test_cheapshark_game_search_acquirer_returns_transport_failure_unchanged() -> None:
    query = "Batman"
    transport_failure = AcquisitionFailure(
        requested_url="https://www.cheapshark.com/api/1.0/games?title=Batman",
        method=AcquisitionMethod.HTTP,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        outcome=AcquisitionFailureOutcome.NETWORK_ERROR,
        diagnostic_message="HTTP connection failed",
        status_code=None,
        final_url=None,
        content_type=None,
    )

    fake_transport = FakeTransport(transport_failure)

    acquirer = CheapSharkGameSearchAcquirer(
        fake_transport,
        user_agent=USER_AGENT,
    )

    result = acquirer.acquire(query)

    assert result is transport_failure


@pytest.mark.parametrize(
    ("status_code", "expected_message"),
    [
        (403, "HTTP request returned status 403"),
        (503, "HTTP request returned status 503"),
    ],
)
def test_cheapshark_game_search_acquirer_returns_http_failure_for_non_success_status(
    status_code: int,
    expected_message: str,
) -> None:
    snapshot = _make_http_snapshot(
        status_code=status_code,
    )

    fake_transport = FakeTransport(snapshot)

    acquirer = CheapSharkGameSearchAcquirer(
        fake_transport,
        user_agent=USER_AGENT,
    )

    result = acquirer.acquire(QUERY)
    expected_failure = _make_acquisition_failure(
        status_code=status_code,
        diagnostic_message=expected_message,
    )

    assert result == expected_failure


def test_cheapshark_game_search_acquirer_rejects_missing_content_type() -> None:
    snapshot = _make_http_snapshot(
        headers={},
    )

    fake_transport = FakeTransport(snapshot)

    acquirer = CheapSharkGameSearchAcquirer(
        fake_transport,
        user_agent=USER_AGENT,
    )

    result = acquirer.acquire(QUERY)

    expected_failure = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
        diagnostic_message="Missing Content-Type header",
        status_code=200,
        content_type=None,
    )

    assert result == expected_failure


def test_cheapshark_game_search_acquirer_rejects_unsupported_content_type() -> None:
    content_type = "text/html"
    snapshot = _make_http_snapshot(
        headers={"Content-Type": content_type},
    )

    fake_transport = FakeTransport(snapshot)

    acquirer = CheapSharkGameSearchAcquirer(
        fake_transport,
        user_agent=USER_AGENT,
    )

    result = acquirer.acquire(QUERY)

    expected_failure = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
        diagnostic_message=f"Unsupported Content-Type: {content_type}",
        status_code=200,
        content_type=content_type,
    )

    assert result == expected_failure


def test_cheapshark_game_search_acquirer_accepts_json_content_type_with_charset(
) -> None:
    snapshot = _make_http_snapshot(
        headers={"Content-Type": "application/json; charset=UTF-8"},
    )

    fake_transport = FakeTransport(snapshot)

    acquirer = CheapSharkGameSearchAcquirer(
        fake_transport,
        user_agent=USER_AGENT,
    )

    result = acquirer.acquire(QUERY)

    assert isinstance(result, AcquisitionSuccess)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?title=Batman"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.final_url == (
        "https://www.cheapshark.com/api/1.0/games?title=Batman"
    )
    assert result.status_code == 200
    assert result.content_type == "application/json; charset=UTF-8"
    assert result.content == '[{"gameID": "1", "external": "Batman"}]'


def test_cheapshark_game_search_acquirer_normalizes_numeric_retry_after_for_429() -> None:
    snapshot = _make_http_snapshot(
        status_code=429,
        headers={
            "Content-Type": "application/json",
            "Retry-After": "30",
        },
        content='{"error": "too many requests"}',
    )

    fake_transport = FakeTransport(snapshot)

    acquirer = CheapSharkGameSearchAcquirer(
        fake_transport,
        user_agent=USER_AGENT,
    )

    result = acquirer.acquire(QUERY)
    expected_failure = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.HTTP_ERROR,
        diagnostic_message="HTTP request returned status 429",
        status_code=429,
        content_type="application/json",
        retry_after_seconds=30,
    )

    assert result == expected_failure


def test_cheapshark_game_search_acquirer_leaves_retry_after_none_when_header_is_missing() -> None:
    snapshot = _make_http_snapshot(
        status_code=429,
        content='{"error": "too many requests"}',
    )

    fake_transport = FakeTransport(snapshot)

    acquirer = CheapSharkGameSearchAcquirer(
        fake_transport,
        user_agent=USER_AGENT,
    )

    result = acquirer.acquire(QUERY)

    expected_failure = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.HTTP_ERROR,
        diagnostic_message="HTTP request returned status 429",
        status_code=429,
        content_type="application/json",
        retry_after_seconds=None,
    )

    assert result == expected_failure


@pytest.mark.parametrize(
    "invalid_retry_after",
    ["later", "-5"],
)
def test_cheapshark_game_search_acquirer_ignores_invalid_retry_after_for_429(
    invalid_retry_after: str,
) -> None:
    snapshot = _make_http_snapshot(
        status_code=429,
        headers={
            "Content-Type": "application/json",
            "Retry-After": invalid_retry_after,
        },
    )

    fake_transport = FakeTransport(snapshot)

    acquirer = CheapSharkGameSearchAcquirer(
        fake_transport,
        user_agent=USER_AGENT,
    )

    result = acquirer.acquire(QUERY)

    expected_failure = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.HTTP_ERROR,
        diagnostic_message="HTTP request returned status 429",
        status_code=429,
        content_type="application/json",
        retry_after_seconds=None,
    )

    assert result == expected_failure


@pytest.mark.parametrize(
    "blank_body",
    ["", " "],
)
def test_cheapshark_game_search_acquirer_rejects_blank_response_body(
    blank_body: str,
) -> None:
    snapshot = _make_http_snapshot(
        content=blank_body,
    )
    fake_transport = FakeTransport(snapshot)

    acquirer = CheapSharkGameSearchAcquirer(
        fake_transport,
        user_agent=USER_AGENT,
    )

    result = acquirer.acquire(QUERY)

    expected_failure = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
        diagnostic_message="HTTP response body is blank",
        status_code=200,
    )

    assert result == expected_failure


def test_cheapshark_game_search_acquirer_rejects_invalid_json() -> None:
    snapshot = _make_http_snapshot(
        content='[{"gameID": "1", "external": "Batman"}',
    )

    fake_transport = FakeTransport(snapshot)

    acquirer = CheapSharkGameSearchAcquirer(
        fake_transport,
        user_agent=USER_AGENT,
    )

    result = acquirer.acquire(QUERY)

    expected_failure = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
        diagnostic_message="HTTP response body is not valid JSON",
        status_code=200,
    )

    assert result == expected_failure
