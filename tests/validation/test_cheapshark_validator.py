from datetime import UTC, datetime

from market_pipeline.acquisition.models import (
    AcquisitionMethod,
    AcquisitionSuccess,
)
from market_pipeline.extraction.models import (
    CheapSharkDealCandidate,
    CheapSharkDealExtractionFailure,
    CheapSharkExtractionSuccess,
)
from market_pipeline.validation.cheapshark_validator import CheapSharkValidator
from market_pipeline.validation.models import (
    CheapSharkDealValidationFailure,
    CheapSharkValidationFailure,
    CheapSharkValidationSuccess,
    ValidatedCheapSharkDeal,
)


def make_acquisition_success() -> AcquisitionSuccess:
    started_at = datetime(
        2026, 8, 18, 11, 6, tzinfo=UTC
    )
    finished_at = datetime(
        2026, 8, 18, 11, 7, tzinfo=UTC
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

    return AcquisitionSuccess(**data)


def make_cheapshark_extraction_success(**overrides) -> CheapSharkExtractionSuccess:
    acquisition = make_acquisition_success()

    data = {
        "acquisition": acquisition,
        "raw_game_metadata": {},
        "deal_results": (),
    }
    data.update(overrides)

    return CheapSharkExtractionSuccess(**data)


def test_validator_preserves_valid_game_metadata_and_empty_deal_results() -> None:
    extraction = make_cheapshark_extraction_success(
        raw_game_metadata={"title": "Batman"},
    )
    validator = CheapSharkValidator()

    result = validator.validate(extraction)

    assert isinstance(result, CheapSharkValidationSuccess)
    assert result.extraction is extraction
    assert result.validated_game_metadata.title == "Batman"
    assert result.deal_results == ()


def test_cheapshark_validator_returns_failure_for_invalid_game_metadata() -> None:
    extraction = make_cheapshark_extraction_success(
        raw_game_metadata={},
    )
    validator = CheapSharkValidator()

    result = validator.validate(extraction)

    assert isinstance(result, CheapSharkValidationFailure)
    assert result.extraction is extraction
    assert result.diagnostic_message == "title: Field required"


def test_cheapshark_validator_validates_deal_candidate() -> None:
    candidate = CheapSharkDealCandidate(
        raw={
            "storeID": "23",
            "price": "12.23",
        },
    )

    extraction = make_cheapshark_extraction_success(
        raw_game_metadata={"title": "Batman"},
        deal_results=(candidate,),
    )

    validator = CheapSharkValidator()
    result = validator.validate(extraction)

    assert isinstance(result, CheapSharkValidationSuccess)
    assert result.validated_game_metadata.title == "Batman"
    assert len(result.deal_results) == 1
    (valid_deal,) = result.deal_results
    assert isinstance(valid_deal, ValidatedCheapSharkDeal)
    assert valid_deal.store_id == "23"
    assert valid_deal.price == "12.23"


def test_validator_returns_deal_validation_failure_for_invalid_candidate() -> None:
    candidate = CheapSharkDealCandidate(
        raw={},
    )
    extraction = make_cheapshark_extraction_success(
        raw_game_metadata={"title": "Batman"},
        deal_results=(candidate,),
    )

    validator = CheapSharkValidator()
    result = validator.validate(extraction)
    expected_message = (
        "storeID: Field required\n"
        "price: Field required"
    )

    assert isinstance(result, CheapSharkValidationSuccess)
    assert result.validated_game_metadata.title == "Batman"
    assert len(result.deal_results) == 1
    (invalid_deal,) = result.deal_results
    assert isinstance(invalid_deal, CheapSharkDealValidationFailure)
    assert invalid_deal.index == 0
    assert invalid_deal.raw is candidate.raw
    assert invalid_deal.diagnostic_message == expected_message


def test_cheapshark_validator_preserves_deal_extraction_failure() -> None:
    candidate = CheapSharkDealExtractionFailure(
        index=2,
        raw=[],
        diagnostic_message="invalid mapping",
    )
    extraction = make_cheapshark_extraction_success(
        raw_game_metadata={"title": "Batman"},
        deal_results=(candidate,),
    )

    validator = CheapSharkValidator()
    result = validator.validate(extraction)

    assert isinstance(result, CheapSharkValidationSuccess)
    assert result.validated_game_metadata.title == "Batman"
    assert len(result.deal_results) == 1
    (extraction_failure,) = result.deal_results
    assert extraction_failure.index == 2
    assert extraction_failure.raw is candidate.raw
    assert extraction_failure.diagnostic_message == "invalid mapping"


def test_validator_preserves_deal_result_order_and_partial_failures() -> None:
    valid_candidate = CheapSharkDealCandidate(
        raw={
            "storeID": "23",
            "price": "12.23",
        },
    )

    extraction_failure = CheapSharkDealExtractionFailure(
        index=1,
        raw=[],
        diagnostic_message="invalid mapping",
    )

    invalid_candidate = CheapSharkDealCandidate(
        raw={
            "storeID": None,
            "price": "12.99",
        },
    )

    extraction = make_cheapshark_extraction_success(
        raw_game_metadata={"title": "Batman"},
        deal_results=(
            valid_candidate,
            extraction_failure,
            invalid_candidate,
        ),
    )
    validator = CheapSharkValidator()
    result = validator.validate(extraction)

    assert isinstance(result, CheapSharkValidationSuccess)
    assert result.extraction is extraction
    assert result.validated_game_metadata.title == "Batman"
    assert len(result.deal_results) == 3
    validated_deal, preserved_extraction_failure, invalid_deal = result.deal_results

    assert isinstance(validated_deal, ValidatedCheapSharkDeal)
    assert validated_deal.store_id == "23"
    assert validated_deal.price == "12.23"

    assert preserved_extraction_failure is extraction_failure

    assert isinstance(invalid_deal, CheapSharkDealValidationFailure)
    assert invalid_deal.index == 2
    assert invalid_deal.raw is invalid_candidate.raw
    assert (
        invalid_deal.diagnostic_message
        == "storeID: Input should be a valid string"
    )
