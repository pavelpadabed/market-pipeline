from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Never
from zoneinfo import ZoneInfo

from market_pipeline.acquisition.models import (
    AcquisitionFailure,
    AcquisitionFailureOutcome,
    AcquisitionMethod,
    AcquisitionResult,
    AcquisitionSuccess,
)
from market_pipeline.application.latest_offers_report import (
    GenerateCheapSharkLatestOffersReport,
)
from market_pipeline.application.models import LatestOffersReportOutcome
from market_pipeline.normalization.cheapshark_store_catalog_normalizer import (
    CheapSharkStoreCatalogNormalizer,
)
from market_pipeline.normalization.models import (
    NormalizedCheapSharkStoreCatalog,
)
from market_pipeline.persistence.queries import CurrentOffer
from market_pipeline.presentation.cheapshark_latest_offers_presenter import (
    CheapSharkLatestOffersPresenter,
)
from market_pipeline.presentation.models import LatestOfferReportRow
from market_pipeline.validation.cheapshark_store_catalog_validator import (
    CheapSharkStoreCatalogValidator,
)
from market_pipeline.validation.models import CheapSharkStoreCatalogSuccess

SOURCE = "cheapshark"
WARSAW = ZoneInfo("Europe/Warsaw")
STARTED_AT = datetime(
    2026,
    10,
    27,
    10,
    5,
    tzinfo=WARSAW,
)
FINISHED_AT = datetime(
    2026,
    10,
    27,
    10,
    6,
    tzinfo=WARSAW,
)
EXTERNAL_PRODUCT_ID = 612


def _make_acquisition_success(content: str) -> AcquisitionSuccess:
    data = {
        "requested_url": "https://example.test/stores",
        "method": AcquisitionMethod.HTTP,
        "started_at": STARTED_AT,
        "finished_at": FINISHED_AT,
        "final_url": "https://example.test/stores",
        "status_code": 200,
        "content_type": "application/json",
        "content": content,
    }
    return AcquisitionSuccess(**data)


def _make_acquisition_failure() -> AcquisitionFailure:
    data = {
        "requested_url": "https://example.test/stores",
        "method": AcquisitionMethod.HTTP,
        "started_at": STARTED_AT,
        "finished_at": FINISHED_AT,
        "outcome": AcquisitionFailureOutcome.NETWORK_ERROR,
        "diagnostic_message": "HTTP connection failed",
        "final_url": None,
        "status_code": None,
        "content_type": None,
        "retry_after_seconds": None,
    }
    return AcquisitionFailure(**data)


def _make_current_offer() -> CurrentOffer:
    return CurrentOffer(
        product_title="Batman",
        source_seller_id="1",
        observed_at=FINISHED_AT,
        price=Decimal("12.99"),
        currency="USD",
    )


class FakeOfferQuery:
    def __init__(self, result: tuple[CurrentOffer, ...]) -> None:
        self.result = result
        self.called_source: str | None = None
        self.called_external_product_id: int | None = None

    def get_current_offers(
        self,
        source: str,
        external_product_id: int,
    ) -> tuple[CurrentOffer, ...]:
        self.called_source = source
        self.called_external_product_id = external_product_id
        return self.result


class FakeStoresAcquirer:
    def __init__(self, result: AcquisitionResult) -> None:
        self.result = result
        self.called = False

    def acquire(self) -> AcquisitionResult:
        self.called = True
        return self.result


class FakeExporter:
    def __init__(self) -> None:
        self.called_report_rows: tuple[LatestOfferReportRow, ...] | None = None
        self.called_path: Path | None = None

    def export(
        self,
        report_rows: tuple[LatestOfferReportRow, ...],
        path: Path,
    ) -> None:
        self.called_report_rows = report_rows
        self.called_path = path


class UnexpectedCallValidator:
    def validate(self, acquisition: AcquisitionResult) -> Never:
        raise AssertionError("validator must not be called")


class UnexpectedCallNormalizer:
    def normalize(self, validation: CheapSharkStoreCatalogSuccess) -> Never:
        raise AssertionError("normalizer must not be called")


class UnexpectedCallPresenter:
    def present(
        self,
        current_offers: tuple[CurrentOffer, ...],
        catalog: NormalizedCheapSharkStoreCatalog,
    ) -> Never:
        raise AssertionError("presenter must not be called")


def test_generate_latest_offers_report_returns_report_saved() -> None:
    report_path = Path("/reports/batman.xlsx")
    current_offers = (_make_current_offer(),)
    fake_query = FakeOfferQuery(current_offers)

    content = '[{"storeID": "1", "storeName": "Steam"}]'
    acquisition_result = _make_acquisition_success(content)
    fake_acquirer = FakeStoresAcquirer(acquisition_result)

    stores_validator = CheapSharkStoreCatalogValidator()
    stores_normalizer = CheapSharkStoreCatalogNormalizer()

    presenter = CheapSharkLatestOffersPresenter()

    fake_exporter = FakeExporter()

    report_generator = GenerateCheapSharkLatestOffersReport(
        fake_query,
        fake_acquirer,
        stores_validator,
        stores_normalizer,
        presenter,
        fake_exporter,
    )

    outcome = report_generator.execute(
        EXTERNAL_PRODUCT_ID,
        report_path,
    )

    expected_rows = (
        LatestOfferReportRow(
            product_title="Batman",
            store_name="Steam",
            price=Decimal("12.99"),
            currency="USD",
            observed_at=FINISHED_AT,
        ),
    )

    assert fake_query.called_source == SOURCE
    assert fake_query.called_external_product_id == EXTERNAL_PRODUCT_ID

    assert fake_acquirer.called is True

    assert fake_exporter.called_report_rows == expected_rows
    assert fake_exporter.called_path == report_path

    assert outcome is LatestOffersReportOutcome.REPORT_SAVED


