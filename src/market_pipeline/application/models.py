from dataclasses import dataclass
from enum import StrEnum


class GameSearchFailureOutcome(StrEnum):
    INVALID_SOURCE_RESPONSE = "invalid_source_response"
    CONNECTION_FAILED = "connection_failed"
    SEARCH_REQUEST_FAILED = "search_request_failed"
    RATE_LIMITED = "rate_limited"


class LatestOffersReportOutcome(StrEnum):
    NO_CURRENT_OFFERS = "no_current_offers"
    STORE_CATALOG_UNAVAILABLE = "store_catalog_unavailable"
    REPORT_SAVED = "report_saved"


class RunPipelineOutcome(StrEnum):
    OFFERS_SAVED = "offers_saved"
    NO_OFFERS = "no_offers"
    OFFERS_PARTIALLY_SAVED = "offers_partially_saved"
    ALL_OFFERS_REJECTED = "all_offers_rejected"
    PROCESSING_FAILED = "processing_failed"
    CONNECTION_ERROR = "connection_error"
    RATE_LIMITED = "rate_limited"


@dataclass(frozen=True, slots=True)
class GameSearchCandidate:
    game_id: int
    title: str


@dataclass(frozen=True, slots=True)
class GameSearchSuccess:
    candidates: tuple[GameSearchCandidate, ...]


@dataclass(frozen=True, slots=True)
class GameSearchFailure:
    outcome: GameSearchFailureOutcome
    retry_after_seconds: int | None = None

    def __post_init__(self) -> None:
        if (
            self.outcome != GameSearchFailureOutcome.RATE_LIMITED
            and self.retry_after_seconds is not None
        ):
            raise ValueError(
                "retry_after_seconds must be None unless outcome is rate_limited"
            )


type GameSearchResult = (
    GameSearchSuccess
    | GameSearchFailure
)


@dataclass(frozen=True)
class RunPipelineResult:
    outcome: RunPipelineOutcome
    retry_after_seconds: int | None
    source_record_count: int | None
    saved_observation_count: int | None
    rejected_record_count: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, RunPipelineOutcome):
            raise TypeError("outcome must be an instance of RunPipelineOutcome")
        if (
            self.retry_after_seconds is not None
            and type(self.retry_after_seconds) is not int
        ):
            raise TypeError("retry_after_seconds must have type int or be None")
        if (
            self.retry_after_seconds is not None
            and self.retry_after_seconds < 0
        ):
            raise ValueError("retry_after_seconds must be non-negative")
        if (
            self.source_record_count is not None
            and type(self.source_record_count) is not int
        ):
            raise TypeError("source_record_count must have type int or be None")
        if (
            self.source_record_count is not None
            and self.source_record_count < 0
        ):
            raise ValueError("source_record_count must be non-negative")
        if (
            self.saved_observation_count is not None
            and type(self.saved_observation_count) is not int
        ):
            raise TypeError("saved_observation_count must have type int or be None")
        if (
            self.saved_observation_count is not None
            and self.saved_observation_count < 0
        ):
            raise ValueError("saved_observation_count must be non-negative")
        if (
            self.rejected_record_count is not None
            and type(self.rejected_record_count) is not int
        ):
            raise TypeError("rejected_record_count must have type int or be None")
        if (
            self.rejected_record_count is not None
            and self.rejected_record_count < 0
        ):
            raise ValueError("rejected_record_count must be non-negative")
        match self.outcome:
            case (
                RunPipelineOutcome.PROCESSING_FAILED
                | RunPipelineOutcome.CONNECTION_ERROR
                | RunPipelineOutcome.RATE_LIMITED
            ) if (
                self.source_record_count is not None
                or self.saved_observation_count is not None
                or self.rejected_record_count is not None
            ):
                raise ValueError(
                    "counts must be None when per-record processing did not complete"
                )
            case (
                RunPipelineOutcome.OFFERS_SAVED
                | RunPipelineOutcome.NO_OFFERS
                | RunPipelineOutcome.OFFERS_PARTIALLY_SAVED
                | RunPipelineOutcome.ALL_OFFERS_REJECTED
            ):
                if (
                    self.source_record_count is None
                    or self.saved_observation_count is None
                    or self.rejected_record_count is None
                ):
                    raise ValueError(
                        "counts must be provided when per-record processing completed"
                    )
                if (
                    self.saved_observation_count
                    + self.rejected_record_count
                    != self.source_record_count
                ):
                    raise ValueError(
                        "source_record_count must equal saved_observation_count "
                        "plus rejected_record_count"
                    )

        if (
            self.outcome == RunPipelineOutcome.OFFERS_SAVED
            and (
                self.rejected_record_count != 0
                or self.saved_observation_count == 0
            )
        ):
            raise ValueError("offers_saved requires saved > 0 and rejected = 0")
        if self.outcome == RunPipelineOutcome.NO_OFFERS and (
            self.source_record_count != 0
            or self.saved_observation_count != 0
            or self.rejected_record_count != 0
        ):
            raise ValueError("counts must be zero when outcome is no_offers")
        if (
            self.outcome == RunPipelineOutcome.OFFERS_PARTIALLY_SAVED
            and (
                self.saved_observation_count == 0
                or self.rejected_record_count == 0
            )
        ):
            raise ValueError(
                "offers_partially_saved requires saved > 0 and rejected > 0"
            )
        if (
            self.outcome == RunPipelineOutcome.ALL_OFFERS_REJECTED
            and (
                self.saved_observation_count != 0
                or self.rejected_record_count == 0
            )
        ):
            raise ValueError(
                "all_offers_rejected requires saved = 0 and rejected > 0"
            )
        if (
            self.outcome != RunPipelineOutcome.RATE_LIMITED
            and self.retry_after_seconds is not None
        ):
            raise ValueError(
                "retry_after_seconds must be None unless outcome is rate_limited"
            )


@dataclass(frozen=True, slots=True)
class LatestOffersReportResult:
    outcome: LatestOffersReportOutcome
    exported_offer_count: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, LatestOffersReportOutcome):
            raise TypeError(
                "outcome must be an instance of LatestOffersReportOutcome"
            )
        if (
            self.exported_offer_count is not None
            and type(self.exported_offer_count) is not int
        ):
            raise TypeError("exported_offer_count must have type int or be None")
        if (
            self.exported_offer_count is not None
            and self.exported_offer_count <= 0
        ):
            raise ValueError("exported_offer_count must be positive when provided")
        if (
            self.outcome is LatestOffersReportOutcome.REPORT_SAVED
            and self.exported_offer_count is None
        ):
            raise ValueError(
                "exported_offer_count is required when outcome is report_saved"
            )
        if (
            self.outcome is not LatestOffersReportOutcome.REPORT_SAVED
            and self.exported_offer_count is not None
        ):
            raise ValueError(
                "exported_offer_count must be None when report is not saved"
            )
