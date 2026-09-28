from collections.abc import Mapping
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from market_pipeline.acquisition.models import (
    AcquisitionMethod,
    AcquisitionSuccess,
)
from market_pipeline.extraction.models import (
    CheapSharkDealExtractionFailure,
    CheapSharkExtractionSuccess,
)
from market_pipeline.validation.models import (
    CheapSharkDealValidationFailure,
    CheapSharkGameCandidate,
    CheapSharkGameSearchFailure,
    CheapSharkGameSearchSuccess,
    CheapSharkStore,
    CheapSharkStoreCatalogFailure,
    CheapSharkStoreCatalogSuccess,
    CheapSharkValidationFailure,
    CheapSharkValidationSuccess,
    ValidatedCheapSharkDeal,
    ValidatedCheapSharkGameMetadata,
)

GAME_SEARCH_REQUESTED_URL = "https://www.cheapshark.com/api/1.0/games?title=Batman"
GAME_SEARCH_FINAL_URL = "https://www.cheapshark.com/api/1.0/games?title=Batman"
GAME_SEARCH_CONTENT = '[{"gameID": "1", "external": "Batman"}]'


def make_acquisition_success(**overrides: object) -> AcquisitionSuccess:
    started_at = datetime(
        2026, 8, 17, 17, tzinfo=UTC
    )
    finished_at = datetime(
        2026, 8, 17, 17, 1, tzinfo=UTC
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


def _make_acquisition_success_for_game_search() -> AcquisitionSuccess:
    return make_acquisition_success(
        requested_url=GAME_SEARCH_REQUESTED_URL,
        final_url=GAME_SEARCH_FINAL_URL,
        content=GAME_SEARCH_CONTENT,
    )


def make_cheapshark_extraction_success() -> CheapSharkExtractionSuccess:
    acquisition = make_acquisition_success()

    return CheapSharkExtractionSuccess(
        acquisition=acquisition,
        raw_game_metadata={},
        deal_results=(),
    )


@pytest.mark.parametrize(
    ("title",),
    [
        pytest.param("Batman: Arkham City", id="without-surrounding-whitespace"),
        pytest.param("  Batman: Arkham City  ", id="with-surrounding-whitespace"),
    ],
)
def test_validated_cheapshark_game_metadata_preserves_valid_title(
    title: str,
) -> None:
    result = ValidatedCheapSharkGameMetadata(title=title)

    assert result.title == title


@pytest.mark.parametrize(
    "invalid_type",
    [
        None,
        True,
        13,
        b"Batman",
    ],
)
def test_validated_cheapshark_game_metadata_rejects_non_string_title(
    invalid_type: object,
) -> None:
    with pytest.raises(ValidationError):
        # noinspection PyTypeChecker
        ValidatedCheapSharkGameMetadata(title=invalid_type)


@pytest.mark.parametrize(
    "blank_title",
    [
        "",
        " ",
        "\t",
        "\n",
        " \t\n ",
    ],
)
def test_validated_cheapshark_game_metadata_rejects_blank_title(
    blank_title: str,
) -> None:
    with pytest.raises(ValidationError):
        ValidatedCheapSharkGameMetadata(title=blank_title)


def test_validated_cheapshark_game_metadata_rejects_missing_title() -> None:
    with pytest.raises(ValidationError):
        ValidatedCheapSharkGameMetadata()


def test_validated_cheapshark_game_metadata_ignores_unknown_fields() -> None:
    raw_game_metadata = {
        "title": "Batman",
        "steamAppID": "21000",
        "thumb": "https://...",
    }

    result = ValidatedCheapSharkGameMetadata.model_validate(raw_game_metadata)

    assert result.model_dump() == {"title": "Batman"}


def test_validated_cheapshark_deal_maps_store_id_source_alias() -> None:
    source_mapping = {"storeID": "23", "price": "12.99"}

    result = ValidatedCheapSharkDeal.model_validate(source_mapping)

    assert result.store_id == "23"


def test_validated_cheapshark_deal_preserves_valid_price() -> None:
    source_mapping = {"storeID": "23", "price": "12.99"}

    result = ValidatedCheapSharkDeal.model_validate(source_mapping)

    assert result.price == "12.99"


@pytest.mark.parametrize(
    "field_name",
    [
        "storeID",
        "price",
    ],
    ids=("store_field", "price_field"),
)
@pytest.mark.parametrize(
    "invalid_type",
    [
        None,
        True,
        123,
        b"23",
    ],
)
def test_validated_cheapshark_deal_rejects_non_string_field_value(
    field_name: str,
    invalid_type: object,
) -> None:
    source_mapping: dict[str, object] = {
        "storeID": "23",
        "price": "12.99",
    }
    source_mapping[field_name] = invalid_type
    with pytest.raises(ValidationError):
        ValidatedCheapSharkDeal.model_validate(source_mapping)


@pytest.mark.parametrize(
    "invalid_store_id",
    [
        "",
        " ",
        "\n",
        "\t",
        "\n\t",
        "abc",
        "-1",
        "1.5",
        "1e2",
    ],
)
def test_validated_cheapshark_deal_rejects_invalid_store_id_format(
    invalid_store_id: str,
) -> None:
    source_mapping = {
        "storeID": invalid_store_id,
        "price": "12.99",
    }
    with pytest.raises(ValidationError):
        ValidatedCheapSharkDeal.model_validate(source_mapping)


def test_validated_cheapshark_deal_preserves_surrounding_whitespace_in_store_id() -> None:
    source_mapping = {
        "storeID": " 23 ",
        "price": "12.99",
    }

    result = ValidatedCheapSharkDeal.model_validate(source_mapping)

    assert result.store_id == " 23 "


def test_validated_cheapshark_deal_rejects_non_numeric_price() -> None:
    source_mapping = {
        "storeID": "23",
        "price": "hello",
    }
    with pytest.raises(
        ValidationError,
        match="price must be a numeric string",
    ):
        ValidatedCheapSharkDeal.model_validate(source_mapping)


@pytest.mark.parametrize(
    "non_finite_value",
    [
        "NaN",
        "Infinity",
        "-Infinity",
    ],
)
def test_validated_cheapshark_deal_rejects_non_finite_price(
    non_finite_value: str,
) -> None:
    source_mapping = {
        "storeID": "23",
        "price": non_finite_value,
    }
    with pytest.raises(
        ValidationError,
        match="price must be a finite number",
    ):
        ValidatedCheapSharkDeal.model_validate(source_mapping)


def test_validated_cheapshark_deal_rejects_negative_price() -> None:
    source_mapping = {
        "storeID": "23",
        "price": "-13.26",
    }
    with pytest.raises(
        ValidationError,
        match="price must be non-negative",
    ):
        ValidatedCheapSharkDeal.model_validate(source_mapping)


def test_validated_cheapshark_deal_accepts_zero_price() -> None:
    source_mapping = {
        "storeID": "23",
        "price": "0",
    }
    result = ValidatedCheapSharkDeal.model_validate(source_mapping)

    assert result.price == "0"


@pytest.mark.parametrize(
    "source_mapping",
    [
        {"price": "12.99"},
        {"storeID": "23"},
    ],
    ids=("without_store_id", "without_price"),
)
def test_validated_cheapshark_deal_rejects_missing_required_field(
    source_mapping: Mapping[str, str],
) -> None:
    with pytest.raises(ValidationError):
        ValidatedCheapSharkDeal.model_validate(source_mapping)


def test_validated_cheapshark_deal_ignores_unknown_fields() -> None:
    source_mapping = {
        "storeID": "23",
        "price": "12.99",
        "retailPrice": "19.99",
        "savings": "78.839420",
    }
    result = ValidatedCheapSharkDeal.model_validate(source_mapping)

    assert result.model_dump() == {"store_id": "23", "price": "12.99"}


def test_deal_validation_failure_preserves_raw_index_and_diagnostic_message(
) -> None:
    raw = {}

    result = CheapSharkDealValidationFailure(
        index=0,
        raw=raw,
        diagnostic_message="invalid data",
    )

    assert result.index == 0
    assert result.raw is raw
    assert result.diagnostic_message == "invalid data"


@pytest.mark.parametrize(
    "blank_diagnostic_message",
    [
        "",
        " ",
        "\n",
        "\t",
        "\n\t",
    ],
)
def test_cheapshark_deal_validation_failure_rejects_blank_diagnostic_message(
    blank_diagnostic_message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="diagnostic_message must not be empty",
    ):
        CheapSharkDealValidationFailure(
            index=1,
            raw={},
            diagnostic_message=blank_diagnostic_message,
        )


@pytest.mark.parametrize(
    "invalid_index_type",
    [
        "hello",
        True,
        False,
        None,
    ],
)
def test_cheapshark_deal_validation_failure_rejects_non_integer_index(
    invalid_index_type: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="index must have type int",
    ):
        # noinspection PyTypeChecker
        CheapSharkDealValidationFailure(
            index=invalid_index_type,
            raw={},
            diagnostic_message="Invalid deal",
        )


def test_cheapshark_deal_validation_failure_rejects_negative_index() -> None:
    with pytest.raises(
        ValueError,
        match="index must not be negative",
    ):
        CheapSharkDealValidationFailure(
            index=-1,
            raw={},
            diagnostic_message="Invalid deal",
        )


def test_cheapshark_validation_success_preserves_extraction_metadata_and_deal_results(
) -> None:
    extraction = make_cheapshark_extraction_success()
    game_metadata = ValidatedCheapSharkGameMetadata(title="Batman")
    result = CheapSharkValidationSuccess(
        extraction=extraction,
        validated_game_metadata=game_metadata,
        deal_results=(),
    )
    assert result.extraction is extraction
    assert result.validated_game_metadata is game_metadata
    assert result.deal_results == ()


def test_cheapshark_validation_success_preserves_ordered_deal_results() -> None:
    extraction = make_cheapshark_extraction_success()
    game_metadata = ValidatedCheapSharkGameMetadata(title="Batman")
    source_mapping = {"storeID": "24", "price": "12.99"}
    expected_results = (
        ValidatedCheapSharkDeal.model_validate(source_mapping),
        CheapSharkDealValidationFailure(
            index=1,
            raw={
                "storeID": "23",
                "price": "Infinity",
            },
            diagnostic_message="price must be a finite number",
        ),
        CheapSharkDealExtractionFailure(
            index=2,
            raw="incorrect",
            diagnostic_message="Deal candidate must be a mapping",
        ),
    )

    result = CheapSharkValidationSuccess(
        extraction=extraction,
        validated_game_metadata=game_metadata,
        deal_results=expected_results,
    )

    assert result.deal_results == expected_results


def test_validation_failure_preserves_extraction_and_diagnostic_message() -> None:
    extraction = make_cheapshark_extraction_success()
    result = CheapSharkValidationFailure(
        extraction=extraction,
        diagnostic_message="invalid game metadata",
    )

    assert result.extraction is extraction
    assert result.diagnostic_message == "invalid game metadata"


@pytest.mark.parametrize(
    "blank_diagnostic_message",
    [
        "",
        " ",
        "\n",
        "\t",
        "\n\t",
    ],
)
def test_cheapshark_validation_failure_rejects_blank_diagnostic_message(
    blank_diagnostic_message: str,
) -> None:
    extraction = make_cheapshark_extraction_success()

    with pytest.raises(
        ValueError,
        match="diagnostic_message must not be empty",
    ):
        CheapSharkValidationFailure(
            extraction=extraction,
            diagnostic_message=blank_diagnostic_message,
        )


def test_cheapshark_store_maps_source_fields_to_python_attributes() -> None:
    source_mapping = {
        "storeID": "1",
        "storeName": "Steam",
    }
    result = CheapSharkStore.model_validate(source_mapping)

    assert result.store_id == "1"
    assert result.store_name == "Steam"


@pytest.mark.parametrize(
    "field_name",
    ["storeID", "storeName"],
)
@pytest.mark.parametrize(
    "invalid_type",
    [None, 13, True, b"13"],
)
def test_cheapshark_store_rejects_non_string_source_field_value(
    field_name: str, invalid_type: object,
) -> None:
    source_mapping: dict[str, object] = {"storeID": "1", "storeName": "Steam"}
    source_mapping[field_name] = invalid_type
    with pytest.raises(ValidationError):
        CheapSharkStore.model_validate(source_mapping)


def test_cheapshark_store_ignores_unknown_source_fields() -> None:
    source_mapping = {
        "storeID": "1",
        "storeName": "Steam",
        "isActive": 1,
        "images": {
            "banner": "/img/stores/banners/0.png",
            "logo": "/img/stores/logos/0.png",
            "icon": "/img/stores/icons/0.png",
        },
    }
    expected_result = {
        "store_id": "1",
        "store_name": "Steam",
    }
    actual_result = CheapSharkStore.model_validate(source_mapping)

    assert actual_result.model_dump() == expected_result


@pytest.mark.parametrize(
    "invalid_store_id",
    [
        "",
        " ",
        "abc",
        "-1",
        "1.5",
        "1e2",
    ],
)
def test_cheapshark_store_rejects_invalid_store_id_format(
    invalid_store_id: str,
) -> None:
    source_mapping = {"storeID": invalid_store_id, "storeName": "Steam"}

    with pytest.raises(ValidationError):
        CheapSharkStore.model_validate(source_mapping)


@pytest.mark.parametrize(
    "blank_store_name",
    [
        "",
        " ",
        "\t",
        "\n",
        "\t\n",
    ],
)
def test_cheapshark_store_rejects_blank_store_name(
    blank_store_name: str,
) -> None:
    source_mapping = {"storeID": "1", "storeName": blank_store_name}

    with pytest.raises(ValidationError):
        CheapSharkStore.model_validate(source_mapping)


def test_cheapshark_store_preserves_surrounding_whitespace_in_store_name() -> None:
    source_mapping = {"storeID": "1", "storeName": " Steam "}
    result = CheapSharkStore.model_validate(source_mapping)

    assert result.store_name == " Steam "


def test_cheapshark_store_catalog_success_preserves_acquisition_and_stores() -> None:
    acquisition = make_acquisition_success()
    expected_stores = (
        CheapSharkStore.model_validate(
            {
                "storeID": "1",
                "storeName": "Steam",
            }
        ),
        CheapSharkStore.model_validate(
            {
                "storeID": "2",
                "storeName": "GamersGate",
            }
        ),
    )

    result = CheapSharkStoreCatalogSuccess(
        acquisition=acquisition,
        stores=expected_stores,
    )

    assert result.acquisition is acquisition
    assert result.stores == expected_stores


def test_store_catalog_failure_preserves_acquisition_and_diagnostic_message() -> None:
    acquisition = make_acquisition_success()
    diagnostic_message = "store_id must contain only ASCII decimal digits"

    result = CheapSharkStoreCatalogFailure(
        acquisition=acquisition,
        diagnostic_message=diagnostic_message,
    )

    assert result.acquisition is acquisition
    assert result.diagnostic_message == diagnostic_message


@pytest.mark.parametrize(
    "blank_diagnostic_message",
    [
        "",
        " ",
        "\n",
        "\t",
        "\n\t",
    ],
)
def test_store_catalog_failure_rejects_blank_diagnostic_message(
    blank_diagnostic_message: str,
) -> None:
    acquisition = make_acquisition_success()

    with pytest.raises(
        ValueError,
        match="diagnostic_message must not be empty",
    ):
        CheapSharkStoreCatalogFailure(
            acquisition=acquisition,
            diagnostic_message=blank_diagnostic_message,
        )


def test_cheapshark_game_candidate_maps_source_fields_to_python_attributes() -> None:
    source_mapping = {"gameID": "1", "external": "Batman"}

    candidate = CheapSharkGameCandidate.model_validate(source_mapping)

    assert candidate.game_id == "1"
    assert candidate.title == "Batman"


@pytest.mark.parametrize(
    "field_name",
    ["gameID", "external"],
)
@pytest.mark.parametrize(
    "invalid_type",
    [None, 13, 13.3, True, b"13"],
)
def test_cheapshark_game_candidate_rejects_non_string_source_field_value(
    field_name: str,
    invalid_type: object,
) -> None:
    source_mapping: dict[str, object] = {
        "gameID": "1",
        "external": "Batman",
    }
    source_mapping[field_name] = invalid_type

    with pytest.raises(ValidationError):
        CheapSharkGameCandidate.model_validate(source_mapping)


@pytest.mark.parametrize(
    "invalid_game_id",
    [
        "",
        " ",
        "abc",
        "-1",
        "1.5",
        "1e2",
        "١٢٣",
    ],
)
def test_cheapshark_game_candidate_rejects_invalid_game_id_format(
    invalid_game_id: str,
) -> None:
    source_mapping = {
        "gameID": invalid_game_id,
        "external": "Batman",
    }

    with pytest.raises(ValidationError):
        CheapSharkGameCandidate.model_validate(source_mapping)


def test_cheapshark_game_candidate_preserves_surrounding_whitespace_in_game_id() -> None:
    source_mapping = {
        "gameID": " 1 ",
        "external": "Batman",
    }

    candidate = CheapSharkGameCandidate.model_validate(source_mapping)

    assert candidate.game_id == " 1 "


@pytest.mark.parametrize(
    "blank_title",
    [
        "",
        " ",
        "\t",
        "\n",
        " \t\n ",
    ],
)
def test_cheapshark_game_candidate_rejects_blank_title(
    blank_title: str,
) -> None:
    source_mapping = {
        "gameID": "1",
        "external": blank_title,
    }

    with pytest.raises(
        ValidationError,
        match="title must not be blank",
    ):
        CheapSharkGameCandidate.model_validate(source_mapping)


def test_cheapshark_game_candidate_preserves_surrounding_whitespace_in_title() -> None:
    source_mapping = {
        "gameID": "1",
        "external": " Batman ",
    }

    candidate = CheapSharkGameCandidate.model_validate(source_mapping)

    assert candidate.title == " Batman "


def test_cheapshark_game_candidate_ignores_unknown_source_fields() -> None:
    source_mapping = {
        "gameID": "107598",
        "steamAppID": "208650",
        "cheapest": "3.99",
        "cheapestDealID": "%2BRR8iNYa2ZB%2FIhfZml8B1USYGhQVeYAv0Tl8JPkZ8UM%3D",
        "external": "Batman: Arkham Knight",
        "internalName": "BATMANARKHAMKNIGHT",
        "thumb": (
            "https://cdn.cloudflare.steamstatic.com/steam/apps/208650/"
            "capsule_sm_120.jpg?t=1681938976"
        ),
    }
    expected_result = {
        "game_id": "107598",
        "title": "Batman: Arkham Knight",
    }

    candidate = CheapSharkGameCandidate.model_validate(source_mapping)

    assert candidate.model_dump() == expected_result


def test_cheapshark_game_search_success_preserves_acquisition_and_games() -> None:
    acquisition = make_acquisition_success(
        requested_url=GAME_SEARCH_REQUESTED_URL,
        final_url=GAME_SEARCH_FINAL_URL,
        content=GAME_SEARCH_CONTENT,
    )
    source_mapping = {"gameID": "1", "external": "Batman"}
    candidate = CheapSharkGameCandidate.model_validate(source_mapping)

    expected_games = (candidate,)

    result = CheapSharkGameSearchSuccess(
        acquisition=acquisition,
        games=expected_games,
    )

    assert isinstance(result, CheapSharkGameSearchSuccess)
    assert result.acquisition is acquisition
    assert result.games == expected_games


def test_cheapshark_game_search_failure_preserves_acquisition_and_diagnostic_message() -> None:
    acquisition = _make_acquisition_success_for_game_search()
    diagnostic_message = "game_id must contain only ASCII decimal digits"

    result = CheapSharkGameSearchFailure(
        acquisition=acquisition,
        diagnostic_message=diagnostic_message,
    )

    assert isinstance(result, CheapSharkGameSearchFailure)
    assert result.acquisition is acquisition
    assert result.diagnostic_message == diagnostic_message


@pytest.mark.parametrize(
    "blank_diagnostic_message",
    [
        "",
        " ",
        "\t",
        "\n",
        " \t\n ",
    ],
)
def test_cheapshark_game_search_failure_rejects_blank_diagnostic_message(
    blank_diagnostic_message: str,
) -> None:
    acquisition = _make_acquisition_success_for_game_search()

    with pytest.raises(
        ValueError,
        match="diagnostic_message must not be empty",
    ):
        CheapSharkGameSearchFailure(
            acquisition=acquisition,
            diagnostic_message=blank_diagnostic_message,
        )
