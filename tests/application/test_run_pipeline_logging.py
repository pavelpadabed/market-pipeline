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
from market_pipeline.application.run_pipeline import RunPipeline
from market_pipeline.extraction.cheapshark_extractor import CheapSharkExtractor
from market_pipeline.normalization.cheapshark_normalizer import CheapSharkNormalizer
from market_pipeline.persistence.inputs import CompletedPipelineRunInput
from market_pipeline.validation.cheapshark_validator import CheapSharkValidator

GAME_ID = 612
WARSAW = ZoneInfo("Europe/Warsaw")
STARTED_AT = datetime(2026, 10, 19, 10, 55, tzinfo=WARSAW)
FINISHED_AT = datetime(2026, 10, 19, 10, 56, tzinfo=WARSAW)


def _make_acquisition_success(content: str) -> AcquisitionSuccess:
    data = {
        "requested_url": "https://www.cheapshark.com/api/1.0/games?id=612",
        "method": AcquisitionMethod.HTTP,
        "started_at": STARTED_AT,
        "finished_at": FINISHED_AT,
        "final_url": "https://api.cheapshark.com/api/1.0/games?id=612",
        "status_code": 200,
        "content_type": "application/json",
        "content": content,
    }
    return AcquisitionSuccess(**data)


class FakeAcquirer:
    def __init__(self, result: AcquisitionResult) -> None:
        self.result = result

    def acquire(self, game_id: int) -> AcquisitionResult:
        return self.result


class FakeWriter:
    def __init__(self) -> None:
        self.pipeline_runs: list[CompletedPipelineRunInput] = []

    def persist(self, pipeline_run: CompletedPipelineRunInput) -> None:
        self.pipeline_runs.append(pipeline_run)


def test_run_pipeline_logs_events_on_success(
    caplog: pytest.LogCaptureFixture,
) -> None:
    content = """
            {
                "info": {
                    "title": "Batman"
                },
                "deals": [
                    {
                        "storeID": "23",
                        "price": "10.23"
                    }
                ]
            }
            """
    acquisition = _make_acquisition_success(content)
    fake_acquirer = FakeAcquirer(acquisition)

    extractor = CheapSharkExtractor()
    validator = CheapSharkValidator()
    normalizer = CheapSharkNormalizer()
    fake_writer = FakeWriter()

    pipeline = RunPipeline(
        fake_acquirer,
        extractor,
        validator,
        normalizer,
        fake_writer,
    )
    expected_message = (
        'event="pipeline run completed" '
        "game_id=612 "
        "outcome=success "
        "observation_count=1 "
        "acquisition_failure_count=0 "
        "extraction_failure_count=0 "
        "validation_failure_count=0"
    )

    with caplog.at_level(
        logging.INFO,
        logger="market_pipeline.application.run_pipeline",
    ):
        pipeline.execute(GAME_ID)

    records = [
        record
        for record in caplog.records
        if record.name == "market_pipeline.application.run_pipeline"
    ]

    assert len(records) == 2
    started, terminal = records
    assert started.levelname == "INFO"
    assert started.getMessage() == (
        'event="pipeline run started" '
        "game_id=612"
    )

    assert terminal.levelname == "INFO"
    assert terminal.getMessage() == expected_message


def test_run_pipeline_logs_acquisition_failure_as_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    acquisition_failure = AcquisitionFailure(
        requested_url="https://www.cheapshark.com/api/1.0/games?title=Batman",
        method=AcquisitionMethod.HTTP,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        outcome=AcquisitionFailureOutcome.HTTP_ERROR,
        diagnostic_message="HTTP request returned status 429",
        final_url=None,
        status_code=429,
        content_type=None,
        retry_after_seconds=60,
    )
    fake_acquirer = FakeAcquirer(acquisition_failure)

    extractor = CheapSharkExtractor()
    validator = CheapSharkValidator()
    normalizer = CheapSharkNormalizer()
    fake_writer = FakeWriter()

    pipeline = RunPipeline(
        fake_acquirer,
        extractor,
        validator,
        normalizer,
        fake_writer,
    )
    expected_acquisition_message = (
        'event="pipeline acquisition failed" '
        "game_id=612 "
        "acquisition_outcome=http_error "
        "diagnostic_message='HTTP request returned status 429' "
        "status_code=429 "
        "retry_after_seconds=60"
    )

    expected_terminal_message = (
        'event="pipeline run completed" '
        "game_id=612 "
        "outcome=failure "
        "observation_count=0 "
        "acquisition_failure_count=1 "
        "extraction_failure_count=0 "
        "validation_failure_count=0"
    )

    with caplog.at_level(
        logging.ERROR,
        logger="market_pipeline.application.run_pipeline",
    ):
        pipeline.execute(GAME_ID)

    records = [
        record
        for record in caplog.records
        if record.name == "market_pipeline.application.run_pipeline"
    ]

    assert len(records) == 2
    acquisition, terminal = records
    assert acquisition.levelname == "ERROR"
    assert acquisition.getMessage() == expected_acquisition_message
    assert terminal.levelname == "ERROR"
    assert terminal.getMessage() == expected_terminal_message


