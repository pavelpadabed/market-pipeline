from datetime import UTC, datetime
from decimal import Decimal

import pytest

from market_pipeline.acquisition.models import (
    AcquisitionMethod,
    AcquisitionSuccess,
)
from market_pipeline.extraction.models import (
    CheapSharkDealExtractionFailure,
    CheapSharkExtractionSuccess,
)
from market_pipeline.normalization.models import (
    CheapSharkGameRequest,
    CheapSharkNormalizationSuccess,
    NormalizedCheapSharkOffer,
    NormalizedCheapSharkStore,
    NormalizedCheapSharkStoreCatalog,
)
from market_pipeline.validation.models import (
    CheapSharkDealValidationFailure,
    CheapSharkStore,
    CheapSharkStoreCatalogSuccess,
    CheapSharkValidationSuccess,
    ValidatedCheapSharkGameMetadata,
)


def make_acquisition_success(**overrides) -> AcquisitionSuccess:
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
    data.update(overrides)

    return AcquisitionSuccess(**data)


def make_cheapshark_extraction_success() -> CheapSharkExtractionSuccess:
    acquisition = make_acquisition_success()

    return CheapSharkExtractionSuccess(
        acquisition=acquisition,
        raw_game_metadata={},
        deal_results=(),
    )


def make_cheapshark_validation_success(
    **overrides,
) -> CheapSharkValidationSuccess:
    extraction = make_cheapshark_extraction_success()
    validated_game_metadata = ValidatedCheapSharkGameMetadata(title="Batman")

    data = {
        "extraction": extraction,
        "validated_game_metadata": validated_game_metadata,
        "deal_results": (),
    }
    data.update(overrides)

    return CheapSharkValidationSuccess(**data)


def test_cheapshark_game_request_preserves_integer_game_id() -> None:
    expected_game_id = 612

    result = CheapSharkGameRequest(game_id=expected_game_id)

    assert result.game_id == expected_game_id


@pytest.mark.parametrize(
    "invalid_game_id",
    [
        "612",
        True,
        False,
        612.50,
        b"612",
    ],
)
def test_cheapshark_game_request_rejects_non_integer_game_id(
    invalid_game_id: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="game_id must have type int",
    ):
        # noinspection PyTypeChecker
        CheapSharkGameRequest(game_id=invalid_game_id)


def test_normalized_cheapshark_offer_preserves_normalized_values() -> None:
    expected_store_id = "23"
    expected_price = Decimal("12.99")

    result = NormalizedCheapSharkOffer(
        store_id=expected_store_id,
        price=expected_price,
    )

    assert result.store_id == expected_store_id
    assert result.price == expected_price


def test_cheapshark_normalization_success_preserves_request_validation_and_normalized_data(
) -> None:
    request = CheapSharkGameRequest(game_id=612)
    validation = make_cheapshark_validation_success()
    title = validation.validated_game_metadata.title

    result = CheapSharkNormalizationSuccess(
        request=request,
        validation=validation,
        title=title,
        offer_results=(),
    )

    assert result.request is request
    assert result.validation is validation
    assert result.title == "Batman"
    assert result.offer_results == ()


def test_cheapshark_normalization_success_preserves_ordered_offer_results() -> None:
    request = CheapSharkGameRequest(game_id=612)
    validation = make_cheapshark_validation_success()
    title = validation.validated_game_metadata.title

    validation_failure = CheapSharkDealValidationFailure(
        index=1,
        raw={
            "storeID": "",
            "price": "12.23",
        },
        diagnostic_message="store_id must not be blank",
    )
    extraction_failure = CheapSharkDealExtractionFailure(
        index=2,
        raw=[],
        diagnostic_message="Deal candidate must be a mapping",
    )
    expected_offer_results = (
        NormalizedCheapSharkOffer(
            store_id="23",
            price=Decimal("12.99"),
        ),
        validation_failure,
        extraction_failure,
    )

    result = CheapSharkNormalizationSuccess(
        request=request,
        validation=validation,
        title=title,
        offer_results=expected_offer_results,
    )

    assert isinstance(result, CheapSharkNormalizationSuccess)
    assert result.request is request
    assert result.validation is validation
    assert result.title == "Batman"
    normalized_offer, preserved_validation, preserved_extraction = (
        result.offer_results
    )
    assert isinstance(normalized_offer, NormalizedCheapSharkOffer)
    assert isinstance(preserved_validation, CheapSharkDealValidationFailure)
    assert isinstance(preserved_extraction, CheapSharkDealExtractionFailure)
    assert preserved_validation is validation_failure
    assert preserved_extraction is extraction_failure
    assert result.offer_results == expected_offer_results


def test_normalized_cheapshark_store_preserves_normalized_values() -> None:
    expected_store_id = "1"
    expected_store_name = "Steam"

    result = NormalizedCheapSharkStore(
        store_id=expected_store_id,
        store_name=expected_store_name,
    )

    assert isinstance(result, NormalizedCheapSharkStore)
    assert result.store_id == expected_store_id
    assert result.store_name == expected_store_name


def test_normalized_cheapshark_store_catalog_preserves_validation_and_ordered_stores() -> None:
    content = (
        '['
            '{"storeID": "1", "storeName": "Steam"},'
            '{"storeID": "2", "storeName": "GamersGate}'
        ']'
    )
    acquisition = make_acquisition_success(content=content)
    validation = CheapSharkStoreCatalogSuccess(
        acquisition=acquisition,
        stores=(
            CheapSharkStore.model_validate(
                {
                    "storeID": "1",
                    "storeName": "Steam",
                },
            ),
            CheapSharkStore.model_validate(
                {
                    "storeID": "2",
                    "storeName": "GamersGate",
                },
            ),
        ),
    )

    result = NormalizedCheapSharkStoreCatalog(
        validation=validation,
        stores=(
            NormalizedCheapSharkStore(
                store_id="1",
                store_name="Steam",
            ),
            NormalizedCheapSharkStore(
                store_id="2",
                store_name="GamersGate",
            ),
        ),
    )

    assert isinstance(result, NormalizedCheapSharkStoreCatalog)
    assert result.validation is validation
    (steam, gamers_gate) = result.stores
    assert steam.store_id == "1"
    assert steam.store_name == "Steam"
    assert gamers_gate.store_id == "2"
    assert gamers_gate.store_name == "GamersGate"
