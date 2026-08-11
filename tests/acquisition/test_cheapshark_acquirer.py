from typing import Any, NamedTuple, Never

import pytest
from requests.exceptions import (
    ConnectionError,
    RequestException,
    Timeout,
    TooManyRedirects,
)

from market_pipeline.acquisition.cheapshark_acquirer import (
    CheapSharkApiAcquirer,
)
from market_pipeline.acquisition.models import (
    AcquisitionFailure,
    AcquisitionFailureOutcome,
    AcquisitionMethod,
    AcquisitionSuccess,
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


class UnexpectedCallSession:
    def get(self, *args, **kwargs) -> Never:
        raise AssertionError("HTTP session must not be called")


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


def test_cheapshark_acquirer_acquires_game_by_id() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    fake_response = FakeResponse(
        status_code=200,
        url="https://www.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": "application/json"},
        text='{"info": {}, "deals": []}',
    )

    fake_session = FakeSession(fake_response)

    acquirer = CheapSharkApiAcquirer(
        fake_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_session.called_url == endpoint
    assert fake_session.called_params == {"id": 612}
    assert fake_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionSuccess)
    assert result.requested_url == "https://www.cheapshark.com/api/1.0/games?id=612"
    assert result.method == AcquisitionMethod.HTTP
    assert result.status_code == 200
    assert result.final_url == "https://www.cheapshark.com/api/1.0/games?id=612"
    assert result.content_type == "application/json"
    assert result.content == '{"info": {}, "deals": []}'