def test_run_pipeline_logs_extraction_failure_as_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    content = """
            {
                "info": {
                    "title": "Batman"
                },
                "deals":
                    {
                        "storeID": "23",
                        "price": "10.23"
                    }

            }
            """
    acquisition = _make_acquisition_success(content)
    fake_acquirer = FakeAcquirer(acquisition)

    extractor = CheapSharkExtractor()
    validator = CheapSharkValidator()
    normalizer = CheapSharkNormalizer()
    fake_writer = FakeWriter()

    pipeline = RunPipeline(
        fake_acquirer,
        extractor,
        validator,
        normalizer,
        fake_writer,
    )
    expected_extraction_message = (
        'event="pipeline extraction failed" '
        "game_id=612 "
        "extraction_outcome=deals_not_list "
        "diagnostic_message='CheapShark deals must be a list'"
    )

    expected_terminal_message = (
        'event="pipeline run completed" '
        "game_id=612 "
        "outcome=failure "
        "observation_count=0 "
        "acquisition_failure_count=0 "
        "extraction_failure_count=1 "
        "validation_failure_count=0"
    )

    with caplog.at_level(
        logging.ERROR,
        logger="market_pipeline.application.run_pipeline",
    ):
        pipeline.execute(GAME_ID)

    records = [
        record
        for record in caplog.records
        if record.name == "market_pipeline.application.run_pipeline"
    ]

    assert len(records) == 2
    extraction, terminal = records
    assert extraction.levelname == "ERROR"
    assert extraction.getMessage() == expected_extraction_message
    assert terminal.levelname == "ERROR"
    assert terminal.getMessage() == expected_terminal_message


def test_run_pipeline_logs_validation_failure_as_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    content = """
            {
                "info": {
                    "title": " "
                },
                "deals": [
                    {
                        "storeID": "23",
                        "price": "10.23"
                    }
                ]
            }
            """
    acquisition = _make_acquisition_success(content)
    fake_acquirer = FakeAcquirer(acquisition)

    extractor = CheapSharkExtractor()
    validator = CheapSharkValidator()
    normalizer = CheapSharkNormalizer()
    fake_writer = FakeWriter()

    pipeline = RunPipeline(
        fake_acquirer,
        extractor,
        validator,
        normalizer,
        fake_writer,
    )
    expected_validation_message = (
        'event="pipeline validation failed" '
        "game_id=612 "
        "diagnostic_message='title: Value error, title must not be blank'"
    )
    expected_terminal_message = (
        'event="pipeline run completed" '
        "game_id=612 "
        "outcome=failure "
        "observation_count=0 "
        "acquisition_failure_count=0 "
        "extraction_failure_count=0 "
        "validation_failure_count=1"
    )

    with caplog.at_level(
        logging.ERROR,
        logger="market_pipeline.application.run_pipeline",
    ):
        pipeline.execute(GAME_ID)

    records = [
        record
        for record in caplog.records
        if record.name == "market_pipeline.application.run_pipeline"
    ]

    assert len(records) == 2
    validation, terminal = records
    assert validation.levelname == "ERROR"
    assert validation.getMessage() == expected_validation_message
    assert terminal.levelname == "ERROR"
    assert terminal.getMessage() == expected_terminal_message


def test_run_pipeline_logs_partial_failure_as_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    content = """
            {
                "info": {
                    "title": "Batman"
                },
                "deals": [
                    {
                        "storeID": "23",
                        "price": "10.23"
                    },
                    {
                        "storeID": "24",
                        "price": "-1.00"
                    }
                ]
            }
            """
    acquisition = _make_acquisition_success(content)
    fake_acquirer = FakeAcquirer(acquisition)

    extractor = CheapSharkExtractor()
    validator = CheapSharkValidator()
    normalizer = CheapSharkNormalizer()
    fake_writer = FakeWriter()

    pipeline = RunPipeline(
        fake_acquirer,
        extractor,
        validator,
        normalizer,
        fake_writer,
    )
    expected_terminal_message = (
        'event="pipeline run completed" '
        "game_id=612 "
        "outcome=partial_failure "
        "observation_count=1 "
        "acquisition_failure_count=0 "
        "extraction_failure_count=0 "
        "validation_failure_count=1"
    )

    with caplog.at_level(
        logging.WARNING,
        logger="market_pipeline.application.run_pipeline",
    ):
        pipeline.execute(GAME_ID)

    records = [
        record
        for record in caplog.records
        if record.name == "market_pipeline.application.run_pipeline"
    ]

    assert len(records) == 1
    terminal, = records
    assert terminal.levelname == "WARNING"
    assert terminal.getMessage() == expected_terminal_message
