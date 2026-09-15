from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from market_pipeline.persistence.models import (
    LogicalOffer,
    OfferObservation,
    PipelineRun,
    SourceProduct,
)


@dataclass(frozen=True, slots=True)
class CurrentOffer:
    product_title: str
    source_seller_id: str
    observed_at: datetime
    price: Decimal
    currency: str


@dataclass(frozen=True, slots=True)
class OfferHistoryEntry:
    product_title: str
    source_seller_id: str
    observed_at: datetime
    price: Decimal
    currency: str


class SqlAlchemyOfferQuery:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_current_offers(
        self,
        source: str,
        external_product_id: int,
    ) -> tuple[CurrentOffer, ...]:
        latest_run_id_statement = select(PipelineRun.id).where(
            PipelineRun.requested_source == source,
            PipelineRun.requested_external_product_id == external_product_id,
        ).order_by(
            PipelineRun.finished_at.desc(),
            PipelineRun.id.desc(),
        ).limit(1)

        statement = select(
            SourceProduct.title,
            LogicalOffer.source_seller_id,
            OfferObservation.observed_at,
            OfferObservation.price,
            OfferObservation.currency,
        ).join(
            LogicalOffer,
            LogicalOffer.source_product_id == SourceProduct.id,
        ).join(
            OfferObservation,
            OfferObservation.logical_offer_id == LogicalOffer.id,
        ).where(
            OfferObservation.run_id == latest_run_id_statement.scalar_subquery(),
        ).order_by(OfferObservation.price)

        result_mappings = self._session.execute(statement).mappings().all()

        return tuple(
            CurrentOffer(
                product_title=result[SourceProduct.title],
                source_seller_id=result[LogicalOffer.source_seller_id],
                observed_at=result[OfferObservation.observed_at],
                price=result[OfferObservation.price],
                currency=result[OfferObservation.currency],
            )
            for result in result_mappings
        )

    def get_offer_history(
        self,
        source: str,
        external_product_id: int,
    ) -> tuple[OfferHistoryEntry, ...]:
        statement = select(
            SourceProduct.title,
            LogicalOffer.source_seller_id,
            OfferObservation.observed_at,
            OfferObservation.price,
            OfferObservation.currency,
        ).join(
            LogicalOffer,
            LogicalOffer.source_product_id == SourceProduct.id,
        ).join(
            OfferObservation,
            OfferObservation.logical_offer_id == LogicalOffer.id,
        ).where(
            SourceProduct.source == source,
            SourceProduct.external_product_id == external_product_id,
        ).order_by(
            OfferObservation.observed_at,
            OfferObservation.id,
        )

        result_mappings = self._session.execute(statement).mappings().all()

        return tuple(
            OfferHistoryEntry(
                product_title=result[SourceProduct.title],
                source_seller_id=result[LogicalOffer.source_seller_id],
                observed_at=result[OfferObservation.observed_at],
                price=result[OfferObservation.price],
                currency=result[OfferObservation.currency],
            )
            for result in result_mappings
        )
