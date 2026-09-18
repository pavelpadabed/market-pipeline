from market_pipeline.normalization.models import (
    NormalizedCheapSharkStore,
    NormalizedCheapSharkStoreCatalog,
)
from market_pipeline.validation.models import (
    CheapSharkStoreCatalogSuccess,
)


class CheapSharkStoreCatalogNormalizer:
    def normalize(
        self,
        validation: CheapSharkStoreCatalogSuccess,
    ) -> NormalizedCheapSharkStoreCatalog:
        buffered_stores: list[NormalizedCheapSharkStore] = []

        for valid_store in validation.stores:
            store_name = valid_store.store_name.strip()
            normalized_store = NormalizedCheapSharkStore(
                store_id=valid_store.store_id,
                store_name=store_name,
            )
            buffered_stores.append(normalized_store)

        return NormalizedCheapSharkStoreCatalog(
            validation=validation,
            stores=tuple(buffered_stores),
        )
