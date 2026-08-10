from typing import NamedTuple, Never

import pytest
from requests.exceptions import (
    ConnectionError,
    InvalidURL,
    RequestException,
    Timeout,
    TooManyRedirects,
)

from market_pipeline.acquisition.models import (
    AcquisitionFailure,
    AcquisitionFailureOutcome,
    AcquisitionMethod,
    AcquisitionSuccess,
)
from market_pipeline.acquisition.requests_acquirer import RequestsAcquirer


class FakeResponse(NamedTuple):
    status_code: int
    url: str
    headers: dict[str, str]
    text: str


class TimeoutSession:
    def get(self, url, *, timeout) -> Never:
        self.called_url = url
        self.called_timeout = timeout
        raise Timeout


class ConnectionErrorSession:
    def get(self, url, *, timeout) -> Never:
        self.called_url = url
        self.called_timeout = timeout
        raise ConnectionError


class TooManyRedirectsSession:
    def __init__(self, response: FakeResponse | None) -> None:
        self.response = response

    def get(self, url, *, timeout) -> Never:
        self.called_url = url
        self.called_timeout = timeout
        raise TooManyRedirects(response=self.response)


class InvalidURLSession:
    def get(self, url, *, timeout) -> Never:
        self.called_url = url
        self.called_timeout = timeout
        raise InvalidURL


class RequestExceptionSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    def get(self, url, *, timeout) -> Never:
        self.called_url = url
        self.called_timeout = timeout
        raise RequestException(response=self.response)


class FakeSession:
    def __init__(self, fake_response: FakeResponse) -> None:
        self.fake_response = fake_response

    def get(self, url, *, timeout) -> FakeResponse:
        self.called_url = url
        self.called_timeout = timeout
        return self.fake_response


def test_requests_acquirer_returns_acquisition_success():
    requested_url = "https://example.test/product"

    fake_response = FakeResponse(
        status_code=200,
        url="https://example.test/products/123",
        headers={"Content-Type": "text/html"},
        text="<html><body>Product</body></html>",
    )

    fake_session = FakeSession(fake_response)

    acquirer = RequestsAcquirer(fake_session, timeout=5)

    result = acquirer.acquire(requested_url)

    assert fake_session.called_url == requested_url
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionSuccess)
    assert result.status_code == 200
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.final_url == "https://example.test/products/123"
    assert result.content_type == "text/html"
    assert result.content == "<html><body>Product</body></html>"


def test_requests_acquirer_returns_timeout_failure():
    requested_url = "https://example.test/product"

    fake_session = TimeoutSession()

    acquirer = RequestsAcquirer(fake_session, timeout=5)

    result = acquirer.acquire(requested_url)

    assert fake_session.called_url == requested_url
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.TIMEOUT
    assert result.diagnostic_message == "HTTP request timed out"
    assert result.final_url is None
    assert result.status_code is None
    assert result.content_type is None


def test_requests_acquirer_returns_network_failure_on_connection_error():
    requested_url = "https://example.test/product"

    fake_session = ConnectionErrorSession()

    acquirer = RequestsAcquirer(fake_session, timeout=5)

    result = acquirer.acquire(requested_url)

    assert fake_session.called_url == requested_url
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.NETWORK_ERROR
    assert result.diagnostic_message == "HTTP connection failed"
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
def test_requests_acquirer_returns_http_failure_for_non_success_status(
    status_code: int,
    expected_message: str,
):
    requested_url = "https://example.test/product"

    fake_response = FakeResponse(
        status_code=status_code,
        url="https://example.test/products/123",
        headers={"Content-Type": "text/html"},
        text="<html><body>Product</body></html>",
    )

    fake_session = FakeSession(fake_response)

    acquirer = RequestsAcquirer(fake_session, timeout=5)

    result = acquirer.acquire(requested_url)

    assert fake_session.called_url == requested_url
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.HTTP_ERROR
    assert result.diagnostic_message == expected_message
    assert result.final_url == "https://example.test/products/123"
    assert result.status_code == status_code
    assert result.content_type == "text/html"


def test_requests_acquirer_returns_unexpected_content_failure_for_blank_body():
    requested_url = "https://example.test/product"

    fake_response = FakeResponse(
        status_code=200,
        url="https://example.test/products/123",
        headers={"Content-Type": "text/html"},
        text=" ",
    )

    fake_session = FakeSession(fake_response)

    acquirer = RequestsAcquirer(fake_session, timeout=5)

    result = acquirer.acquire(requested_url)

    assert fake_session.called_url == requested_url
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.UNEXPECTED_CONTENT
    assert result.diagnostic_message == "HTTP response body is blank"
    assert result.final_url == "https://example.test/products/123"
    assert result.status_code == 200
    assert result.content_type == "text/html"


def test_requests_acquirer_rejects_unsupported_content_type():
    requested_url = "https://example.test/product"

    fake_response = FakeResponse(
        status_code=200,
        url="https://example.test/products/123",
        headers={"Content-Type": "application/pdf"},
        text="test",
    )

    fake_session = FakeSession(fake_response)

    acquirer = RequestsAcquirer(fake_session, timeout=5)

    result = acquirer.acquire(requested_url)

    assert fake_session.called_url == requested_url
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.UNEXPECTED_CONTENT
    assert result.diagnostic_message == "Unsupported Content-Type: application/pdf"
    assert result.final_url == "https://example.test/products/123"
    assert result.status_code == 200
    assert result.content_type == "application/pdf"


