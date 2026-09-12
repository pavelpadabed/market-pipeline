from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from market_pipeline.persistence.types import (
    PipelineRunOutcome,
    ProcessingStage,
)


@dataclass(frozen=True, slots=True)
class ProductInput:
    source: str
    external_product_id: int
    title: str

    def __post_init__(self) -> None:
        if not isinstance(self.source, str):
            raise TypeError("source must be an instance of str")
        if not self.source.strip():
            raise ValueError("source must not be blank")
        if type(self.external_product_id) is not int:
            raise TypeError("external_product_id must have type int")
        if not isinstance(self.title, str):
            raise TypeError("title must be an instance of str")
        if not self.title.strip():
            raise ValueError("title must not be blank")


@dataclass(frozen=True, slots=True)
class OfferObservationInput:
    source_seller_id: str
    observed_at: datetime
    price: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.source_seller_id, str):
            raise TypeError(
                "source_seller_id must be an instance of str"
            )
        if not self.source_seller_id.strip():
            raise ValueError("source_seller_id must not be blank")
        if not isinstance(self.observed_at, datetime):
            raise TypeError(
                "observed_at must be an instance of datetime"
            )
        if (
            self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise ValueError("observed_at must be timezone-aware")
        if not isinstance(self.price, Decimal):
            raise TypeError("price must be an instance of Decimal")
        if not self.price.is_finite():
            raise ValueError("price must be finite")
        if self.price < 0:
            raise ValueError("price must be non-negative")
        if not isinstance(self.currency, str):
            raise TypeError("currency must be an instance of str")
        if not self.currency.strip():
            raise ValueError("currency must not be blank")


@dataclass(frozen=True, slots=True)
class ProcessingFailureInput:
    stage: ProcessingStage
    source_index: int | None
    diagnostic_message: str

    def __post_init__(self) -> None:
        if not isinstance(self.stage, ProcessingStage):
            raise TypeError("stage must be an instance of ProcessingStage")
        if self.source_index is not None and type(self.source_index) is not int:
            raise TypeError("source_index must have type int or be None")
        if self.source_index is not None and self.source_index < 0:
            raise ValueError("source_index must be non-negative")
        if not isinstance(self.diagnostic_message, str):
            raise TypeError(
                "diagnostic_message must be an instance of str"
            )
        if not self.diagnostic_message.strip():
            raise ValueError("diagnostic_message must not be blank")


@dataclass(frozen=True, slots=True)
class CompletedPipelineRunInput:
    requested_source: str
    requested_external_product_id: int
    started_at: datetime
    finished_at: datetime
    outcome: PipelineRunOutcome
    product: ProductInput | None
    observations: tuple[OfferObservationInput, ...]
    failures: tuple[ProcessingFailureInput, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.requested_source, str):
            raise TypeError("requested_source must be an instance of str")
        if not self.requested_source.strip():
            raise ValueError("requested_source must not be blank")
        if type(self.requested_external_product_id) is not int:
            raise TypeError(
                "requested_external_product_id must have type int"
            )
        if not isinstance(self.started_at, datetime):
            raise TypeError("started_at must be an instance of datetime")
        if (
            self.started_at.tzinfo is None
            or self.started_at.utcoffset() is None
        ):
            raise ValueError("started_at must be timezone-aware")
        if not isinstance(self.finished_at, datetime):
            raise TypeError("finished_at must be an instance of datetime")
        if (
            self.finished_at.tzinfo is None
            or self.finished_at.utcoffset() is None
        ):
            raise ValueError("finished_at must be timezone-aware")
        if self.finished_at < self.started_at:
            raise ValueError(
                "finished_at must not be earlier than started_at"
            )
        if not isinstance(self.outcome, PipelineRunOutcome):
            raise TypeError(
                "outcome must be an instance of PipelineRunOutcome"
            )
        if self.product is not None and not isinstance(
            self.product,
            ProductInput,
        ):
            raise TypeError(
                "product must be an instance of ProductInput or be None"
            )
        if not isinstance(self.observations, tuple):
            raise TypeError("observations must be an instance of tuple")
        if not all(
            isinstance(observation, OfferObservationInput)
            for observation in self.observations
        ):
            raise TypeError(
                "observations must contain only OfferObservationInput instances"
            )
        if not isinstance(self.failures, tuple):
            raise TypeError("failures must be an instance of tuple")
        if not all(
            isinstance(failure, ProcessingFailureInput)
            for failure in self.failures
        ):
            raise TypeError(
                "failures must contain only ProcessingFailureInput instances"
            )
        if self.outcome is PipelineRunOutcome.SUCCESS and self.failures:
            raise ValueError("successful run must not contain failures")
        if self.outcome is PipelineRunOutcome.SUCCESS and self.product is None:
            raise ValueError("successful run must contain a product")
        if (
            self.outcome is PipelineRunOutcome.PARTIAL_FAILURE
            and not self.failures
        ):
            raise ValueError(
                "partially failed run must contain at least one failure"
            )
        if (
            self.outcome is PipelineRunOutcome.PARTIAL_FAILURE
            and not self.observations
        ):
            raise ValueError(
                "partially failed run must contain at least one observation"
            )
        if (
            self.outcome is PipelineRunOutcome.PARTIAL_FAILURE
            and self.product is None
        ):
            raise ValueError("partially failed run must contain a product")
        if self.outcome is PipelineRunOutcome.FAILURE and self.observations:
            raise ValueError("failed run must not contain observations")
        if self.outcome is PipelineRunOutcome.FAILURE and not self.failures:
            raise ValueError("failed run must contain at least one failure")
