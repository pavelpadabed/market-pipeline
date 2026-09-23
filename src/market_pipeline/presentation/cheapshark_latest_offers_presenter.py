from market_pipeline.persistence.queries import (
    CurrentOffer,
)

from market_pipeline.normalization.models import (
    NormalizedCheapSharkStoreCatalog,
)

from market_pipeline.presentation.models import LatestOfferReportRow


class CheapSharkLatestOffersPresenter:
    def present(
        self,
        current_offers: tuple[CurrentOffer, ...],
        catalog: NormalizedCheapSharkStoreCatalog,
    ) -> tuple[LatestOfferReportRow, ...]:
        store_names_by_id = {}
        for store in catalog.stores:
            store_names_by_id[store.store_id] = store.store_name

        report_rows: list[LatestOfferReportRow] = []
        for offer in current_offers:
            report_row = LatestOfferReportRow(
                product_title=offer.product_title,
                store_name=(
                    store_names_by_id.get(
                        offer.source_seller_id,
                        f"Unknown store ({offer.source_seller_id})",
                    )
                ),
                price=offer.price,
                currency=offer.currency,
                observed_at=offer.observed_at,
            )
            report_rows.append(report_row)

        return tuple(report_rows)
