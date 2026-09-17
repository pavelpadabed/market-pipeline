from pydantic import TypeAdapter, ValidationError

from market_pipeline.acquisition.models import AcquisitionSuccess
from market_pipeline.validation.error_formatting import _format_validation_error
from market_pipeline.validation.models import (
    CheapSharkStore,
    CheapSharkStoreCatalogFailure,
    CheapSharkStoreCatalogResult,
    CheapSharkStoreCatalogSuccess,
)

_STORE_CATALOG_ADAPTER = TypeAdapter(tuple[CheapSharkStore, ...])


class CheapSharkStoreCatalogValidator:
    def validate(
        self,
        acquisition: AcquisitionSuccess,
    ) -> CheapSharkStoreCatalogResult:
        content = acquisition.content
        try:
            stores = _STORE_CATALOG_ADAPTER.validate_json(content)
        except ValidationError as exc:
            diagnostic_message = _format_validation_error(exc)
            return CheapSharkStoreCatalogFailure(
                acquisition=acquisition,
                diagnostic_message=diagnostic_message,
            )

        return CheapSharkStoreCatalogSuccess(
            acquisition=acquisition,
            stores=stores,
        )
