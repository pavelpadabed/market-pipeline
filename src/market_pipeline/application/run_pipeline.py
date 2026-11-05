import logging
from datetime import UTC, datetime

from market_pipeline.acquisition.cheapshark_acquirer import (
    CheapSharkApiAcquirer,
)
from market_pipeline.acquisition.models import AcquisitionFailure
from market_pipeline.extraction.cheapshark_extractor import CheapSharkExtractor
from market_pipeline.extraction.models import (
    CheapSharkDealExtractionFailure,
    CheapSharkExtractionFailure,
)
from market_pipeline.normalization.cheapshark_normalizer import CheapSharkNormalizer
from market_pipeline.normalization.models import NormalizedCheapSharkOffer
from market_pipeline.persistence.inputs import (
    CompletedPipelineRunInput,
    OfferObservationInput,
    ProcessingFailureInput,
    ProductInput,
)
from market_pipeline.persistence.types import (
    PipelineRunOutcome,
    ProcessingStage,
)
from market_pipeline.persistence.writer import SqlAlchemyPipelineRunWriter
from market_pipeline.validation.cheapshark_validator import CheapSharkValidator
from market_pipeline.validation.models import (
    CheapSharkDealValidationFailure,
    CheapSharkValidationFailure,
)

SOURCE = "cheapshark"
CURRENCY = "USD"

logger = logging.getLogger(__name__)


