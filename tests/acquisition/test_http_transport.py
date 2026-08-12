from dataclasses import asdict
from datetime import UTC, datetime
from typing import NamedTuple, Never

import pytest
from requests.exceptions import (
    ConnectionError,
    RequestException,
    Timeout,
    TooManyRedirects,
)

from market_pipeline.acquisition.http_transport import (
    HttpGetTransport,
    HttpResponseSnapshot,
)
from market_pipeline.acquisition.models import (
    AcquisitionFailure,
    AcquisitionFailureOutcome,
    AcquisitionMethod,
)


class FakeResponse(NamedTuple):
    status_code: int
    url: str
    headers: dict[str, str]
    text: str

class FakeSession:
    def __init__(self, fake_response: FakeResponse) -> None:
        self.fake_response = fake_response

    def get(self, url, *, params, headers, timeout) -> FakeResponse:
        self.called_url = url
        self.called_params = params
        self.called_headers = headers
        self.called_timeout = timeout
        return self.fake_response


class TimeoutSession:
    def get(self, url, *, params, headers, timeout) -> Never:
        self.called_url = url
        self.called_params = params
        self.called_headers = headers
        self.called_timeout = timeout
        raise Timeout


class ConnectionErrorSession:
    def get(self, url, *, params, headers, timeout) -> Never:
        self.called_url = url
        self.called_params = params
        self.called_headers = headers
        self.called_timeout = timeout
        raise ConnectionError


class TooManyRedirectsSession:
    def __init__(self, response: FakeResponse | None) -> None:
        self.response = response

    def get(self, url, *, params, headers, timeout) -> Never:
        self.called_url = url
        self.called_params = params
        self.called_headers = headers
        self.called_timeout = timeout
        raise TooManyRedirects(response=self.response)


class RequestExceptionSession:
    def __init__(self, response: FakeResponse | None) -> None:
        self.response = response

    def get(self, url, *, params, headers, timeout) -> Never:
        self.called_url = url
        self.called_params = params
        self.called_headers = headers
        self.called_timeout = timeout
        raise RequestException(response=self.response)


def test_http_response_snapshot_preserves_response_metadata() -> None:
    started_at = datetime(
        2026,
        8,
        11,
        8,
        1,
        tzinfo=UTC,
    )
    finished_at = datetime(
        2026,
        8,
        11,
        8,
        2,
        tzinfo=UTC,
    )

    result = HttpResponseSnapshot(
        requested_url="https://www.cheapshark.com/api/1.0/games",
        started_at=started_at,
        finished_at=finished_at,
        status_code=200,
        final_url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": "application/json"},
        content='{"info": {}, "deals": []}',
    )

    assert asdict(result) == {
        "requested_url": "https://www.cheapshark.com/api/1.0/games",
        "started_at": started_at,
        "finished_at": finished_at,
        "status_code": 200,
        "final_url": "https://api.cheapshark.com/api/1.0/games?id=612",
        "headers": {"Content-Type": "application/json"},
        "content": '{"info": {}, "deals": []}',
    }


def test_http_get_transport_returns_response_snapshot() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    headers = {"User-Agent": "MarketPipelineTest/0.1"}
    params = {"id": 612}

    fake_response = FakeResponse(
        status_code=200,
        url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": "application/json"},
        text='{"info": {}, "deals": []}',
    )

    fake_session = FakeSession(fake_response)

    transport = HttpGetTransport(
        fake_session,
        timeout=2,
    )

    result = transport.get(
        endpoint,
        params=params,
        headers=headers,
    )

    assert fake_session.called_url == "https://www.cheapshark.com/api/1.0/games"
    assert fake_session.called_params == {"id": 612}
    assert fake_session.called_headers == {"User-Agent": "MarketPipelineTest/0.1"}
    assert fake_session.called_timeout == 2

    assert isinstance(result, HttpResponseSnapshot)
    assert result.requested_url == "https://www.cheapshark.com/api/1.0/games?id=612"
    assert result.started_at.tzinfo is not None
    assert result.started_at.utcoffset() is not None
    assert result.finished_at.tzinfo is not None
    assert result.finished_at.utcoffset() is not None
    assert result.finished_at >= result.started_at
    assert result.status_code == 200
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.headers == {"Content-Type": "application/json"}
    assert result.content == '{"info": {}, "deals": []}'


