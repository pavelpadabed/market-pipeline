from datetime import UTC, datetime

from market_pipeline.acquisition.models import (
    AcquisitionMethod,
    AcquisitionSuccess,
)
from market_pipeline.validation.cheapshark_store_catalog_validator import (
    CheapSharkStoreCatalogValidator,
)
from market_pipeline.validation.models import (
    CheapSharkStore,
    CheapSharkStoreCatalogFailure,
    CheapSharkStoreCatalogSuccess,
)


def _make_acquisition_success(content: str) -> AcquisitionSuccess:
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
        "content": content,
    }

    return AcquisitionSuccess(**data)


def test_store_catalog_validator_returns_success_for_valid_catalog() -> None:
    valid_content = (
        '['
        '{"storeID": "1", "storeName": "Steam"},'
        '{"storeID": "2", "storeName": "GamersGate"}'
        ']'
    )
    acquisition = _make_acquisition_success(valid_content)

    validator = CheapSharkStoreCatalogValidator()
    result = validator.validate(acquisition)

    assert isinstance(result, CheapSharkStoreCatalogSuccess)
    assert result.acquisition is acquisition
    steam, gamers_gate = result.stores
    assert isinstance(steam, CheapSharkStore)
    assert isinstance(gamers_gate, CheapSharkStore)
    assert steam.store_id == "1"
    assert steam.store_name == "Steam"
    assert gamers_gate.store_id == "2"
    assert gamers_gate.store_name == "GamersGate"


def test_store_catalog_validator_returns_failure_for_malformed_json() -> None:
    malformed_content = (
        '['
        '{"storeID": "1", "storeName": "Steam"},'
        '{"storeID": "2", "storeName": "GamersGate"}'
    )

    acquisition = _make_acquisition_success(malformed_content)

    validator = CheapSharkStoreCatalogValidator()
    result = validator.validate(acquisition)

    assert isinstance(result, CheapSharkStoreCatalogFailure)
    assert result.acquisition is acquisition
    assert result.diagnostic_message == (
        "Invalid JSON: EOF while parsing a list at line 1 column 83"
    )


def test_store_catalog_validator_returns_failure_when_any_store_is_invalid() -> None:
    content = (
        '['
        '{"storeID": "1", "storeName": "Steam"},'
        '{"storeID": "2", "storeName": ""}'
        ']'
    )
    acquisition = _make_acquisition_success(content)

    validator = CheapSharkStoreCatalogValidator()
    result = validator.validate(acquisition)

    assert isinstance(result, CheapSharkStoreCatalogFailure)
    assert result.acquisition is acquisition
    assert result.diagnostic_message == (
        "1.storeName: Value error, store_name must not be blank"
    )
