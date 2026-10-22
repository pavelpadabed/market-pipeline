from datetime import datetime
from decimal import Decimal
from typing import Never
from zoneinfo import ZoneInfo

from market_pipeline.acquisition.models import (
    AcquisitionFailure,
    AcquisitionFailureOutcome,
    AcquisitionMethod,
    AcquisitionResult,
    AcquisitionSuccess,
)
from market_pipeline.application.run_pipeline import RunPipeline
from market_pipeline.extraction.cheapshark_extractor import CheapSharkExtractor
from market_pipeline.extraction.models import CheapSharkExtractionSuccess
from market_pipeline.normalization.cheapshark_normalizer import CheapSharkNormalizer
from market_pipeline.persistence.inputs import CompletedPipelineRunInput
from market_pipeline.persistence.types import PipelineRunOutcome, ProcessingStage
from market_pipeline.validation.cheapshark_validator import CheapSharkValidator
from market_pipeline.validation.models import CheapSharkValidationSuccess

GAME_ID = 612
WARSAW = ZoneInfo("Europe/Warsaw")
STARTED_AT = datetime(2026, 10, 19, 10, 55, tzinfo=WARSAW)
FINISHED_AT = datetime(2026, 10, 19, 10, 56, tzinfo=WARSAW)


def _make_acquisition_success(**overrides: object) -> AcquisitionSuccess:
    data = {
        "requested_url": "https://www.cheapshark.com/api/1.0/games?id=612",
        "method": AcquisitionMethod.HTTP,
        "started_at": STARTED_AT,
        "finished_at": FINISHED_AT,
        "final_url": "https://api.cheapshark.com/api/1.0/games?id=612",
        "status_code": 200,
        "content_type": "application/json",
        "content": """
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
            """,
    }
    data.update(overrides)
    return AcquisitionSuccess(**data)


def _make_acquisition_failure() -> AcquisitionFailure:
    data = {
        "requested_url": "https://www.cheapshark.com/api/1.0/games?id=612",
        "method": AcquisitionMethod.HTTP,
        "started_at": STARTED_AT,
        "finished_at": FINISHED_AT,
        "outcome": AcquisitionFailureOutcome.NETWORK_ERROR,
        "diagnostic_message": "HTTP connection failed",
        "final_url": None,
        "status_code": None,
        "content_type": None,
        "retry_after_seconds": None,
    }

    return AcquisitionFailure(**data)


class FakeAcquirer:
    def __init__(self, result: AcquisitionResult) -> None:
        self.result = result
        self.called_game_id: int | None = None

    def acquire(self, game_id: int) -> AcquisitionResult:
        self.called_game_id = game_id
        return self.result


class FakeWriter:
    def __init__(self) -> None:
        self.pipeline_runs: list[CompletedPipelineRunInput] = []

    def persist(self, pipeline_run: CompletedPipelineRunInput) -> None:
        self.pipeline_runs.append(pipeline_run)


class UnexpectedCallExtractor:
    def extract(self, acquisition: AcquisitionSuccess) -> Never:
        raise AssertionError("extractor must not be called")


class UnexpectedCallValidator:
    def validate(self, extraction: CheapSharkExtractionSuccess) -> Never:
        raise AssertionError("validator must not be called")


class UnexpectedCallNormalizer:
    def normalize(
        self,
        validation: CheapSharkValidationSuccess,
    ) -> Never:
        raise AssertionError("normalizer must not be called")


def test_run_pipeline_persists_successful_run() -> None:
    acquisition_result = _make_acquisition_success()
    fake_acquirer = FakeAcquirer(acquisition_result)

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

    pipeline.execute(GAME_ID)

    assert fake_acquirer.called_game_id == GAME_ID
    assert len(fake_writer.pipeline_runs) == 1

    pipeline_run = fake_writer.pipeline_runs[0]
    assert pipeline_run.requested_source == "cheapshark"
    assert pipeline_run.requested_external_product_id == GAME_ID
    assert pipeline_run.outcome is PipelineRunOutcome.SUCCESS
    assert pipeline_run.product is not None
    assert pipeline_run.product.source == "cheapshark"
    assert pipeline_run.product.external_product_id == GAME_ID
    assert pipeline_run.product.title == "Batman"
    assert pipeline_run.failures == ()
    assert len(pipeline_run.observations) == 1

    observation = pipeline_run.observations[0]
    assert observation.source_seller_id == "23"
    assert observation.price == Decimal("10.23")


