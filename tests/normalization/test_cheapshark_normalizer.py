from datetime import UTC, datetime
from decimal import Decimal

from market_pipeline.acquisition.models import (
    AcquisitionMethod,
    AcquisitionSuccess,
)
from market_pipeline.extraction.models import (
    CheapSharkDealExtractionFailure,
    CheapSharkExtractionSuccess,
)
from market_pipeline.normalization.cheapshark_normalizer import (
    CheapSharkNormalizer,
)
from market_pipeline.normalization.models import (
    CheapSharkGameRequest,
    CheapSharkNormalizationSuccess,
    NormalizedCheapSharkOffer,
)
from market_pipeline.validation.models import (
    CheapSharkDealValidationFailure,
    CheapSharkValidationSuccess,
    ValidatedCheapSharkDeal,
    ValidatedCheapSharkGameMetadata,
)


def make_acquisition_success() -> AcquisitionSuccess:
    started_at = datetime(2026, 8, 19, 10, 8, tzinfo=UTC)
    finished_at = datetime(2026, 8, 19, 10, 9, tzinfo=UTC)
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


def make_cheapshark_extraction_success() -> CheapSharkExtractionSuccess:
    acquisition = make_acquisition_success()

    return CheapSharkExtractionSuccess(
        acquisition=acquisition,
        raw_game_metadata={},
        deal_results=(),
    )


def make_cheapshark_validation_success(
    title: str = "Batman",
    **overrides,
) -> CheapSharkValidationSuccess:
    extraction = make_cheapshark_extraction_success()
    validated_game_metadata = ValidatedCheapSharkGameMetadata(title=title)

    data = {
        "extraction": extraction,
        "validated_game_metadata": validated_game_metadata,
        "deal_results": (),
    }
    data.update(overrides)

    return CheapSharkValidationSuccess(**data)


def test_cheapshark_normalizer_normalizes_title_with_empty_offer_results() -> None:
    request = CheapSharkGameRequest(game_id=612)
    validation = make_cheapshark_validation_success(title=" Batman ")

    normalizer = CheapSharkNormalizer()

    result = normalizer.normalize(request, validation)

    assert isinstance(result, CheapSharkNormalizationSuccess)
    assert result.request is request
    assert result.validation is validation
    assert result.title == "Batman"
    assert result.offer_results == ()


def test_cheapshark_normalizer_normalizes_validated_deal() -> None:
    request = CheapSharkGameRequest(game_id=612)
    source_mapping = {
        "storeID": " 23 ",
        "price": "12.99",
    }
    validated_deal = ValidatedCheapSharkDeal.model_validate(source_mapping)
    validation = make_cheapshark_validation_success(
        deal_results=(validated_deal,),
    )

    normalizer = CheapSharkNormalizer()

    result = normalizer.normalize(request, validation)

    assert isinstance(result, CheapSharkNormalizationSuccess)
    assert result.request is request
    assert result.validation is validation
    assert result.title == "Batman"
    (normalized_offer,) = result.offer_results
    assert isinstance(normalized_offer, NormalizedCheapSharkOffer)
    assert normalized_offer.store_id == "23"
    assert normalized_offer.price == Decimal("12.99")


def test_cheapshark_normalizer_preserves_ordered_results_and_prior_failures() -> None:
    request = CheapSharkGameRequest(game_id=612)
    source_mapping = {"storeID": "23", "price": "12.99"}
    validated_deal = ValidatedCheapSharkDeal.model_validate(source_mapping)
    extraction_failure = CheapSharkDealExtractionFailure(
        index=0,
        raw=[],
        diagnostic_message="Deal candidate must be a mapping",
    )
    expected_normalized_offer = NormalizedCheapSharkOffer(
        store_id="23",
        price=Decimal("12.99"),
    )

    validation_failure = CheapSharkDealValidationFailure(
        index=2,
        raw={
            "storeID": "",
            "price": "7.33",
        },
        diagnostic_message="store_id must not be empty",
    )

    validation = make_cheapshark_validation_success(
        deal_results=(
            extraction_failure,
            validated_deal,
            validation_failure,
        ),
    )

    expected_offer_results = (
        extraction_failure,
        expected_normalized_offer,
        validation_failure,
    )

    normalizer = CheapSharkNormalizer()

    result = normalizer.normalize(request, validation)

    assert isinstance(result, CheapSharkNormalizationSuccess)
    assert result.request is request
    assert result.validation is validation
    assert result.title == "Batman"
    preserved_extraction, normalized_offer, preserved_validation = (
        result.offer_results
    )
    assert isinstance(preserved_extraction, CheapSharkDealExtractionFailure)
    assert isinstance(normalized_offer, NormalizedCheapSharkOffer)
    assert isinstance(preserved_validation, CheapSharkDealValidationFailure)
    assert preserved_validation is validation_failure
    assert preserved_extraction is extraction_failure
    assert result.offer_results == expected_offer_results
