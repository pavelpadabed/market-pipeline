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
        current_offers = self.query.get_current_offers(
            self._SOURCE,
            external_product_id,
        )

        if not current_offers:
            return LatestOffersReportOutcome.NO_CURRENT_OFFERS

        acquisition = self.acquirer.acquire()
        if isinstance(acquisition, AcquisitionFailure):
            return LatestOffersReportOutcome.STORE_CATALOG_UNAVAILABLE

        validation = self.validator.validate(acquisition)
        if isinstance(validation, CheapSharkStoreCatalogFailure):
            return LatestOffersReportOutcome.STORE_CATALOG_UNAVAILABLE

        normalization = self.normalizer.normalize(validation)

        if not normalization.stores:
            return LatestOffersReportOutcome.STORE_CATALOG_UNAVAILABLE

        latest_offers = self.presenter.present(
            current_offers,
            normalization,
        )

        self.exporter.export(latest_offers, path)

        return LatestOffersReportOutcome.REPORT_SAVED
