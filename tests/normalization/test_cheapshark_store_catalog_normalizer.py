from datetime import UTC, datetime

from market_pipeline.acquisition.models import (
    AcquisitionMethod,
    AcquisitionSuccess,
)
from market_pipeline.normalization.cheapshark_store_catalog_normalizer import (
    CheapSharkStoreCatalogNormalizer,
)
from market_pipeline.normalization.models import (
    NormalizedCheapSharkStore,
    NormalizedCheapSharkStoreCatalog,
)
from market_pipeline.validation.models import (
    CheapSharkStore,
    CheapSharkStoreCatalogSuccess,
)


def _make_acquisition_success(**overrides) -> AcquisitionSuccess:
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


def test_cheapshark_store_catalog_normalizer_normalizes_stores_in_source_order() -> None:
    content = (
        '['
        '{"storeID": "1", "storeName": "Steam"},'
        '{"storeID": "2", "storeName": " GamersGate "}'
        ']'
    )
    acquisition = _make_acquisition_success(content=content)
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
                    "storeName": " GamersGate ",
                },
            ),
        ),
    )
    expected_stores = (
        NormalizedCheapSharkStore(
            store_id="1",
            store_name="Steam",
        ),
        NormalizedCheapSharkStore(
            store_id="2",
            store_name="GamersGate",
        ),
    )
    normalizer = CheapSharkStoreCatalogNormalizer()
    actual_result = normalizer.normalize(validation)

    assert isinstance(actual_result, NormalizedCheapSharkStoreCatalog)
    assert actual_result.validation is validation
    assert actual_result.stores == expected_stores


def test_cheapshark_store_catalog_normalizer_preserves_empty_catalog() -> None:
    acquisition = _make_acquisition_success(content="[]")
    validation = CheapSharkStoreCatalogSuccess(
        acquisition=acquisition,
        stores=(),
    )
    normalizer = CheapSharkStoreCatalogNormalizer()

    result = normalizer.normalize(validation)

    assert isinstance(result, NormalizedCheapSharkStoreCatalog)
    assert result.validation is validation
    assert result.stores == ()
