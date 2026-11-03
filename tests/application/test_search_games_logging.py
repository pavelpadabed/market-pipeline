import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from market_pipeline.acquisition.models import (
    AcquisitionFailure,
    AcquisitionFailureOutcome,
    AcquisitionMethod,
    AcquisitionResult,
    AcquisitionSuccess,
)
from market_pipeline.application.search_games import SearchGames
from market_pipeline.normalization.cheapshark_game_search_normalizer import (
    CheapSharkGameSearchNormalizer,
)
from market_pipeline.validation.cheapshark_game_search_validator import (
    CheapSharkGameSearchValidator,
)

WARSAW = ZoneInfo("Europe/Warsaw")
QUERY = "Batman"
STARTED_AT = datetime(
    2026,
    11,
    3,
    9,
    19,
    tzinfo=WARSAW,
)
FINISHED_AT = datetime(
    2026,
    11,
    3,
    9,
    20,
    tzinfo=WARSAW,
)


def _make_acquisition_success(
    content: str,
    **overrides: object,
) -> AcquisitionSuccess:
    data = {
        "requested_url": "https://www.cheapshark.com/api/1.0/games?title=Batman",
        "method": AcquisitionMethod.HTTP,
        "started_at": STARTED_AT,
        "finished_at": FINISHED_AT,
        "final_url": "https://www.cheapshark.com/api/1.0/games?title=Batman",
        "status_code": 200,
        "content_type": "application/json",
        "content": content,
    }
    data.update(overrides)
    return AcquisitionSuccess(**data)


def _make_acquisition_failure(
    diagnostic_message: str,
    final_url: str | None,
    status_code: int | None,
    content_type: str | None,
    retry_after_seconds: int | None = None,
    **overrides: object,
) -> AcquisitionFailure:
    data = {
        "requested_url": "https://www.cheapshark.com/api/1.0/games?title=Batman",
        "method": AcquisitionMethod.HTTP,
        "started_at": STARTED_AT,
        "finished_at": FINISHED_AT,
        "outcome": AcquisitionFailureOutcome.HTTP_ERROR,
        "diagnostic_message": diagnostic_message,
        "final_url": final_url,
        "status_code": status_code,
        "content_type": content_type,
        "retry_after_seconds": retry_after_seconds,
    }
    data.update(overrides)
    return AcquisitionFailure(**data)


class FakeGameSearchAcquirer:
    def __init__(self, result: AcquisitionResult) -> None:
        self.result = result

    def acquire(self, query: str) -> AcquisitionResult:
        self.called_query = query
        return self.result


def test_search_games_logs_started_and_completed_events_on_success(
    caplog: pytest.LogCaptureFixture,
) -> None:
    content = (
        '['
        '{"gameID": "2", "external": "LEGO Batman"},'
        '{"gameID": "1", "external": "Batman"}'
        ']'
    )
    acquisition = _make_acquisition_success(content)
    fake_acquirer = FakeGameSearchAcquirer(acquisition)

    validator = CheapSharkGameSearchValidator()
    normalizer = CheapSharkGameSearchNormalizer()

    searcher = SearchGames(
        fake_acquirer,
        validator,
        normalizer,
    )

    with caplog.at_level(
        logging.INFO,
        logger="market_pipeline.application.search_games",
    ):
        searcher.search(QUERY)

    records = [
        record
        for record in caplog.records
        if record.name == "market_pipeline.application.search_games"
    ]

    assert len(records) == 2
    started_record, completed_record = records
    assert started_record.levelname == "INFO"
    assert started_record.getMessage() == 'event="game search started"'
    assert completed_record.levelname == "INFO"
    assert completed_record.getMessage() == (
        'event="game search completed" candidate_count=2'
    )


def test_search_games_logs_acquisition_failure_as_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    acquisition = _make_acquisition_failure(
        diagnostic_message="HTTP request returned status 429",
        final_url=None,
        status_code=429,
        content_type=None,
        retry_after_seconds=60,
    )
    fake_acquirer = FakeGameSearchAcquirer(acquisition)

    validator = CheapSharkGameSearchValidator()
    normalizer = CheapSharkGameSearchNormalizer()

    searcher = SearchGames(
        fake_acquirer,
        validator,
        normalizer,
    )

    with caplog.at_level(
        logging.ERROR,
        logger="market_pipeline.application.search_games",
    ):
        searcher.search(QUERY)

    records = [
        record
        for record in caplog.records
        if record.name == "market_pipeline.application.search_games"
    ]

    assert len(records) == 1
    record, = records
    assert record.levelname == "ERROR"
    assert record.getMessage() == (
        'event="game search acquisition failed" '
        "acquisition_outcome=http_error "
        "diagnostic_message='HTTP request returned status 429' "
        "status_code=429 "
        "retry_after_seconds=60"
    )


def test_search_games_logs_validation_failure_as_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    content = (
        '['
        '{"gameID": "2", "external": " "},'
        '{"gameID": "1", "external": "Batman"}'
        ']'
    )
    acquisition = _make_acquisition_success(content)
    fake_acquirer = FakeGameSearchAcquirer(acquisition)

    validator = CheapSharkGameSearchValidator()
    normalizer = CheapSharkGameSearchNormalizer()

    searcher = SearchGames(
        fake_acquirer,
        validator,
        normalizer,
    )

    with caplog.at_level(
        logging.ERROR,
        logger="market_pipeline.application.search_games",
    ):
        searcher.search(QUERY)

    records = [
        record
        for record in caplog.records
        if record.name == "market_pipeline.application.search_games"
    ]

    assert len(records) == 1
    record, = records
    assert record.levelname == "ERROR"
    message = record.getMessage()
    assert message.startswith(
        'event="game search validation failed" diagnostic_message='
    )
    assert "title must not be blank" in message
    assert "\n" not in message
