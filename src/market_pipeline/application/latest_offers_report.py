import logging
from pathlib import Path

from market_pipeline.acquisition.cheapshark_stores_acquirer import (
    CheapSharkStoresAcquirer,
)
from market_pipeline.acquisition.models import AcquisitionFailure
from market_pipeline.application.models import LatestOffersReportOutcome
from market_pipeline.export.excel_latest_offers_exporter import (
    ExcelLatestOffersExporter,
)
from market_pipeline.normalization.cheapshark_store_catalog_normalizer import (
    CheapSharkStoreCatalogNormalizer,
)
from market_pipeline.persistence.queries import SqlAlchemyOfferQuery
from market_pipeline.presentation.cheapshark_latest_offers_presenter import (
    CheapSharkLatestOffersPresenter,
)
from market_pipeline.validation.cheapshark_store_catalog_validator import (
    CheapSharkStoreCatalogValidator,
)
from market_pipeline.validation.models import CheapSharkStoreCatalogFailure

logger = logging.getLogger(__name__)


class GenerateCheapSharkLatestOffersReport:
    _SOURCE = "cheapshark"

    def __init__(
        self,
        query: SqlAlchemyOfferQuery,
        acquirer: CheapSharkStoresAcquirer,
        validator: CheapSharkStoreCatalogValidator,
        normalizer: CheapSharkStoreCatalogNormalizer,
        presenter: CheapSharkLatestOffersPresenter,
        exporter: ExcelLatestOffersExporter,
    ) -> None:
        self.query = query
        self.acquirer = acquirer
        self.validator = validator
        self.normalizer = normalizer
        self.presenter = presenter
        self.exporter = exporter

    def execute(
        self,
        external_product_id: int,
        path: Path,
    ) -> LatestOffersReportOutcome:
        logger.info(
            'event="latest offers report generation started" '
            "external_product_id=%s",
            external_product_id,
        )
        current_offers = self.query.get_current_offers(
            self._SOURCE,
            external_product_id,
        )

        if not current_offers:
            outcome = LatestOffersReportOutcome.NO_CURRENT_OFFERS
            logger.info(
                'event="latest offers report not generated" '
                "external_product_id=%s "
                "outcome=%s",
                external_product_id,
                outcome,
            )
            return outcome

        acquisition = self.acquirer.acquire()
        if isinstance(acquisition, AcquisitionFailure):
            logger.error(
                'event="latest offers report store catalog acquisition failed" '
                "external_product_id=%s "
                "acquisition_outcome=%s "
                "diagnostic_message=%r "
                "status_code=%s "
                "retry_after_seconds=%s",
                external_product_id,
                acquisition.outcome,
                acquisition.diagnostic_message,
                acquisition.status_code,
                acquisition.retry_after_seconds,
            )
            return LatestOffersReportOutcome.STORE_CATALOG_UNAVAILABLE

        validation = self.validator.validate(acquisition)
        if isinstance(validation, CheapSharkStoreCatalogFailure):
            logger.error(
                'event="latest offers report store catalog validation failed" '
                "external_product_id=%s "
                "diagnostic_message=%r",
                external_product_id,
                validation.diagnostic_message,
            )
            return LatestOffersReportOutcome.STORE_CATALOG_UNAVAILABLE

        normalization = self.normalizer.normalize(validation)

        if not normalization.stores:
            logger.error(
                'event="latest offers report not generated: store catalog is empty" '
                "external_product_id=%s",
                external_product_id,
            )
            return LatestOffersReportOutcome.STORE_CATALOG_UNAVAILABLE

        latest_offers = self.presenter.present(
            current_offers,
            normalization,
        )

        self.exporter.export(latest_offers, path)

        logger.info(
            'event="latest offers report saved" '
            "external_product_id=%s "
            "output_file_name=%s",
            external_product_id,
            path.name,
        )

        return LatestOffersReportOutcome.REPORT_SAVED
