from datetime import UTC, datetime
from typing import Any, Never

import pytest

from market_pipeline.acquisition.cheapshark_acquirer import (
    CheapSharkApiAcquirer,
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

STARTED_AT = datetime(2026, 8, 12, 13, 35, tzinfo=UTC)
FINISHED_AT = datetime(2026, 8, 12, 13, 36, tzinfo=UTC)


class UnexpectedCallTransport:
    def get(self, *args, **kwargs) -> Never:
        raise AssertionError("HTTP transport must not be called")


class FakeHttpTransport:
    def __init__(self, http_result: HttpTransportResult) -> None:
        self.http_result = http_result

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
        return self.http_result


def test_cheapshark_acquirer_acquires_game_by_id() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    http_result = HttpResponseSnapshot(
        requested_url="https://www.cheapshark.com/api/1.0/games?id=612",
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        final_url="https://api.cheapshark.com/api/1.0/games?id=612",
        status_code=200,
        headers={"Content-Type": "application/json"},
        content='{"info": {}, "deals": []}',
    )

    fake_transport = FakeHttpTransport(http_result)

    acquirer = CheapSharkApiAcquirer(
        fake_transport,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_transport.called_url == endpoint
    assert fake_transport.called_params == {"id": 612}
    assert fake_transport.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert isinstance(result, AcquisitionSuccess)
    assert result.requested_url == "https://www.cheapshark.com/api/1.0/games?id=612"
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.status_code == 200
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.content_type == "application/json"
    assert result.content == '{"info": {}, "deals": []}'


def test_cheapshark_acquirer_preserves_requested_url_after_redirect() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    http_result = HttpResponseSnapshot(
        requested_url="https://www.cheapshark.com/api/1.0/games?id=612",
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        final_url="https://api.cheapshark.com/api/1.0/games?id=612",
        status_code=200,
        headers={"Content-Type": "application/json"},
        content='{"info": {}, "deals": []}',
    )

    transport = FakeHttpTransport(http_result)

    acquirer = CheapSharkApiAcquirer(
        transport,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert transport.called_url == endpoint
    assert transport.called_params == {"id": 612}
    assert transport.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert isinstance(result, AcquisitionSuccess)
    assert result.requested_url == "https://www.cheapshark.com/api/1.0/games?id=612"
    assert result.method == AcquisitionMethod.HTTP
    assert result.status_code == 200
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.content_type == "application/json"
    assert result.content == '{"info": {}, "deals": []}'

@pytest.mark.parametrize(
    "invalid_game_id",
    [
        "612",
        True,
        False,
    ],
)
def test_cheapshark_acquirer_rejects_non_integer_game_id_before_transport_call(
    invalid_game_id: Any,
) -> None:
    user_agent = "MarketPipelineTest/0.1"

    unexpected_transport = UnexpectedCallTransport()

    acquirer = CheapSharkApiAcquirer(
        unexpected_transport,
        user_agent=user_agent,
    )

    with pytest.raises(TypeError):
        acquirer.acquire(invalid_game_id)


def test_cheapshark_acquirer_returns_transport_failure_unchanged() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    transport_failure = AcquisitionFailure(
        requested_url="https://www.cheapshark.com/api/1.0/games?id=612",
        method=AcquisitionMethod.HTTP,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        outcome=AcquisitionFailureOutcome.REQUEST_ERROR,
        diagnostic_message="HTTP request timed out",
        final_url="https://api.cheapshark.com/api/1.0/games?id=612",
        status_code=502,
        content_type="application/json",
        retry_after_seconds=None,
    )

    transport = FakeHttpTransport(transport_failure)

    acquirer = CheapSharkApiAcquirer(
        transport,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)
    assert transport.called_url == endpoint
    assert transport.called_params == {"id": 612}
    assert transport.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1",
    }
    assert result is transport_failure


@pytest.mark.parametrize(
    ("status_code", "expected_message"),
    [
        (403, "HTTP request returned status 403"),
        (503, "HTTP request returned status 503"),
    ],
)
def test_cheapshark_acquirer_returns_http_failure_for_non_success_status(
    status_code: int,
    expected_message: str,
) -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    http_result = HttpResponseSnapshot(
        requested_url="https://www.cheapshark.com/api/1.0/games?id=612",
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=status_code,
        final_url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": "application/json"},
        content='{"message": "Forbidden"}',
    )

    fake_transport = FakeHttpTransport(http_result)

    acquirer = CheapSharkApiAcquirer(
        fake_transport,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_transport.called_url == endpoint
    assert fake_transport.called_params == {"id": 612}
    assert fake_transport.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.outcome == AcquisitionFailureOutcome.HTTP_ERROR
    assert result.diagnostic_message == expected_message
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == status_code
    assert result.content_type == "application/json"
    assert result.retry_after_seconds is None


def test_cheapshark_acquirer_rejects_missing_content_type() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    http_result = HttpResponseSnapshot(
        requested_url="https://www.cheapshark.com/api/1.0/games?id=612",
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=200,
        final_url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={},
        content='{"info": {}, "deals": []}',
    )

    fake_transport = FakeHttpTransport(http_result)

    acquirer = CheapSharkApiAcquirer(
        fake_transport,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_transport.called_url == endpoint
    assert fake_transport.called_params == {"id": 612}
    assert fake_transport.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.outcome == AcquisitionFailureOutcome.UNEXPECTED_CONTENT
    assert result.diagnostic_message == "Missing Content-Type header"
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 200
    assert result.content_type is None
    assert result.retry_after_seconds is None


def test_cheapshark_acquirer_returns_unexpected_content_failure_for_blank_body(
) -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    http_result = HttpResponseSnapshot(
        requested_url="https://www.cheapshark.com/api/1.0/games?id=612",
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=200,
        final_url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": "application/json"},
        content=" ",
    )

    fake_transport = FakeHttpTransport(http_result)

    acquirer = CheapSharkApiAcquirer(
        fake_transport,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_transport.called_url == endpoint
    assert fake_transport.called_params == {"id": 612}
    assert fake_transport.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.outcome == AcquisitionFailureOutcome.UNEXPECTED_CONTENT
    assert result.diagnostic_message == "HTTP response body is blank"
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 200
    assert result.content_type == "application/json"
    assert result.retry_after_seconds is None


@pytest.mark.parametrize(
    "content_type",
    [
        "application/json",
        "application/json; charset=UTF-8",
        "Application/json; Charset=UTF-8",
    ],
)
def test_cheapshark_acquirer_accepts_supported_json_content_type(
    content_type: str,
) -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    http_result = HttpResponseSnapshot(
        requested_url="https://www.cheapshark.com/api/1.0/games?id=612",
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=200,
        final_url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": content_type},
        content='{"info": {}, "deals": []}',
    )

    fake_transport = FakeHttpTransport(http_result)

    acquirer = CheapSharkApiAcquirer(
        fake_transport,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_transport.called_url == endpoint
    assert fake_transport.called_params == {"id": 612}
    assert fake_transport.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }

    assert isinstance(result, AcquisitionSuccess)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 200
    assert result.content_type == content_type
    assert result.content == '{"info": {}, "deals": []}'


def test_cheapshark_acquirer_rejects_unsupported_content_type() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    http_result = HttpResponseSnapshot(
        requested_url="https://www.cheapshark.com/api/1.0/games?id=612",
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=200,
        final_url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": "text/html"},
        content='{"info": {}, "deals": []}',
    )

    fake_transport = FakeHttpTransport(http_result)

    acquirer = CheapSharkApiAcquirer(
        fake_transport,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_transport.called_url == endpoint
    assert fake_transport.called_params == {"id": 612}
    assert fake_transport.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.outcome == AcquisitionFailureOutcome.UNEXPECTED_CONTENT
    assert result.diagnostic_message == "Unsupported Content-Type: text/html"
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 200
    assert result.content_type == "text/html"
    assert result.retry_after_seconds is None


def test_cheapshark_acquirer_rejects_malformed_json() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    http_result = HttpResponseSnapshot(
        requested_url="https://www.cheapshark.com/api/1.0/games?id=612",
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=200,
        final_url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": "application/json"},
        content='{"info": {',
    )

    fake_transport = FakeHttpTransport(http_result)

    acquirer = CheapSharkApiAcquirer(
        fake_transport,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_transport.called_url == endpoint
    assert fake_transport.called_params == {"id": 612}
    assert fake_transport.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.outcome == AcquisitionFailureOutcome.UNEXPECTED_CONTENT
    assert result.diagnostic_message == "HTTP response body is not valid JSON"
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 200
    assert result.content_type == "application/json"
    assert result.retry_after_seconds is None


def test_cheapshark_acquirer_accepts_valid_json_without_expected_game_fields(
) -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612
    content = '{"message": "No game data"}'

    http_result = HttpResponseSnapshot(
        requested_url="https://www.cheapshark.com/api/1.0/games?id=612",
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=200,
        final_url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": "application/json"},
        content=content,
    )

    fake_transport = FakeHttpTransport(http_result)

    acquirer = CheapSharkApiAcquirer(
        fake_transport,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_transport.called_url == endpoint
    assert fake_transport.called_params == {"id": 612}
    assert fake_transport.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }

    assert isinstance(result, AcquisitionSuccess)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 200
    assert result.content_type == "application/json"
    assert result.content == content


def test_cheapshark_acquirer_preserves_retry_after_seconds_on_rate_limit() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612
    content = '{"message": "Too many requests"}'

    http_result = HttpResponseSnapshot(
        requested_url="https://www.cheapshark.com/api/1.0/games?id=612",
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=429,
        final_url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={
            "Content-Type": "application/json",
            "Retry-After": "60",
        },
        content=content,
    )

    fake_transport = FakeHttpTransport(http_result)

    acquirer = CheapSharkApiAcquirer(
        fake_transport,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_transport.called_url == endpoint
    assert fake_transport.called_params == {"id": 612}
    assert fake_transport.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.outcome == AcquisitionFailureOutcome.HTTP_ERROR
    assert result.diagnostic_message == "HTTP request returned status 429"
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 429
    assert result.content_type == "application/json"
    assert result.retry_after_seconds == 60


def test_cheapshark_acquirer_leaves_retry_after_none_when_header_is_missing(
) -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612
    content = '{"message": "Too many requests"}'

    http_result = HttpResponseSnapshot(
        requested_url="https://www.cheapshark.com/api/1.0/games?id=612",
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=429,
        final_url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={
            "Content-Type": "application/json",
        },
        content=content,
    )

    fake_transport = FakeHttpTransport(http_result)

    acquirer = CheapSharkApiAcquirer(
        fake_transport,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_transport.called_url == endpoint
    assert fake_transport.called_params == {"id": 612}
    assert fake_transport.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.outcome == AcquisitionFailureOutcome.HTTP_ERROR
    assert result.diagnostic_message == "HTTP request returned status 429"
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 429
    assert result.content_type == "application/json"
    assert result.retry_after_seconds is None


@pytest.mark.parametrize(
    "invalid_value",
    [
        "later",
        "-1",
        "",
    ],
)
def test_cheapshark_acquirer_ignores_invalid_retry_after_values(
    invalid_value: str,
) -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612
    content = '{"message": "Too many requests"}'

    http_result = HttpResponseSnapshot(
        requested_url="https://www.cheapshark.com/api/1.0/games?id=612",
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=429,
        final_url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={
            "Content-Type": "application/json",
            "Retry-After": invalid_value,
        },
        content=content,
    )

    fake_transport = FakeHttpTransport(http_result)

    acquirer = CheapSharkApiAcquirer(
        fake_transport,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_transport.called_url == endpoint
    assert fake_transport.called_params == {"id": 612}
    assert fake_transport.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.outcome == AcquisitionFailureOutcome.HTTP_ERROR
    assert result.diagnostic_message == "HTTP request returned status 429"
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 429
    assert result.content_type == "application/json"
    assert result.retry_after_seconds is None
