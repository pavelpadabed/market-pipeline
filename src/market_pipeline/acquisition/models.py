from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AcquisitionMethod(StrEnum):
    HTTP = "http"
    BROWSER = "browser"


class AcquisitionFailureOutcome(StrEnum):
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    REQUEST_ERROR = "request_error"
    HTTP_ERROR = "http_error"
    BLOCKED = "blocked"
    UNEXPECTED_CONTENT = "unexpected_content"
    BROWSER_ERROR = "browser_error"


def _validate_timestamps(
    started_at: datetime,
    finished_at: datetime,
) -> None:
    if not all(
        isinstance(value, datetime)
        for value in (started_at, finished_at)
    ):
        raise TypeError(
            "started_at and finished_at must be an instance of datetime"
        )
    if not all(
        value.tzinfo is not None
        and value.utcoffset() is not None
        for value in (started_at, finished_at)
    ):
        raise ValueError(
            "started_at and finished_at must be timezone-aware"
        )
    if finished_at < started_at:
        raise ValueError(
            "finished_at must not be before started_at"
        )


def _validate_http_status_code(status_code: int) -> None:
    if not 100 <= status_code <= 599:
        raise ValueError(
            "status_code must be between 100 and 599"
        )


@dataclass(frozen=True, slots=True)
class AcquisitionSuccess:
    requested_url: str
    method: AcquisitionMethod
    started_at: datetime
    finished_at: datetime
    final_url: str
    status_code: int
    content_type: str | None
    content: str

    def __post_init__(self) -> None:
        _validate_timestamps(
            self.started_at,
            self.finished_at,
        )
        _validate_http_status_code(self.status_code)

        if not 200 <= self.status_code <= 299:
            raise ValueError(
                "status_code for success must be between 200 and 299"
            )


@dataclass(frozen=True, slots=True)
class AcquisitionFailure:
    requested_url: str
    method: AcquisitionMethod
    started_at: datetime
    finished_at: datetime
    outcome: AcquisitionFailureOutcome
    diagnostic_message: str
    final_url: str | None
    status_code: int | None
    content_type: str | None

    def __post_init__(self) -> None:
        _validate_timestamps(
            self.started_at,
            self.finished_at,
        )

        if not self.diagnostic_message.strip():
            raise ValueError(
                "diagnostic_message must not be empty"
            )

        if self.status_code is not None:
            _validate_http_status_code(self.status_code)


type AcquisitionResult = AcquisitionSuccess | AcquisitionFailure