def test_cheapshark_acquirer_preserves_requested_url_after_redirect() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    fake_response = FakeResponse(
        status_code=200,
        url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": "application/json"},
        text='{"info": {}, "deals": []}',
    )

    fake_session = FakeSession(fake_response)

    acquirer = CheapSharkApiAcquirer(
        fake_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_session.called_url == endpoint
    assert fake_session.called_params == {"id": 612}
    assert fake_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert fake_session.called_timeout == 5

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
def test_cheapshark_acquirer_rejects_non_integer_game_id_before_request(
    invalid_game_id: Any,
) -> None:
    user_agent = "MarketPipelineTest/0.1"

    unexpected_session = UnexpectedCallSession()

    acquirer = CheapSharkApiAcquirer(
        unexpected_session,
        timeout=5,
        user_agent=user_agent,
    )

    with pytest.raises(TypeError):
        acquirer.acquire(invalid_game_id)


def test_cheapshark_acquirer_returns_timeout_failure() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    timeout_session = TimeoutSession()

    acquirer = CheapSharkApiAcquirer(
        timeout_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert timeout_session.called_url == endpoint
    assert timeout_session.called_params == {"id": 612}
    assert timeout_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert timeout_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == "https://www.cheapshark.com/api/1.0/games?id=612"
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.TIMEOUT
    assert result.diagnostic_message == "HTTP request timed out"
    assert result.final_url is None
    assert result.status_code is None
    assert result.content_type is None


def test_cheapshark_acquirer_returns_network_failure_on_connection_error() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    connection_error_session = ConnectionErrorSession()

    acquirer = CheapSharkApiAcquirer(
        connection_error_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert connection_error_session.called_url == endpoint
    assert connection_error_session.called_params == {"id": 612}
    assert connection_error_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert connection_error_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == "https://www.cheapshark.com/api/1.0/games?id=612"
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.NETWORK_ERROR
    assert result.diagnostic_message == "HTTP connection failed"
    assert result.final_url is None
    assert result.status_code is None
    assert result.content_type is None


def test_cheapshark_acquirer_returns_http_failure_on_too_many_redirects() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    fake_response = FakeResponse(
        status_code=302,
        url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": "application/json"},
        text='{"info": {}, "deals": []}',
    )

    too_many_redirects_session = TooManyRedirectsSession(fake_response)

    acquirer = CheapSharkApiAcquirer(
        too_many_redirects_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert too_many_redirects_session.called_url == endpoint
    assert too_many_redirects_session.called_params == {"id": 612}
    assert too_many_redirects_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert too_many_redirects_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == "https://www.cheapshark.com/api/1.0/games?id=612"
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.HTTP_ERROR
    assert result.diagnostic_message == "HTTP request exceeded redirect limit"
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 302
    assert result.content_type == "application/json"


def test_cheapshark_acquirer_returns_http_failure_for_redirect_limit_without_response(
) -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    too_many_redirects_session = TooManyRedirectsSession(response=None)

    acquirer = CheapSharkApiAcquirer(
        too_many_redirects_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert too_many_redirects_session.called_url == endpoint
    assert too_many_redirects_session.called_params == {"id": 612}
    assert too_many_redirects_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert too_many_redirects_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.HTTP_ERROR
    assert result.diagnostic_message == "HTTP request exceeded redirect limit"
    assert result.final_url is None
    assert result.status_code is None
    assert result.content_type is None


def test_cheapshark_acquirer_preserves_response_metadata_on_request_exception(
) -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    fake_response = FakeResponse(
        status_code=502,
        url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": "application/json"},
        text='{"info": {}, "deals": []}',
    )

    request_exception_session = RequestExceptionSession(fake_response)

    acquirer = CheapSharkApiAcquirer(
        request_exception_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert request_exception_session.called_url == endpoint
    assert request_exception_session.called_params == {"id": 612}
    assert request_exception_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert request_exception_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == "https://www.cheapshark.com/api/1.0/games?id=612"
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.REQUEST_ERROR
    assert result.diagnostic_message == "HTTP request failed: RequestException"
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 502
    assert result.content_type == "application/json"


def test_cheapshark_acquirer_returns_request_failure_without_response() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    request_exception_session = RequestExceptionSession(response=None)

    acquirer = CheapSharkApiAcquirer(
        request_exception_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert request_exception_session.called_url == endpoint
    assert request_exception_session.called_params == {"id": 612}
    assert request_exception_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert request_exception_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.REQUEST_ERROR
    assert result.diagnostic_message == "HTTP request failed: RequestException"
    assert result.final_url is None
    assert result.status_code is None
    assert result.content_type is None

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

    fake_response = FakeResponse(
        status_code=status_code,
        url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": "application/json"},
        text='{"message": "Forbidden"}',
    )

    fake_session = FakeSession(fake_response)

    acquirer = CheapSharkApiAcquirer(
        fake_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_session.called_url == endpoint
    assert fake_session.called_params == {"id": 612}
    assert fake_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.HTTP_ERROR
    assert result.diagnostic_message == expected_message
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == status_code
    assert result.content_type == "application/json"


def test_cheapshark_acquirer_rejects_missing_content_type() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    fake_response = FakeResponse(
        status_code=200,
        url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={},
        text='{"info": {}, "deals": []}',
    )

    fake_session = FakeSession(fake_response)

    acquirer = CheapSharkApiAcquirer(
        fake_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_session.called_url == endpoint
    assert fake_session.called_params == {"id": 612}
    assert fake_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.UNEXPECTED_CONTENT
    assert result.diagnostic_message == "Missing Content-Type header"
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 200
    assert result.content_type is None


def test_cheapshark_acquirer_returns_unexpected_content_failure_for_blank_body(
) -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    fake_response = FakeResponse(
        status_code=200,
        url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": "application/json"},
        text=" ",
    )

    fake_session = FakeSession(fake_response)

    acquirer = CheapSharkApiAcquirer(
        fake_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_session.called_url == endpoint
    assert fake_session.called_params == {"id": 612}
    assert fake_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.UNEXPECTED_CONTENT
    assert result.diagnostic_message == "HTTP response body is blank"
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 200
    assert result.content_type == "application/json"


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

    fake_response = FakeResponse(
        status_code=200,
        url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": content_type},
        text='{"info": {}, "deals": []}',
    )

    fake_session = FakeSession(fake_response)

    acquirer = CheapSharkApiAcquirer(
        fake_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_session.called_url == endpoint
    assert fake_session.called_params == {"id": 612}
    assert fake_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionSuccess)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 200
    assert result.content_type == content_type
    assert result.content == '{"info": {}, "deals": []}'


def test_cheapshark_acquirer_rejects_unsupported_content_type() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    fake_response = FakeResponse(
        status_code=200,
        url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": "text/html"},
        text='{"info": {}, "deals": []}',
    )

    fake_session = FakeSession(fake_response)

    acquirer = CheapSharkApiAcquirer(
        fake_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_session.called_url == endpoint
    assert fake_session.called_params == {"id": 612}
    assert fake_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.UNEXPECTED_CONTENT
    assert result.diagnostic_message == "Unsupported Content-Type: text/html"
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 200
    assert result.content_type == "text/html"


def test_cheapshark_acquirer_rejects_malformed_json() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612

    fake_response = FakeResponse(
        status_code=200,
        url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": "application/json"},
        text='{"info": {',
    )

    fake_session = FakeSession(fake_response)

    acquirer = CheapSharkApiAcquirer(
        fake_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_session.called_url == endpoint
    assert fake_session.called_params == {"id": 612}
    assert fake_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.UNEXPECTED_CONTENT
    assert result.diagnostic_message == "HTTP response body is not valid JSON"
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 200
    assert result.content_type == "application/json"


def test_cheapshark_acquirer_accepts_valid_json_without_expected_game_fields(
) -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612
    content = '{"message": "No game data"}'

    fake_response = FakeResponse(
        status_code=200,
        url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={"Content-Type": "application/json"},
        text=content,
    )

    fake_session = FakeSession(fake_response)

    acquirer = CheapSharkApiAcquirer(
        fake_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_session.called_url == endpoint
    assert fake_session.called_params == {"id": 612}
    assert fake_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionSuccess)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 200
    assert result.content_type == "application/json"
    assert result.content == content


def test_cheapshark_acquirer_preserves_retry_after_seconds_on_rate_limit() -> None:
    endpoint = "https://www.cheapshark.com/api/1.0/games"
    user_agent = "MarketPipelineTest/0.1"
    game_id = 612
    content = '{"message": "Too many requests"}'

    fake_response = FakeResponse(
        status_code=429,
        url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={
            "Content-Type": "application/json",
            "Retry-After": "60",
        },
        text=content,
    )

    fake_session = FakeSession(fake_response)

    acquirer = CheapSharkApiAcquirer(
        fake_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_session.called_url == endpoint
    assert fake_session.called_params == {"id": 612}
    assert fake_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
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

    fake_response = FakeResponse(
        status_code=429,
        url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={
            "Content-Type": "application/json",
        },
        text=content,
    )

    fake_session = FakeSession(fake_response)

    acquirer = CheapSharkApiAcquirer(
        fake_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_session.called_url == endpoint
    assert fake_session.called_params == {"id": 612}
    assert fake_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
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

    fake_response = FakeResponse(
        status_code=429,
        url="https://api.cheapshark.com/api/1.0/games?id=612",
        headers={
            "Content-Type": "application/json",
            "Retry-After": invalid_value,
        },
        text=content,
    )

    fake_session = FakeSession(fake_response)

    acquirer = CheapSharkApiAcquirer(
        fake_session,
        timeout=5,
        user_agent=user_agent,
    )

    result = acquirer.acquire(game_id)

    assert fake_session.called_url == endpoint
    assert fake_session.called_params == {"id": 612}
    assert fake_session.called_headers == {
        "User-Agent": "MarketPipelineTest/0.1"
    }
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == (
        "https://www.cheapshark.com/api/1.0/games?id=612"
    )
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.HTTP_ERROR
    assert result.diagnostic_message == "HTTP request returned status 429"
    assert result.final_url == "https://api.cheapshark.com/api/1.0/games?id=612"
    assert result.status_code == 429
    assert result.content_type == "application/json"
    assert result.retry_after_seconds is None
