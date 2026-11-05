import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

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
from market_pipeline.normalization.cheapshark_store_catalog_normalizer import (
    CheapSharkStoreCatalogNormalizer,
)
from market_pipeline.persistence.queries import CurrentOffer
from market_pipeline.presentation.cheapshark_latest_offers_presenter import (
    CheapSharkLatestOffersPresenter,
)
from market_pipeline.presentation.models import LatestOfferReportRow
from market_pipeline.validation.cheapshark_store_catalog_validator import (
    CheapSharkStoreCatalogValidator,
)

WARSAW = ZoneInfo("Europe/Warsaw")
STARTED_AT = datetime(
    2026,
    11,
    5,
    10,
    4,
    tzinfo=WARSAW,
)
FINISHED_AT = datetime(
    2026,
    11,
    5,
    10,
    5,
    tzinfo=WARSAW,
)
EXTERNAL_PRODUCT_ID = 612
REPORT_PATH = Path("/reports/batman.xlsx")


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

    def get_current_offers(
        self,
        source: str,
        external_product_id: int,
    ) -> tuple[CurrentOffer, ...]:
        return self.result


class FakeStoresAcquirer:
    def __init__(self, result: AcquisitionResult) -> None:
        self.result = result

    def acquire(self) -> AcquisitionResult:
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


def _make_report_generator(
    current_offers: tuple[CurrentOffer, ...],
    acquisition_result: AcquisitionResult,
) -> GenerateCheapSharkLatestOffersReport:
    fake_query = FakeOfferQuery(current_offers)
    fake_acquirer = FakeStoresAcquirer(acquisition_result)
    stores_validator = CheapSharkStoreCatalogValidator()
    stores_normalizer = CheapSharkStoreCatalogNormalizer()
    presenter = CheapSharkLatestOffersPresenter()
    fake_exporter = FakeExporter()

    return GenerateCheapSharkLatestOffersReport(
        fake_query,
        fake_acquirer,
        stores_validator,
        stores_normalizer,
        presenter,
        fake_exporter,
    )


def test_latest_offers_report_logs_report_saved(
    caplog: pytest.LogCaptureFixture,
) -> None:
    current_offers = (_make_current_offer(),)
    content = '[{"storeID": "1", "storeName": "Steam"}]'
    acquisition_result = _make_acquisition_success(content)
    report_generator = _make_report_generator(
        current_offers,
        acquisition_result,
    )

    with caplog.at_level(
        logging.INFO,
        logger="market_pipeline.application.latest_offers_report",
    ):
        report_generator.execute(
            EXTERNAL_PRODUCT_ID,
            REPORT_PATH,
        )

    records = [
        record
        for record in caplog.records
        if record.name == "market_pipeline.application.latest_offers_report"
    ]

    assert len(records) == 2
    started, saved = records
    assert started.levelname == "INFO"
    assert started.getMessage() == (
        'event="latest offers report generation started" '
        "external_product_id=612"
    )
    assert saved.levelname == "INFO"
    assert saved.getMessage() == (
        'event="latest offers report saved" '
        "external_product_id=612 "
        "output_file_name=batman.xlsx"
    )


def test_latest_offers_report_logs_no_current_offers(
    caplog: pytest.LogCaptureFixture,
) -> None:
    content = '[{"storeID": "1", "storeName": "Steam"}]'
    acquisition_result = _make_acquisition_success(content)
    report_generator = _make_report_generator(
        (),
        acquisition_result,
    )

    with caplog.at_level(
        logging.INFO,
        logger="market_pipeline.application.latest_offers_report",
    ):
        report_generator.execute(
            EXTERNAL_PRODUCT_ID,
            REPORT_PATH,
        )

    records = [
        record
        for record in caplog.records
        if record.name == "market_pipeline.application.latest_offers_report"
    ]

    assert len(records) == 2
    started, not_generated = records
    assert started.levelname == "INFO"
    assert started.getMessage() == (
        'event="latest offers report generation started" '
        "external_product_id=612"
    )
    assert not_generated.levelname == "INFO"
    assert not_generated.getMessage() == (
        'event="latest offers report not generated" '
        "external_product_id=612 "
        "outcome=no_current_offers"
    )


def test_latest_offers_report_logs_acquisition_failure_as_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    current_offers = (_make_current_offer(),)
    acquisition_failure = AcquisitionFailure(
        requested_url="https://example.test/stores",
        method=AcquisitionMethod.HTTP,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        outcome=AcquisitionFailureOutcome.HTTP_ERROR,
        diagnostic_message="HTTP request returned status 429",
        final_url=None,
        status_code=429,
        content_type=None,
        retry_after_seconds=60,
    )
    report_generator = _make_report_generator(
        current_offers,
        acquisition_failure,
    )

    with caplog.at_level(
        logging.ERROR,
        logger="market_pipeline.application.latest_offers_report",
    ):
        report_generator.execute(
            EXTERNAL_PRODUCT_ID,
            REPORT_PATH,
        )

    records = [
        record
        for record in caplog.records
        if record.name == "market_pipeline.application.latest_offers_report"
    ]

    assert len(records) == 1
    acquisition, = records
    assert acquisition.levelname == "ERROR"
    assert acquisition.getMessage() == (
        'event="latest offers report store catalog acquisition failed" '
        "external_product_id=612 "
        "acquisition_outcome=http_error "
        "diagnostic_message='HTTP request returned status 429' "
        "status_code=429 "
        "retry_after_seconds=60"
    )


def test_latest_offers_report_logs_validation_failure_as_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    current_offers = (_make_current_offer(),)
    content = '[{"storeID": "1", "storeName": "   "}]'
    acquisition_result = _make_acquisition_success(content)
    report_generator = _make_report_generator(
        current_offers,
        acquisition_result,
    )

    with caplog.at_level(
        logging.ERROR,
        logger="market_pipeline.application.latest_offers_report",
    ):
        report_generator.execute(
            EXTERNAL_PRODUCT_ID,
            REPORT_PATH,
        )

    records = [
        record
        for record in caplog.records
        if record.name == "market_pipeline.application.latest_offers_report"
    ]

    assert len(records) == 1
    validation, = records
    assert validation.levelname == "ERROR"
    assert validation.getMessage() == (
        'event="latest offers report store catalog validation failed" '
        "external_product_id=612 "
        "diagnostic_message="
        "'0.storeName: Value error, store_name must not be blank'"
    )


def test_latest_offers_report_logs_empty_store_catalog_as_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    current_offers = (_make_current_offer(),)
    acquisition_result = _make_acquisition_success("[]")
    report_generator = _make_report_generator(
        current_offers,
        acquisition_result,
    )

    with caplog.at_level(
        logging.ERROR,
        logger="market_pipeline.application.latest_offers_report",
    ):
        report_generator.execute(
            EXTERNAL_PRODUCT_ID,
            REPORT_PATH,
        )

    records = [
        record
        for record in caplog.records
        if record.name == "market_pipeline.application.latest_offers_report"
    ]

    assert len(records) == 1
    empty_catalog, = records
    assert empty_catalog.levelname == "ERROR"
    assert empty_catalog.getMessage() == (
        'event="latest offers report not generated: store catalog is empty" '
        "external_product_id=612"
    )
