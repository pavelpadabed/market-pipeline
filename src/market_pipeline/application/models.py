from dataclasses import dataclass
from enum import StrEnum


class GameSearchFailureOutcome(StrEnum):
    INVALID_SOURCE_RESPONSE = "invalid_source_response"
    CONNECTION_FAILED = "connection_failed"
    SEARCH_REQUEST_FAILED = "search_request_failed"
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
