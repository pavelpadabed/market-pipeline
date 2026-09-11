from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    Identity,
    Numeric,
    TIMESTAMP,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


class Base(DeclarativeBase):
    pass


class SourceProduct(Base):
    __tablename__ = "source_product"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_product_id",
            name="uq_source_product_source_external_product_id",
        ),
        CheckConstraint(
            "source ~ '[^[:space:]]'",
            name="ck_source_product_source_not_blank",
        ),
        CheckConstraint(
            "title ~ '[^[:space:]]'",
            name="ck_source_product_title_not_blank",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    source: Mapped[str] = mapped_column(Text)
    external_product_id: Mapped[int] = mapped_column(
        BigInteger,
    )
    title: Mapped[str] = mapped_column(Text)


class LogicalOffer(Base):
    __tablename__ = "logical_offer"
    __table_args__ = (
        UniqueConstraint(
            "source_product_id",
            "source_seller_id",
            name="uq_logical_offer_source_product_id_source_seller_id",
        ),
        CheckConstraint(
            "source_seller_id ~ '[^[:space:]]'",
            name="ck_logical_offer_source_seller_id_not_blank",
        ),
    )
    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    source_product_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("source_product.id"),
    )
    source_seller_id: Mapped[str] = mapped_column(Text)


class PipelineRunOutcome(StrEnum):
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"
    FAILURE = "failure"


class PipelineRun(Base):
    __tablename__ = "pipeline_run"
    __table_args__ = (
        CheckConstraint(
            "finished_at >= started_at",
            name="ck_pipeline_run_finished_at_not_before_started_at",
        ),
        CheckConstraint(
            "outcome IN ('success', 'partial_failure', 'failure')",
            name="ck_pipeline_run_outcome_valid",
        ),
    )
    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    finished_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    outcome: Mapped[PipelineRunOutcome] = mapped_column(
        Enum(
            PipelineRunOutcome,
            native_enum=False,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
        ),
    )


class OfferObservation(Base):
    __tablename__ = "offer_observation"
    __table_args__ = (
        CheckConstraint(
            "price >= 0",
            name="ck_offer_observation_price_non_negative",
        ),
        CheckConstraint(
            "price NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)",
            name="ck_offer_observation_price_finite",
        ),
        CheckConstraint(
            "currency ~ '[^[:space:]]'",
            name="ck_offer_observation_currency_not_blank",
        ),
    )
    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    logical_offer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("logical_offer.id"),
    )
    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("pipeline_run.id"),
    )
    observed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    price: Mapped[Decimal] = mapped_column(Numeric)
    currency: Mapped[str] = mapped_column(Text)


class ProcessingStage(StrEnum):
    ACQUISITION = "acquisition"
    EXTRACTION = "extraction"
    VALIDATION = "validation"


class ProcessingFailure(Base):
    __tablename__ = "processing_failure"
    __table_args__ = (
        CheckConstraint(
            "source_index IS NULL OR source_index >= 0",
            name="ck_processing_failure_source_index_non_negative",
        ),
        CheckConstraint(
            "diagnostic_message ~ '[^[:space:]]'",
            name="ck_processing_failure_diagnostic_message_not_blank",
        ),
        CheckConstraint(
            "stage IN ('acquisition', 'extraction', 'validation')",
            name="ck_processing_failure_stage_valid",
        ),
    )
    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("pipeline_run.id"),
    )
    stage: Mapped[ProcessingStage] = mapped_column(
        Enum(
            ProcessingStage,
            native_enum=False,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
        ),
    )
    source_index: Mapped[int | None] = mapped_column(
        BigInteger,
    )
    diagnostic_message: Mapped[str] = mapped_column(Text)
