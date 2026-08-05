from dataclasses import FrozenInstanceError, asdict
from datetime import UTC, datetime

import pytest

from market_pipeline.acquisition.models import (
    AcquisitionFailure,
    AcquisitionFailureOutcome,
    AcquisitionMethod,
    AcquisitionSuccess,
)


def make_acquisition_success(**overrides) -> AcquisitionSuccess:
    started_at = datetime(
        2026, 8, 4, 8, tzinfo=UTC
    )
    finished_at = datetime(
        2026, 8, 4, 8, 1, tzinfo=UTC
    )
    data = {
        "requested_url": "https://example.test/product",
        "method": AcquisitionMethod.HTTP,
        "started_at": started_at,
        "finished_at": finished_at,
        "final_url": "https://example.test/products/123",
        "status_code": 200,
        "content_type": "text/html",
        "content": "<html><body>Product</body></html>",
    }
    data.update(overrides)

    return AcquisitionSuccess(**data)


def make_acquisition_failure(**overrides) -> AcquisitionFailure:
    started_at = datetime(
        2026, 8, 4, 8, tzinfo=UTC
    )
    finished_at = datetime(
        2026, 8, 4, 8, 1, tzinfo=UTC
    )

    data = {
        "requested_url": "https://example.test/product",
        "method": AcquisitionMethod.HTTP,
        "started_at": started_at,
        "finished_at": finished_at,
        "outcome": AcquisitionFailureOutcome.HTTP_ERROR,
        "diagnostic_message": "Server returned HTTP 503",
        "final_url": "https://example.test/products/123",
        "status_code": 503,
        "content_type": "text/html",
    }
    data.update(overrides)

    return AcquisitionFailure(**data)


def test_acquisition_success_stores_response_data():
    started_at = datetime(
        2026, 8, 4, 8, tzinfo=UTC
    )
    finished_at = datetime(
        2026, 8, 4, 8, 1, tzinfo=UTC
    )
    result = AcquisitionSuccess(
        requested_url="https://example.test/product",
        method=AcquisitionMethod.HTTP,
        started_at=started_at,
        finished_at=finished_at,
        final_url="https://example.test/products/123",
        status_code=200,
        content_type="text/html",
        content="<html><body>Product</body></html>",
    )

    assert asdict(result) == {
        "requested_url": "https://example.test/product",
        "method": AcquisitionMethod.HTTP,
        "started_at": started_at,
        "finished_at": finished_at,
        "final_url": "https://example.test/products/123",
        "status_code": 200,
        "content_type": "text/html",
        "content": "<html><body>Product</body></html>",
    }


def test_acquisition_failure_stores_available_http_metadata():
    started_at = datetime(
        2026, 8, 4, 9, tzinfo=UTC
    )
    finished_at = datetime(
        2026, 8, 4, 9, 1, tzinfo=UTC
    )

    result = AcquisitionFailure(
        requested_url="https://example.test/product",
        method=AcquisitionMethod.HTTP,
        started_at=started_at,
        finished_at=finished_at,
        outcome=AcquisitionFailureOutcome.HTTP_ERROR,
        diagnostic_message="Server returned HTTP 503",
        final_url="https://example.test/products/123",
        status_code=503,
        content_type="text/html",
    )

    assert asdict(result) == {
        "requested_url": "https://example.test/product",
        "method": AcquisitionMethod.HTTP,
        "started_at": started_at,
        "finished_at": finished_at,
        "outcome": AcquisitionFailureOutcome.HTTP_ERROR,
        "diagnostic_message": "Server returned HTTP 503",
        "final_url": "https://example.test/products/123",
        "status_code": 503,
        "content_type": "text/html",
    }


def test_acquisition_failure_accepts_unavailable_http_metadata():
    started_at = datetime(
        2026, 8, 4, 9, tzinfo=UTC
    )
    finished_at = datetime(
        2026, 8, 4, 9, 1, tzinfo=UTC
    )
    result = AcquisitionFailure(
        requested_url="https://example.test/product",
        method=AcquisitionMethod.HTTP,
        started_at=started_at,
        finished_at=finished_at,
        outcome=AcquisitionFailureOutcome.NETWORK_ERROR,
        diagnostic_message="Could not connect to host",
        final_url=None,
        status_code=None,
        content_type=None,
    )

    assert asdict(result) == {
        "requested_url": "https://example.test/product",
        "method": AcquisitionMethod.HTTP,
        "started_at": started_at,
        "finished_at": finished_at,
        "outcome": AcquisitionFailureOutcome.NETWORK_ERROR,
        "diagnostic_message": "Could not connect to host",
        "final_url": None,
        "status_code": None,
        "content_type": None,
    }


