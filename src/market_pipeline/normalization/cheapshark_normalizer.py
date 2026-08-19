from decimal import Decimal

from market_pipeline.extraction.models import (
    CheapSharkDealExtractionFailure,
)
from market_pipeline.normalization.models import (
    CheapSharkGameRequest,
    CheapSharkNormalizedOfferResult,
    CheapSharkNormalizationSuccess,
    NormalizedCheapSharkOffer,
)
from market_pipeline.validation.models import (
    CheapSharkDealValidationFailure,
    CheapSharkValidationSuccess,
)


class CheapSharkNormalizer:
    def normalize(
        self,
        request: CheapSharkGameRequest,
        validation: CheapSharkValidationSuccess,
    ) -> CheapSharkNormalizationSuccess:
        title = validation.validated_game_metadata.title.strip()

        deal_results = validation.deal_results

        buffer_offer_results: list[CheapSharkNormalizedOfferResult] = []

        for deal in deal_results:
            if isinstance(deal, CheapSharkDealExtractionFailure):
                buffer_offer_results.append(deal)
                continue
            if isinstance(deal, CheapSharkDealValidationFailure):
                buffer_offer_results.append(deal)
                continue
            store_id = deal.store_id.strip()
            price = Decimal(deal.price)

            normalized_offer = NormalizedCheapSharkOffer(
                store_id=store_id,
                price=price,
            )
            buffer_offer_results.append(normalized_offer)

        return CheapSharkNormalizationSuccess(
            request=request,
            validation=validation,
            title=title,
            offer_results=tuple(buffer_offer_results),
        )