@pytest.mark.parametrize(
    ("session", "outcome", "message"),
    [
        (
            TimeoutSession(),
            AcquisitionFailureOutcome.TIMEOUT,
            "HTTP request timed out",
        ),
        (
            ConnectionErrorSession(),
            AcquisitionFailureOutcome.NETWORK_ERROR,
            "HTTP connection failed",
        ),
    ],
    ids=("timeout", "connection-error"),
)
def test_http_get_transport_classifies_transport_exception_without_response(
    session,
    outcome,
    message,
) -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    headers = {"User-Agent": "MarketPipelineTest/0.1"}
    params = {"id": 612}

    transport = HttpGetTransport(
        session,
        timeout=2,
    )

    result = transport.get(
        endpoint,
        params=params,
        headers=headers,
    )

    assert session.called_url == "https://www.cheapshark.com/api/1.0/games"
    assert session.called_params == {"id": 612}
    assert session.called_headers == {"User-Agent": "MarketPipelineTest/0.1"}
    assert session.called_timeout == 2

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == "https://www.cheapshark.com/api/1.0/games?id=612"
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at.tzinfo is not None
    assert result.started_at.utcoffset() is not None
    assert result.finished_at.tzinfo is not None
    assert result.finished_at.utcoffset() is not None
    assert result.finished_at >= result.started_at
    assert result.outcome == outcome
    assert result.diagnostic_message == message
    assert result.final_url is None
    assert result.status_code is None
    assert result.content_type is None
    assert result.retry_after_seconds is None


@pytest.mark.parametrize(
    (
        "response",
        "expected_final_url",
        "expected_status_code",
        "expected_content_type",
    ),
    [
        (None, None, None, None),
        (
            FakeResponse(
                status_code=302,
                url="https://api.cheapshark.com/api/1.0/games?id=612",
                headers={"Content-Type": "application/json"},
                text="",
            ),
            "https://api.cheapshark.com/api/1.0/games?id=612",
            302,
            "application/json",
        ),
    ],
    ids=("without-response", "with-response"),
)
def test_http_get_transport_returns_redirect_limit_failure(
    response: FakeResponse | None,
    expected_final_url: str | None,
    expected_status_code: int | None,
    expected_content_type: str | None,
) -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    headers = {"User-Agent": "MarketPipelineTest/0.1"}
    params = {"id": 612}

    too_many_redirects_session = TooManyRedirectsSession(response)

    transport = HttpGetTransport(
        too_many_redirects_session,
        timeout=2,
    )

    result = transport.get(
        endpoint,
        params=params,
        headers=headers,
    )

    assert too_many_redirects_session.called_url == endpoint
    assert too_many_redirects_session.called_params == {"id": 612}
    assert too_many_redirects_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert too_many_redirects_session.called_timeout == 2

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at.tzinfo is not None
    assert result.started_at.utcoffset() is not None
    assert result.finished_at.tzinfo is not None
    assert result.finished_at.utcoffset() is not None
    assert result.finished_at >= result.started_at
    assert result.outcome == AcquisitionFailureOutcome.HTTP_ERROR
    assert result.diagnostic_message == (
        "HTTP request exceeded redirect limit"
    )
    assert result.final_url == expected_final_url
    assert result.status_code == expected_status_code
    assert result.content_type == expected_content_type
    assert result.retry_after_seconds is None


@pytest.mark.parametrize(
    (
        "response",
        "expected_final_url",
        "expected_status_code",
        "expected_content_type",
    ),
    [
        (None, None, None, None),
        (
            FakeResponse(
                status_code=502,
                url="https://api.cheapshark.com/api/1.0/games?id=612",
                headers={"Content-Type": "application/json"},
                text="",
            ),
            "https://api.cheapshark.com/api/1.0/games?id=612",
            502,
            "application/json",
        ),
    ],
    ids=("without-response", "with-response"),
)
def test_http_get_transport_returns_request_failure_on_request_exception(
    response: FakeResponse | None,
    expected_final_url: str | None,
    expected_status_code: int | None,
    expected_content_type: str | None,
) -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    headers = {"User-Agent": "MarketPipelineTest/0.1"}
    params = {"id": 612}

    request_exception_session = RequestExceptionSession(response)

    transport = HttpGetTransport(
        request_exception_session,
        timeout=2,
    )

    result = transport.get(
        endpoint,
        params=params,
        headers=headers,
    )

    assert request_exception_session.called_url == endpoint
    assert request_exception_session.called_params == {"id": 612}
    assert request_exception_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert request_exception_session.called_timeout == 2

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at.tzinfo is not None
    assert result.started_at.utcoffset() is not None
    assert result.finished_at.tzinfo is not None
    assert result.finished_at.utcoffset() is not None
    assert result.finished_at >= result.started_at
    assert result.outcome == AcquisitionFailureOutcome.REQUEST_ERROR
    assert result.diagnostic_message == (
        "HTTP request failed: RequestException"
    )
    assert result.final_url == expected_final_url
    assert result.status_code == expected_status_code
    assert result.content_type == expected_content_type
    assert result.retry_after_seconds is None
