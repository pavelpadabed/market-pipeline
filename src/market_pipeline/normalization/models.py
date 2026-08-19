from dataclasses import dataclass
from decimal import Decimal

from market_pipeline.extraction.models import (
    CheapSharkDealExtractionFailure,
)
from market_pipeline.validation.models import (
    CheapSharkDealValidationFailure,
    CheapSharkValidationSuccess,
)


@dataclass(frozen=True, slots=True)
class CheapSharkGameRequest:
    game_id: int

    def __post_init__(self) -> None:
        if type(self.game_id) is not int:
            raise TypeError("game_id must have type int")


@dataclass(frozen=True, slots=True)
class NormalizedCheapSharkOffer:
    store_id: str
    price: Decimal


type CheapSharkNormalizedOfferResult = (
    NormalizedCheapSharkOffer
    | CheapSharkDealValidationFailure
    | CheapSharkDealExtractionFailure
)


@dataclass(frozen=True, slots=True)
class CheapSharkNormalizationSuccess:
    request: CheapSharkGameRequest
    validation: CheapSharkValidationSuccess
    title: str
    offer_results: tuple[CheapSharkNormalizedOfferResult, ...]
