from datetime import UTC, datetime

import pytest

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
from market_pipeline.acquisition.requests_acquirer import RequestsAcquirer

STARTED_AT = datetime(2026, 8, 13, 9, 2, tzinfo=UTC)
FINISHED_AT = datetime(2026, 8, 13, 9, 3, tzinfo=UTC)


class FakeHttpTransport:
    def __init__(self, http_result: HttpTransportResult) -> None:
        self.http_result = http_result

    def get(self, url: str) -> HttpTransportResult:
        self.called_url = url
        return self.http_result


def test_requests_acquirer_returns_acquisition_success() -> None:
    requested_url = "https://example.test/product"

    http_result = HttpResponseSnapshot(
        requested_url=requested_url,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=200,
        final_url="https://example.test/products/123",
        headers={"Content-Type": "text/html"},
        content="<html><body>Product</body></html>",
    )

    transport = FakeHttpTransport(http_result)

    acquirer = RequestsAcquirer(transport)

    result = acquirer.acquire(requested_url)

    assert transport.called_url == requested_url

    assert isinstance(result, AcquisitionSuccess)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.final_url == "https://example.test/products/123"
    assert result.status_code == 200
    assert result.content_type == "text/html"
    assert result.content == "<html><body>Product</body></html>"


def test_requests_acquirer_returns_transport_failure_unchanged() -> None:
    requested_url = "https://example.test/product"

    transport_failure = AcquisitionFailure(
        requested_url=requested_url,
        method=AcquisitionMethod.HTTP,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        outcome=AcquisitionFailureOutcome.REQUEST_ERROR,
        diagnostic_message="HTTP request failed: RequestException",
        final_url="https://example.test/upstream",
        status_code=502,
        content_type="text/html",
    )
    transport = FakeHttpTransport(transport_failure)
    acquirer = RequestsAcquirer(transport)

    result = acquirer.acquire(requested_url)

    assert transport.called_url == requested_url
    assert result is transport_failure


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
) -> None:
    requested_url = "https://example.test/product"

    http_result = HttpResponseSnapshot(
        requested_url=requested_url,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=status_code,
        final_url="https://example.test/products/123",
        headers={"Content-Type": "text/html"},
        content="<html><body>Product</body></html>",
    )
    transport = FakeHttpTransport(http_result)
    acquirer = RequestsAcquirer(transport)

    result = acquirer.acquire(requested_url)

    assert transport.called_url == requested_url

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.outcome == AcquisitionFailureOutcome.HTTP_ERROR
    assert result.diagnostic_message == expected_message
    assert result.final_url == "https://example.test/products/123"
    assert result.status_code == status_code
    assert result.content_type == "text/html"
    assert result.retry_after_seconds is None


def test_requests_acquirer_returns_unexpected_content_failure_for_blank_body() -> None:
    requested_url = "https://example.test/product"

    http_result = HttpResponseSnapshot(
        requested_url=requested_url,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=200,
        final_url="https://example.test/products/123",
        headers={"Content-Type": "text/html"},
        content=" ",
    )
    transport = FakeHttpTransport(http_result)
    acquirer = RequestsAcquirer(transport)

    result = acquirer.acquire(requested_url)

    assert transport.called_url == requested_url

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.outcome == AcquisitionFailureOutcome.UNEXPECTED_CONTENT
    assert result.diagnostic_message == "HTTP response body is blank"
    assert result.final_url == "https://example.test/products/123"
    assert result.status_code == 200
    assert result.content_type == "text/html"
    assert result.retry_after_seconds is None


def test_requests_acquirer_rejects_unsupported_content_type() -> None:
    requested_url = "https://example.test/product"

    http_result = HttpResponseSnapshot(
        requested_url=requested_url,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=200,
        final_url="https://example.test/products/123",
        headers={"Content-Type": "application/pdf"},
        content="test",
    )
    transport = FakeHttpTransport(http_result)
    acquirer = RequestsAcquirer(transport)

    result = acquirer.acquire(requested_url)

    assert transport.called_url == requested_url

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.outcome == AcquisitionFailureOutcome.UNEXPECTED_CONTENT
    assert result.diagnostic_message == "Unsupported Content-Type: application/pdf"
    assert result.final_url == "https://example.test/products/123"
    assert result.status_code == 200
    assert result.content_type == "application/pdf"
    assert result.retry_after_seconds is None


def test_requests_acquirer_accepts_html_content_type_with_charset() -> None:
    requested_url = "https://example.test/product"

    http_result = HttpResponseSnapshot(
        requested_url=requested_url,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=200,
        final_url="https://example.test/products/123",
        headers={"Content-Type": "text/html; charset=UTF-8"},
        content="<html><body>Product</body></html>",
    )
    transport = FakeHttpTransport(http_result)
    acquirer = RequestsAcquirer(transport)

    result = acquirer.acquire(requested_url)

    assert transport.called_url == requested_url

    assert isinstance(result, AcquisitionSuccess)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.final_url == "https://example.test/products/123"
    assert result.status_code == 200
    assert result.content_type == "text/html; charset=UTF-8"
    assert result.content == "<html><body>Product</body></html>"


def test_requests_acquirer_rejects_missing_content_type() -> None:
    requested_url = "https://example.test/product"

    http_result = HttpResponseSnapshot(
        requested_url=requested_url,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=200,
        final_url="https://example.test/products/123",
        headers={},
        content="test",
    )
    transport = FakeHttpTransport(http_result)
    acquirer = RequestsAcquirer(transport)

    result = acquirer.acquire(requested_url)

    assert transport.called_url == requested_url

    assert isinstance(result, AcquisitionFailure)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.outcome == AcquisitionFailureOutcome.UNEXPECTED_CONTENT
    assert result.diagnostic_message == "Missing Content-Type header"
    assert result.final_url == "https://example.test/products/123"
    assert result.status_code == 200
    assert result.content_type is None
    assert result.retry_after_seconds is None


def test_requests_acquirer_accepts_case_insensitive_html_media_type() -> None:
    requested_url = "https://example.test/product"

    http_result = HttpResponseSnapshot(
        requested_url=requested_url,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        status_code=200,
        final_url="https://example.test/products/123",
        headers={"Content-Type": "Text/html; Charset=UTF-8"},
        content="<html><body>Product</body></html>",
    )
    transport = FakeHttpTransport(http_result)
    acquirer = RequestsAcquirer(transport)

    result = acquirer.acquire(requested_url)

    assert transport.called_url == requested_url

    assert isinstance(result, AcquisitionSuccess)
    assert result.requested_url == requested_url
    assert result.method == AcquisitionMethod.HTTP
    assert result.started_at == STARTED_AT
    assert result.finished_at == FINISHED_AT
    assert result.final_url == "https://example.test/products/123"
    assert result.status_code == 200
    assert result.content_type == "Text/html; Charset=UTF-8"
    assert result.content == "<html><body>Product</body></html>"