def test_run_pipeline_persists_failed_run_on_acquisition_failure() -> None:
    acquisition_result = _make_acquisition_failure()
    fake_acquirer = FakeAcquirer(acquisition_result)

    fake_extractor = UnexpectedCallExtractor()
    validator = CheapSharkValidator()
    normalizer = CheapSharkNormalizer()
    fake_writer = FakeWriter()

    pipeline = RunPipeline(
        fake_acquirer,
        fake_extractor,
        validator,
        normalizer,
        fake_writer,
    )

    pipeline.execute(GAME_ID)

    assert fake_acquirer.called_game_id == GAME_ID
    assert len(fake_writer.pipeline_runs) == 1

    pipeline_run = fake_writer.pipeline_runs[0]
    assert pipeline_run.requested_source == "cheapshark"
    assert pipeline_run.requested_external_product_id == GAME_ID
    assert pipeline_run.outcome is PipelineRunOutcome.FAILURE
    assert pipeline_run.product is None
    assert len(pipeline_run.failures) == 1
    assert pipeline_run.observations == ()

    failure = pipeline_run.failures[0]
    assert failure.stage is ProcessingStage.ACQUISITION
    assert failure.source_index is None
    assert failure.diagnostic_message == acquisition_result.diagnostic_message


def test_run_pipeline_persists_failed_run_on_extraction_failure() -> None:
    invalid_content = """
            {
                "info": {
                    "title": "Batman"
                },
                "deals": [
                    {
                        "storeID": "23",
                        "price": "10.23"
                    }
            }
            """
    acquisition_result = _make_acquisition_success(content=invalid_content)
    fake_acquirer = FakeAcquirer(acquisition_result)

    extractor = CheapSharkExtractor()
    fake_validator = UnexpectedCallValidator()
    normalizer = CheapSharkNormalizer()
    fake_writer = FakeWriter()

    pipeline = RunPipeline(
        fake_acquirer,
        extractor,
        fake_validator,
        normalizer,
        fake_writer,
    )

    pipeline.execute(GAME_ID)

    assert fake_acquirer.called_game_id == GAME_ID
    assert len(fake_writer.pipeline_runs) == 1

    pipeline_run = fake_writer.pipeline_runs[0]
    assert pipeline_run.requested_source == "cheapshark"
    assert pipeline_run.requested_external_product_id == GAME_ID
    assert pipeline_run.outcome is PipelineRunOutcome.FAILURE
    assert pipeline_run.product is None
    assert len(pipeline_run.failures) == 1
    assert pipeline_run.observations == ()

    failure = pipeline_run.failures[0]
    assert failure.stage is ProcessingStage.EXTRACTION
    assert failure.source_index is None
    assert failure.diagnostic_message == "Acquired content is not valid JSON"