def test_requests_acquirer_accepts_html_content_type_with_charset():
    requested_url = "https://example.test/product"

    fake_response = FakeResponse(
        status_code=200,
        url="https://example.test/products/123",
        headers={"Content-Type": "text/html; charset=UTF-8"},
        text="<html><body>Product</body></html>",
    )

    fake_session = FakeSession(fake_response)

    acquirer = RequestsAcquirer(fake_session, timeout=5)

    result = acquirer.acquire(requested_url)

    assert fake_session.called_url == requested_url
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionSuccess)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.final_url == "https://example.test/products/123"
    assert result.status_code == 200
    assert result.content_type == "text/html; charset=UTF-8"
    assert result.content == "<html><body>Product</body></html>"


def test_requests_acquirer_rejects_missing_content_type():
    requested_url = "https://example.test/product"

    fake_response = FakeResponse(
        status_code=200,
        url="https://example.test/products/123",
        headers={},
        text="test",
    )

    fake_session = FakeSession(fake_response)

    acquirer = RequestsAcquirer(fake_session, timeout=5)

    result = acquirer.acquire(requested_url)

    assert fake_session.called_url == requested_url
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.UNEXPECTED_CONTENT
    assert result.diagnostic_message == "Missing Content-Type header"
    assert result.final_url == "https://example.test/products/123"
    assert result.status_code == 200
    assert result.content_type is None


def test_requests_acquirer_accepts_case_insensitive_html_media_type():
    requested_url = "https://example.test/product"

    fake_response = FakeResponse(
        status_code=200,
        url="https://example.test/products/123",
        headers={"Content-Type": "Text/html; Charset=UTF-8"},
        text="<html><body>Product</body></html>",
    )

    fake_session = FakeSession(fake_response)

    acquirer = RequestsAcquirer(fake_session, timeout=5)

    result = acquirer.acquire(requested_url)

    assert fake_session.called_url == requested_url
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionSuccess)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.final_url == "https://example.test/products/123"
    assert result.status_code == 200
    assert result.content_type == "Text/html; Charset=UTF-8"
    assert result.content == "<html><body>Product</body></html>"


def test_requests_acquirer_returns_http_failure_on_too_many_redirects():
    requested_url = "https://example.test/product"

    fake_response = FakeResponse(
        status_code=302,
        url="https://example.test/redirect-loop",
        headers={"Content-Type": "text/html; charset=UTF-8"},
        text="<html><body>Product</body></html>",
    )

    fake_session = TooManyRedirectsSession(fake_response)

    acquirer = RequestsAcquirer(fake_session, timeout=5)

    result = acquirer.acquire(requested_url)

    assert fake_session.called_url == requested_url
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.HTTP_ERROR
    assert result.diagnostic_message == "HTTP request exceeded redirect limit"
    assert result.final_url == "https://example.test/redirect-loop"
    assert result.status_code == 302
    assert result.content_type == "text/html; charset=UTF-8"


def test_requests_acquirer_returns_http_failure_for_redirect_limit_without_response():
    requested_url = "https://example.test/product"

    fake_response = None

    fake_session = TooManyRedirectsSession(fake_response)

    acquirer = RequestsAcquirer(fake_session, timeout=5)

    result = acquirer.acquire(requested_url)

    assert fake_session.called_url == requested_url
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.HTTP_ERROR
    assert result.diagnostic_message == "HTTP request exceeded redirect limit"
    assert result.final_url is None
    assert result.status_code is None
    assert result.content_type is None


def test_requests_acquirer_returns_request_failure_on_invalid_url():
    requested_url = "https://"

    fake_session = InvalidURLSession()

    acquirer = RequestsAcquirer(fake_session, timeout=5)

    result = acquirer.acquire(requested_url)

    assert fake_session.called_url == requested_url
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.REQUEST_ERROR
    assert result.diagnostic_message == "HTTP request failed: InvalidURL"
    assert result.final_url is None
    assert result.status_code is None
    assert result.content_type is None


def test_requests_acquirer_preserves_response_metadata_on_request_exception():
    requested_url = "https://example.test/product"

    fake_response = FakeResponse(
        status_code=502,
        url="https://example.test/upstream",
        headers={"Content-Type": "text/html"},
        text="<html><body>Bad Gateway</body></html>",
    )

    fake_session = RequestExceptionSession(fake_response)

    acquirer = RequestsAcquirer(fake_session, timeout=5)

    result = acquirer.acquire(requested_url)

    assert fake_session.called_url == requested_url
    assert fake_session.called_timeout == 5

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.outcome == AcquisitionFailureOutcome.REQUEST_ERROR
    assert result.diagnostic_message == "HTTP request failed: RequestException"
    assert result.final_url == "https://example.test/upstream"
    assert result.status_code == 502
    assert result.content_type == "text/html"
