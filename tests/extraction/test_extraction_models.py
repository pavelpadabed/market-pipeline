from datetime import UTC, datetime

import pytest

from market_pipeline.acquisition.models import (
    AcquisitionMethod,
    AcquisitionSuccess,
)
from market_pipeline.extraction.models import (
    CheapSharkDealCandidate,
    CheapSharkDealExtractionFailure,
    CheapSharkExtractionFailure,
    CheapSharkExtractionFailureOutcome,
    CheapSharkExtractionSuccess,
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
        "content_type": "application/json",
        "content": '{"info": {}, "deals": []}',
    }
    data.update(overrides)

    return AcquisitionSuccess(**data)


def test_cheapshark_deal_candidate_accepts_empty_raw_mapping() -> None:
    candidate = CheapSharkDealCandidate(raw={})

    assert candidate.raw == {}


@pytest.mark.parametrize(
    "invalid_raw",
    [
        [],
        "hello",
        None,
    ],
)
def test_cheapshark_deal_candidate_rejects_non_mapping_raw(
    invalid_raw: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="raw must be a mapping",
    ):
        # noinspection PyTypeChecker
        CheapSharkDealCandidate(raw=invalid_raw)


def test_cheapshark_extraction_failure_preserves_acquisition_outcome_and_diagnostic_message(
) -> None:
    acquisition = make_acquisition_success()
    extraction_failure = CheapSharkExtractionFailure(
        acquisition=acquisition,
        outcome=CheapSharkExtractionFailureOutcome.INVALID_JSON,
        diagnostic_message="Acquired content is not valid JSON",
    )

    assert extraction_failure.acquisition is acquisition
    assert extraction_failure.outcome == CheapSharkExtractionFailureOutcome.INVALID_JSON
    assert extraction_failure.diagnostic_message == "Acquired content is not valid JSON"


@pytest.mark.parametrize(
    "invalid_message",
    [
        "",
        " ",
    ],
)
def test_cheapshark_extraction_failure_rejects_blank_diagnostic_message(
    invalid_message: str,
) -> None:
    acquisition = make_acquisition_success()
    with pytest.raises(
        ValueError,
        match="diagnostic_message must not be empty",
    ):
        CheapSharkExtractionFailure(
            acquisition=acquisition,
            outcome=CheapSharkExtractionFailureOutcome.INVALID_JSON,
            diagnostic_message=invalid_message,
        )


def test_cheapshark_deal_extraction_failure_preserves_index_raw_and_diagnostic_message(
) -> None:
    extraction_deal_failure = CheapSharkDealExtractionFailure(
        index=0,
        raw="incorrect",
        diagnostic_message="Deal candidate must be a mapping",
    )

    assert extraction_deal_failure.index == 0
    assert extraction_deal_failure.raw == "incorrect"
    assert extraction_deal_failure.diagnostic_message == (
        "Deal candidate must be a mapping"
    )


@pytest.mark.parametrize(
    "non_integer_index",
    [
        "2",
        True,
        False,
    ],
)
def test_cheapshark_deal_extraction_failure_rejects_non_integer_index(
    non_integer_index: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="index must have type int",
    ):
        # noinspection PyTypeChecker
        CheapSharkDealExtractionFailure(
            index=non_integer_index,
            raw="incorrect",
            diagnostic_message="Deal candidate must be a mapping",
        )


def test_cheapshark_deal_extraction_failure_rejects_negative_index() -> None:
    with pytest.raises(
        ValueError,
        match="index must not be negative",
    ):
        CheapSharkDealExtractionFailure(
            index=-1,
            raw="incorrect",
            diagnostic_message="Deal candidate must be a mapping",
        )


@pytest.mark.parametrize(
    "invalid_message",
    [
        "",
        " ",
    ],
)
def test_cheapshark_deal_extraction_failure_rejects_blank_diagnostic_message(
    invalid_message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="diagnostic_message must not be empty",
    ):
        CheapSharkDealExtractionFailure(
            index=1,
            raw="incorrect",
            diagnostic_message=invalid_message,
        )


def test_extraction_success_accepts_empty_game_metadata_and_deal_results() -> None:
    acquisition = make_acquisition_success()
    extractor_success = CheapSharkExtractionSuccess(
        acquisition=acquisition,
        raw_game_metadata={},
        deal_results=(),
    )

    assert extractor_success.acquisition is acquisition
    assert extractor_success.raw_game_metadata == {}
    assert extractor_success.deal_results == ()