def test_run_pipeline_persists_failed_run_on_validation_failure() -> None:
    invalid_content = """
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
    acquisition_result = _make_acquisition_success(content=invalid_content)
    fake_acquirer = FakeAcquirer(acquisition_result)

    extractor = CheapSharkExtractor()
    validator = CheapSharkValidator()
    fake_normalizer = UnexpectedCallNormalizer()
    fake_writer = FakeWriter()

    pipeline = RunPipeline(
        fake_acquirer,
        extractor,
        validator,
        fake_normalizer,
        fake_writer,
    )

    pipeline.execute(GAME_ID)

    assert fake_acquirer.called_game_id == GAME_ID
    assert len(fake_writer.pipeline_runs) == 1

    pipeline_run = fake_writer.pipeline_runs[0]
    assert pipeline_run.requested_source == "cheapshark"
    assert pipeline_run.requested_external_product_id == GAME_ID
    assert pipeline_run.outcome is PipelineRunOutcome.FAILURE
    assert pipeline_run.product is None
    assert len(pipeline_run.failures) == 1
    assert pipeline_run.observations == ()

    failure = pipeline_run.failures[0]
    assert failure.stage is ProcessingStage.VALIDATION
    assert failure.source_index is None
    assert "title must not be blank" in failure.diagnostic_message


def test_run_pipeline_persists_partial_failure_on_deal_extraction_failure() -> None:
    invalid_deal_content = """
            {
                "info": {"title": "Batman"},
                "deals": [
                    {"storeID": "23", "price": "10.23"},
                    null
                ]
            }
            """
    acquisition_result = _make_acquisition_success(content=invalid_deal_content)
    fake_acquirer = FakeAcquirer(acquisition_result)

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

    pipeline.execute(GAME_ID)

    assert fake_acquirer.called_game_id == GAME_ID
    assert len(fake_writer.pipeline_runs) == 1

    pipeline_run = fake_writer.pipeline_runs[0]
    assert pipeline_run.requested_source == "cheapshark"
    assert pipeline_run.requested_external_product_id == GAME_ID
    assert pipeline_run.outcome is PipelineRunOutcome.PARTIAL_FAILURE
    assert pipeline_run.product is not None
    assert len(pipeline_run.observations) == 1
    assert len(pipeline_run.failures) == 1

    failure = pipeline_run.failures[0]
    assert failure.stage is ProcessingStage.EXTRACTION
    assert failure.source_index == 1
    assert failure.diagnostic_message == "Deal candidate must be a mapping"

    observation = pipeline_run.observations[0]
    assert observation.source_seller_id == "23"
    assert observation.price == Decimal("10.23")
    assert observation.currency == "USD"
    assert observation.observed_at == acquisition_result.finished_at


def test_run_pipeline_persists_failed_run_when_all_deals_fail_extraction() -> None:
    content = """
        {
            "info": {"title": "Batman"},
            "deals": [null]
        }
        """
    acquisition_result = _make_acquisition_success(content=content)
    fake_acquirer = FakeAcquirer(acquisition_result)
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

    pipeline.execute(GAME_ID)

    assert fake_acquirer.called_game_id == GAME_ID
    assert len(fake_writer.pipeline_runs) == 1

    pipeline_run = fake_writer.pipeline_runs[0]
    assert pipeline_run.requested_source == "cheapshark"
    assert pipeline_run.requested_external_product_id == GAME_ID
    assert pipeline_run.outcome is PipelineRunOutcome.FAILURE
    assert pipeline_run.product is not None
    assert pipeline_run.product.source == "cheapshark"
    assert pipeline_run.product.external_product_id == GAME_ID
    assert pipeline_run.product.title == "Batman"
    assert pipeline_run.observations == ()
    assert len(pipeline_run.failures) == 1

    failure = pipeline_run.failures[0]
    assert failure.stage is ProcessingStage.EXTRACTION
    assert failure.source_index == 0
    assert failure.diagnostic_message == "Deal candidate must be a mapping"


def test_run_pipeline_persist_partial_failure_on_deal_validation_failure() -> None:
    invalid_content = """
            {
                "info": {"title": "Batman"},
                "deals": [
                    {"storeID": "23", "price": "10.23"},
                    {"storeID": "46", "price": "-12.33"}
                ]
            }
            """
    acquisition_result = _make_acquisition_success(content=invalid_content)
    fake_acquirer = FakeAcquirer(acquisition_result)

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

    pipeline.execute(GAME_ID)

    assert fake_acquirer.called_game_id == GAME_ID
    assert len(fake_writer.pipeline_runs) == 1

    pipeline_run = fake_writer.pipeline_runs[0]
    assert pipeline_run.requested_source == "cheapshark"
    assert pipeline_run.requested_external_product_id == GAME_ID
    assert pipeline_run.outcome is PipelineRunOutcome.PARTIAL_FAILURE
    assert pipeline_run.product is not None
    assert pipeline_run.product.source == "cheapshark"
    assert pipeline_run.product.external_product_id == GAME_ID
    assert pipeline_run.product.title == "Batman"
    assert len(pipeline_run.observations) == 1
    assert len(pipeline_run.failures) == 1

    failure = pipeline_run.failures[0]
    assert failure.stage is ProcessingStage.VALIDATION
    assert failure.source_index == 1
    assert "price must be non-negative" in failure.diagnostic_message

    observation = pipeline_run.observations[0]
    assert observation.source_seller_id == "23"
    assert observation.price == Decimal("10.23")


def test_run_pipeline_persists_success_on_empty_deals() -> None:
    content = """
            {
                "info": {"title": "Batman"},
                "deals": []
            }
            """
    acquisition_result = _make_acquisition_success(content=content)
    fake_acquirer = FakeAcquirer(acquisition_result)

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

    pipeline.execute(GAME_ID)

    assert fake_acquirer.called_game_id == GAME_ID
    assert len(fake_writer.pipeline_runs) == 1

    pipeline_run = fake_writer.pipeline_runs[0]
    assert pipeline_run.requested_source == "cheapshark"
    assert pipeline_run.requested_external_product_id == GAME_ID
    assert pipeline_run.outcome is PipelineRunOutcome.SUCCESS
    assert pipeline_run.product is not None
    assert pipeline_run.product.source == "cheapshark"
    assert pipeline_run.product.external_product_id == GAME_ID
    assert pipeline_run.product.title == "Batman"
    assert pipeline_run.observations == ()
    assert pipeline_run.failures == ()
