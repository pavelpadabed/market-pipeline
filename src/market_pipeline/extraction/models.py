from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from market_pipeline.acquisition.models import AcquisitionSuccess


class CheapSharkExtractionFailureOutcome(StrEnum):
    INVALID_JSON = "invalid_json"
    ROOT_NOT_MAPPING = "root_not_mapping"
    INFO_MISSING = "info_missing"
    INFO_NOT_MAPPING = "info_not_mapping"
    DEALS_MISSING = "deals_missing"
    DEALS_NOT_LIST = "deals_not_list"


@dataclass(frozen=True, slots=True)
class CheapSharkDealCandidate:
    raw: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.raw, Mapping):
            raise TypeError("raw must be a mapping")


@dataclass(frozen=True, slots=True)
class CheapSharkDealExtractionFailure:
    index: int
    raw: object
    diagnostic_message: str

    def __post_init__(self) -> None:
        if type(self.index) is not int:
            raise TypeError("index must have type int")
        if self.index < 0:
            raise ValueError("index must not be negative")
        if not self.diagnostic_message.strip():
            raise ValueError("diagnostic_message must not be empty")


type CheapSharkDealResult = (
    CheapSharkDealCandidate
    | CheapSharkDealExtractionFailure
)


@dataclass(frozen=True, slots=True)
class CheapSharkExtractionSuccess:
    acquisition: AcquisitionSuccess
    raw_game_metadata: Mapping[str, object]
    deal_results: tuple[CheapSharkDealResult, ...]


@dataclass(frozen=True, slots=True)
class CheapSharkExtractionFailure:
    acquisition: AcquisitionSuccess
    outcome: CheapSharkExtractionFailureOutcome
    diagnostic_message: str

    def __post_init__(self) -> None:
        if not self.diagnostic_message.strip():
            raise ValueError("diagnostic_message must not be empty")


type CheapSharkExtractionResult = (
    CheapSharkExtractionSuccess
    | CheapSharkExtractionFailure
)
