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

    def execute(self, game_id: int) -> None:
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
            self.writer.persist(completed_run)
            return
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
            self.writer.persist(completed_run)
            return
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
            self.writer.persist(completed_run)
            return
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
