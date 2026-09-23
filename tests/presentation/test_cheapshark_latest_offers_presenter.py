from datetime import UTC, datetime
from decimal import Decimal

from market_pipeline.acquisition.models import (
    AcquisitionMethod,
    AcquisitionSuccess,
)

from market_pipeline.validation.models import (
    CheapSharkStore,
    CheapSharkStoreCatalogFailure,
    CheapSharkStoreCatalogSuccess,
)

from market_pipeline.persistence.queries import (
    CurrentOffer,
)

from market_pipeline.normalization.models import (
    NormalizedCheapSharkStore,
    NormalizedCheapSharkStoreCatalog,
)
from market_pipeline.presentation.cheapshark_latest_offers_presenter import (
    CheapSharkLatestOffersPresenter,
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


def _make_normalized_store_catalog() -> NormalizedCheapSharkStoreCatalog:
    content = '[{"storeID": "1", "storeName": "Steam"}]'
    acquisition = _make_acquisition_success(content)
    store = CheapSharkStore.model_validate(
        {
            "storeID": "1",
            "storeName": "Steam",
        }
    )
    validation = CheapSharkStoreCatalogSuccess(
        acquisition=acquisition,
        stores=(store,),
    )
    normalized_store = NormalizedCheapSharkStore(
        store_id="1",
        store_name="Steam",
    )
    return NormalizedCheapSharkStoreCatalog(
        validation=validation,
        stores=(normalized_store,),
    )


def test_present_resolves_known_store_name() -> None:
    observed_at = datetime(
        2026, 8, 17, 17, 1, tzinfo=UTC
    )
    current_offer = CurrentOffer(
        product_title="Batman",
        source_seller_id="1",
        observed_at=observed_at,
        price=Decimal("12.99"),
        currency="USD",
    )

    content = '[{"storeID": "1", "storeName": "Steam"}]'
    acquisition = _make_acquisition_success(content)
    store = CheapSharkStore.model_validate(
        {
            "storeID": "1",
            "storeName": "Steam",
        }
    )
    validation = CheapSharkStoreCatalogSuccess(
        acquisition=acquisition,
        stores=(store,),
    )
    normalized_store = NormalizedCheapSharkStore(
        store_id="1",
        store_name="Steam",
    )

    normalization = NormalizedCheapSharkStoreCatalog(
        validation=validation,
        stores=(normalized_store,),
    )

    presenter = CheapSharkLatestOffersPresenter()
    result = presenter.present((current_offer,), normalization)

    report_row, = result
    assert report_row.product_title == "Batman"
    assert report_row.store_name == "Steam"
    assert report_row.price == Decimal("12.99")
    assert report_row.currency == "USD"
    assert report_row.observed_at == observed_at


def test_present_uses_fallback_for_unknown_source_seller_id() -> None:
    observed_at = datetime(
        2026, 8, 17, 17, 1, tzinfo=UTC
    )
    current_offer = CurrentOffer(
        product_title="Batman",
        source_seller_id="999",
        observed_at=observed_at,
        price=Decimal("12.99"),
        currency="USD",
    )
    catalog = _make_normalized_store_catalog()

    presenter = CheapSharkLatestOffersPresenter()

    result = presenter.present((current_offer,), catalog)

    report_row, = result

    assert report_row.store_name == "Unknown store (999)"


def test_present_returns_empty_tuple_for_empty_current_offers() -> None:
    current_offers = ()

    catalog = _make_normalized_store_catalog()

    presenter = CheapSharkLatestOffersPresenter()

    result = presenter.present(current_offers, catalog)

    assert result == ()


def test_present_preserves_current_offer_order() -> None:
    observed_at = datetime(
        2026, 8, 17, 17, 1, tzinfo=UTC
    )
    first_current_offer = CurrentOffer(
        product_title="Batman",
        source_seller_id="1",
        observed_at=observed_at,
        price=Decimal("12.99"),
        currency="USD",
    )
    second_current_offer = CurrentOffer(
        product_title="The Witcher 3",
        source_seller_id="1",
        observed_at=observed_at,
        price=Decimal("8.99"),
        currency="USD",
    )
    catalog = _make_normalized_store_catalog()
    presenter = CheapSharkLatestOffersPresenter()

    result = presenter.present(
        (
            first_current_offer,
            second_current_offer,
        ),
        catalog,
    )

    first_report_row, second_report_row = result

    assert first_report_row.product_title == "Batman"
    assert first_report_row.price == Decimal("12.99")

    assert second_report_row.product_title == "The Witcher 3"
    assert second_report_row.price == Decimal("8.99")