def test_acquisition_success_is_immutable():
    started_at = datetime(
        2026, 8, 4, 8, tzinfo=UTC
    )
    finished_at = datetime(
        2026, 8, 4, 8, 1, tzinfo=UTC
    )
    result = AcquisitionSuccess(
        requested_url="https://example.test/product",
        method=AcquisitionMethod.HTTP,
        started_at=started_at,
        finished_at=finished_at,
        final_url="https://example.test/products/123",
        status_code=200,
        content_type="text/html",
        content="<html><body>Product</body></html>",
    )

    with pytest.raises(FrozenInstanceError):
        result.status_code = 201


def test_acquisition_success_rejects_finished_at_before_started_at():
    invalid_started_at = datetime(
        2026, 8, 4, 8, 3, tzinfo=UTC
    )

    with pytest.raises(ValueError):
        make_acquisition_success(
            started_at=invalid_started_at,
        )


def test_acquisition_failure_rejects_finished_at_before_started_at():
    invalid_started_at = datetime(
        2026, 8, 4, 9, 1, tzinfo=UTC
    )

    with pytest.raises(ValueError):
        make_acquisition_failure(
            started_at=invalid_started_at,
        )


def test_acquisition_success_rejects_naive_datetime():
    naive_started_at = datetime(
        2026, 8, 4, 9
    )
    naive_finished_at = datetime(
        2026, 8, 4, 9, 1
    )

    with pytest.raises(ValueError):
        make_acquisition_success(
            started_at=naive_started_at,
            finished_at=naive_finished_at,
        )


def test_acquisition_success_rejects_naive_finished_at():
    naive_finished_at = datetime(
        2026, 8, 4, 9, 1
    )

    with pytest.raises(
        ValueError,
        match="started_at and finished_at must be timezone-aware",
    ):
        make_acquisition_success(
            finished_at=naive_finished_at,
        )


def test_acquisition_failure_rejects_naive_datetime():
    naive_started_at = datetime(
        2026, 8, 4, 9
    )
    naive_finished_at = datetime(
        2026, 8, 4, 9, 1
    )

    with pytest.raises(ValueError):
        make_acquisition_failure(
            started_at=naive_started_at,
            finished_at=naive_finished_at,
        )


def test_acquisition_failure_rejects_empty_diagnostic_message():
    with pytest.raises(
        ValueError,
        match="diagnostic_message must not be empty",
    ):
        make_acquisition_failure(diagnostic_message="")


def test_acquisition_failure_rejects_whitespace_only_diagnostic_message():
    with pytest.raises(
        ValueError,
        match="diagnostic_message must not be empty",
    ):
        make_acquisition_failure(diagnostic_message=" ")


def test_acquisition_success_rejects_non_datetime_timestamp():
    string_started_at = "2026-08-05 08:00:00"

    with pytest.raises(
        TypeError,
        match="started_at and finished_at must be an instance of datetime",
    ):
        make_acquisition_success(
            started_at=string_started_at,
        )


def test_acquisition_success_rejects_status_code_above_http_range():
    with pytest.raises(
        ValueError,
        match="status_code must be between 100 and 599",
    ):
        make_acquisition_success(
            status_code=600,
        )


def test_acquisition_success_rejects_status_code_below_http_range():
    with pytest.raises(
        ValueError,
        match="status_code must be between 100 and 599",
    ):
        make_acquisition_success(
            status_code=99,
        )


def test_acquisition_success_rejects_non_success_status_code():
    with pytest.raises(
        ValueError,
        match="status_code for success must be between 200 and 299",
    ):
        make_acquisition_success(
            status_code=503,
        )


def test_acquisition_failure_rejects_status_code_above_http_range():
    with pytest.raises(
        ValueError,
        match="status_code must be between 100 and 599",
    ):
        make_acquisition_failure(
            status_code=600,
        )