def test_generate_latest_offers_report_returns_no_current_offers() -> None:
    report_path = Path("/reports/batman.xlsx")
    current_offers = ()
    fake_query = FakeOfferQuery(current_offers)

    content = '[{"storeID": "1", "storeName": "Steam"}]'
    acquisition_result = _make_acquisition_success(content)
    fake_acquirer = FakeStoresAcquirer(acquisition_result)

    stores_validator = CheapSharkStoreCatalogValidator()
    stores_normalizer = CheapSharkStoreCatalogNormalizer()

    presenter = CheapSharkLatestOffersPresenter()

    fake_exporter = FakeExporter()

    report_generator = GenerateCheapSharkLatestOffersReport(
        fake_query,
        fake_acquirer,
        stores_validator,
        stores_normalizer,
        presenter,
        fake_exporter,
    )

    outcome = report_generator.execute(
        EXTERNAL_PRODUCT_ID,
        report_path,
    )

    assert fake_query.called_source == SOURCE
    assert fake_query.called_external_product_id == EXTERNAL_PRODUCT_ID

    assert fake_acquirer.called is False

    assert fake_exporter.called_report_rows is None
    assert fake_exporter.called_path is None

    assert outcome is LatestOffersReportOutcome.NO_CURRENT_OFFERS


def test_generate_latest_offers_report_returns_store_catalog_unavailable_on_acquisition_failure(
) -> None:
    report_path = Path("/reports/batman.xlsx")
    current_offers = (_make_current_offer(),)
    fake_query = FakeOfferQuery(current_offers)

    acquisition_result = _make_acquisition_failure()
    fake_acquirer = FakeStoresAcquirer(acquisition_result)

    unexpected_validator = UnexpectedCallValidator()
    stores_normalizer = CheapSharkStoreCatalogNormalizer()

    presenter = CheapSharkLatestOffersPresenter()

    fake_exporter = FakeExporter()

    report_generator = GenerateCheapSharkLatestOffersReport(
        fake_query,
        fake_acquirer,
        unexpected_validator,
        stores_normalizer,
        presenter,
        fake_exporter,
    )

    outcome = report_generator.execute(
        EXTERNAL_PRODUCT_ID,
        report_path,
    )

    assert fake_query.called_source == SOURCE
    assert fake_query.called_external_product_id == EXTERNAL_PRODUCT_ID

    assert fake_acquirer.called is True

    assert fake_exporter.called_report_rows is None
    assert fake_exporter.called_path is None

    assert outcome is LatestOffersReportOutcome.STORE_CATALOG_UNAVAILABLE

def test_generate_latest_offers_report_returns_store_catalog_unavailable_on_validation_failure(
) -> None:
    report_path = Path("/reports/batman.xlsx")
    current_offers = (_make_current_offer(),)
    fake_query = FakeOfferQuery(current_offers)

    content = '[{"storeID": "1", "storeName": "   "}]'
    acquisition_result = _make_acquisition_success(content)
    fake_acquirer = FakeStoresAcquirer(acquisition_result)

    stores_validator = CheapSharkStoreCatalogValidator()
    unexpected_normalizer = UnexpectedCallNormalizer()

    presenter = CheapSharkLatestOffersPresenter()

    fake_exporter = FakeExporter()

    report_generator = GenerateCheapSharkLatestOffersReport(
        fake_query,
        fake_acquirer,
        stores_validator,
        unexpected_normalizer,
        presenter,
        fake_exporter,
    )

    outcome = report_generator.execute(
        EXTERNAL_PRODUCT_ID,
        report_path,
    )

    assert fake_query.called_source == SOURCE
    assert fake_query.called_external_product_id == EXTERNAL_PRODUCT_ID

    assert fake_acquirer.called is True

    assert fake_exporter.called_report_rows is None
    assert fake_exporter.called_path is None

    assert outcome is LatestOffersReportOutcome.STORE_CATALOG_UNAVAILABLE


def test_generate_latest_offers_report_returns_store_catalog_unavailable_on_empty_catalog(
) -> None:
    report_path = Path("/reports/batman.xlsx")
    current_offers = (_make_current_offer(),)
    fake_query = FakeOfferQuery(current_offers)

    acquisition_result = _make_acquisition_success("[]")
    fake_acquirer = FakeStoresAcquirer(acquisition_result)

    stores_validator = CheapSharkStoreCatalogValidator()
    stores_normalizer = CheapSharkStoreCatalogNormalizer()

    unexpected_presenter = UnexpectedCallPresenter()

    fake_exporter = FakeExporter()

    report_generator = GenerateCheapSharkLatestOffersReport(
        fake_query,
        fake_acquirer,
        stores_validator,
        stores_normalizer,
        unexpected_presenter,
        fake_exporter,
    )

    outcome = report_generator.execute(
        EXTERNAL_PRODUCT_ID,
        report_path,
    )

    assert fake_query.called_source == SOURCE
    assert fake_query.called_external_product_id == EXTERNAL_PRODUCT_ID

    assert fake_acquirer.called is True

    assert fake_exporter.called_report_rows is None
    assert fake_exporter.called_path is None

    assert outcome is LatestOffersReportOutcome.STORE_CATALOG_UNAVAILABLE
