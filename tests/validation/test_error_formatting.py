import pytest
from pydantic import TypeAdapter, ValidationError

from market_pipeline.validation.error_formatting import _format_validation_error
from market_pipeline.validation.models import (
    CheapSharkStore,
    ValidatedCheapSharkDeal,
    ValidatedCheapSharkGameMetadata,
)


def test_format_validation_error_formats_missing_title_diagnostic_message() -> None:
    expected_message = "title: Field required"
    with pytest.raises(ValidationError) as exc:
        ValidatedCheapSharkGameMetadata.model_validate({})
    actual_message = _format_validation_error(exc.value)

    assert actual_message == expected_message


def test_format_validation_error_formats_multiple_field_diagnostics() -> None:
    expected_message = (
        "storeID: Field required\n"
        "price: Field required"
    )
    with pytest.raises(ValidationError) as exc:
        ValidatedCheapSharkDeal.model_validate({})
    actual_message = _format_validation_error(exc.value)

    assert actual_message == expected_message


def test_format_validation_error_omits_location_separator_when_location_is_empty() -> None:
    malformed_content = (
        '['
        '{"storeID": "1", "storeName": "Steam"},'
        '{"storeID": "2", "storeName": "GamersGate"}'
    )
    adapter = TypeAdapter(tuple[CheapSharkStore, ...])

    with pytest.raises(ValidationError) as exc:
        adapter.validate_json(malformed_content)
    expected_message = exc.value.errors()[0]["msg"]
    actual_message = _format_validation_error(exc.value)

    assert actual_message == expected_message