class RunPipeline:
    def __init__(
        self,
        acquirer: CheapSharkApiAcquirer,
        extractor: CheapSharkExtractor,
        validator: CheapSharkValidator,
        normalizer: CheapSharkNormalizer,
        writer: SqlAlchemyPipelineRunWriter,
    ) -> None:
        self.acquirer = acquirer
        self.extractor = extractor
        self.validator = validator
        self.normalizer = normalizer
        self.writer = writer

    def _build_failed_run_input(
        self,
        *,
        game_id: int,
        started_at: datetime,
        finished_at: datetime,
        failures: tuple[ProcessingFailureInput, ...],
    ) -> CompletedPipelineRunInput:
        return CompletedPipelineRunInput(
            requested_source=SOURCE,
            requested_external_product_id=game_id,
            started_at=started_at,
            finished_at=finished_at,
            outcome=PipelineRunOutcome.FAILURE,
            product=None,
            observations=(),
            failures=failures,
        )

    def _log_completed_run(
        self,
        completed_run: CompletedPipelineRunInput,
    ) -> None:
        log_level_by_outcome = {
            PipelineRunOutcome.SUCCESS: logging.INFO,
            PipelineRunOutcome.PARTIAL_FAILURE: logging.WARNING,
            PipelineRunOutcome.FAILURE: logging.ERROR,
        }
        observation_count = len(completed_run.observations)

        acquisition_failure_count = sum(
            1
            for failure in completed_run.failures
            if failure.stage is ProcessingStage.ACQUISITION
        )

        extraction_failure_count = sum(
            1
            for failure in completed_run.failures
            if failure.stage is ProcessingStage.EXTRACTION
        )

        validation_failure_count = sum(
            1
            for failure in completed_run.failures
            if failure.stage is ProcessingStage.VALIDATION
        )

        logger.log(
            log_level_by_outcome[completed_run.outcome],
            'event="pipeline run completed" '
            "game_id=%s "
            "outcome=%s "
            "observation_count=%s "
            "acquisition_failure_count=%s "
            "extraction_failure_count=%s "
            "validation_failure_count=%s",
            completed_run.requested_external_product_id,
            completed_run.outcome,
            observation_count,
            acquisition_failure_count,
            extraction_failure_count,
            validation_failure_count,
        )

    def execute(self, game_id: int) -> bool:
        """Persist the run and return whether it contains saved observations.

        False means the run was saved without observations, not that saving
        failed. Persistence errors propagate to the caller.
        """
        logger.info(
            'event="pipeline run started" '
            "game_id=%s",
            game_id,
        )
        started_at = datetime.now(UTC)
        acquisition = self.acquirer.acquire(game_id)
        if isinstance(acquisition, AcquisitionFailure):
            completed_run = self._build_failed_run_input(
                game_id=game_id,
                started_at=started_at,
                finished_at=datetime.now(UTC),
                failures=(
                    ProcessingFailureInput(
                        stage=ProcessingStage.ACQUISITION,
                        source_index=None,
                        diagnostic_message=acquisition.diagnostic_message,
                    ),
                ),
            )
            logger.error(
                'event="pipeline acquisition failed" '
                "game_id=%s "
                "acquisition_outcome=%s "
                "diagnostic_message=%r "
                "status_code=%s "
                "retry_after_seconds=%s",
                game_id,
                acquisition.outcome,
                acquisition.diagnostic_message,
                acquisition.status_code,
                acquisition.retry_after_seconds,
            )

            self.writer.persist(completed_run)

            self._log_completed_run(completed_run)

            return False
        extraction = self.extractor.extract(acquisition)
        if isinstance(extraction, CheapSharkExtractionFailure):
            completed_run = self._build_failed_run_input(
                game_id=game_id,
                started_at=started_at,
                finished_at=datetime.now(UTC),
                failures=(
                    ProcessingFailureInput(
                        stage=ProcessingStage.EXTRACTION,
                        source_index=None,
                        diagnostic_message=extraction.diagnostic_message,
                    ),
                ),
            )
            logger.error(
                'event="pipeline extraction failed" '
                "game_id=%s "
                "extraction_outcome=%s "
                "diagnostic_message=%r",
                game_id,
                extraction.outcome,
                extraction.diagnostic_message,
            )
            self.writer.persist(completed_run)

            self._log_completed_run(completed_run)

            return False
        validation = self.validator.validate(extraction)
        if isinstance(validation, CheapSharkValidationFailure):
            completed_run = self._build_failed_run_input(
                game_id=game_id,
                started_at=started_at,
                finished_at=datetime.now(UTC),
                failures=(
                    ProcessingFailureInput(
                        stage=ProcessingStage.VALIDATION,
                        source_index=None,
                        diagnostic_message=validation.diagnostic_message,
                    ),
                ),
            )
            logger.error(
                'event="pipeline validation failed" '
                "game_id=%s "
                "diagnostic_message=%r",
                game_id,
                validation.diagnostic_message,
            )

            self.writer.persist(completed_run)

            self._log_completed_run(completed_run)

            return False
        normalization = self.normalizer.normalize(validation)

        observations: list[OfferObservationInput] = []
        failures: list[ProcessingFailureInput] = []

        for offer in normalization.offer_results:
            match offer:
                case CheapSharkDealExtractionFailure():
                    failure = ProcessingFailureInput(
                        stage=ProcessingStage.EXTRACTION,
                        source_index=offer.index,
                        diagnostic_message=offer.diagnostic_message,
                    )
                    failures.append(failure)
                case CheapSharkDealValidationFailure():
                    failure = ProcessingFailureInput(
                        stage=ProcessingStage.VALIDATION,
                        source_index=offer.index,
                        diagnostic_message=offer.diagnostic_message,
                    )
                    failures.append(failure)
                case NormalizedCheapSharkOffer():
                    observation = OfferObservationInput(
                        source_seller_id=offer.store_id,
                        observed_at=acquisition.finished_at,
                        price=offer.price,
                        currency=CURRENCY,
                    )
                    observations.append(observation)

        finished_at = datetime.now(UTC)

        if not failures:
            outcome = PipelineRunOutcome.SUCCESS
        elif observations:
            outcome = PipelineRunOutcome.PARTIAL_FAILURE
        else:
            outcome = PipelineRunOutcome.FAILURE

        completed_run = CompletedPipelineRunInput(
            requested_source=SOURCE,
            requested_external_product_id=game_id,
            started_at=started_at,
            finished_at=finished_at,
            outcome=outcome,
            product=ProductInput(
                source=SOURCE,
                external_product_id=game_id,
                title=normalization.title,
            ),
            observations=tuple(observations),
            failures=tuple(failures),
        )

        self.writer.persist(completed_run)

        self._log_completed_run(completed_run)

        return bool(completed_run.observations)
