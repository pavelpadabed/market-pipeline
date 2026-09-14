from sqlalchemy import select
from sqlalchemy.orm import Session

from market_pipeline.persistence.inputs import (
    CompletedPipelineRunInput,
    OfferObservationInput,
    ProductInput,
    ProcessingFailureInput,
)
from market_pipeline.persistence.models import (
    LogicalOffer,
    OfferObservation,
    PipelineRun,
    ProcessingFailure,
    SourceProduct,
)


class SqlAlchemyPipelineRunWriter:
    def __init__(self, session: Session) -> None:
        self._session = session

    def persist(
        self,
        completed_run: CompletedPipelineRunInput,
    ) -> None:
        pipeline_run = PipelineRun(
            requested_source=completed_run.requested_source,
            requested_external_product_id=(
                completed_run.requested_external_product_id
            ),
            started_at=completed_run.started_at,
            finished_at=completed_run.finished_at,
            outcome=completed_run.outcome,
        )

        self._session.add(pipeline_run)
        self._session.flush()

        for failure in completed_run.failures:
            processing_failure = ProcessingFailure(
                run_id=pipeline_run.id,
                stage=failure.stage,
                source_index=failure.source_index,
                diagnostic_message=failure.diagnostic_message,
            )
            self._session.add(processing_failure)
        self._session.flush()

        product = completed_run.product
        if product is not None:
            statement = (
                select(SourceProduct).where(
                    SourceProduct.source == product.source,
                    SourceProduct.external_product_id
                    == product.external_product_id
                )
            )
            source_product = self._session.scalars(statement).one_or_none()
            if source_product is None:
                source_product = SourceProduct(
                    source=product.source,
                    external_product_id=product.external_product_id,
                    title=product.title,
                )
                self._session.add(source_product)
            if source_product.title != product.title:
                source_product.title = product.title
            self._session.flush()

            observation_offer_pairs: list[
                tuple[LogicalOffer, OfferObservationInput]
            ] = []
            for observation in completed_run.observations:
                statement = (
                    select(LogicalOffer).where(
                        LogicalOffer.source_product_id
                        == source_product.id,
                        LogicalOffer.source_seller_id == observation.source_seller_id,
                    )
                )
                logical_offer = self._session.scalars(statement).one_or_none()
                if logical_offer is None:
                    logical_offer = LogicalOffer(
                        source_product_id=source_product.id,
                        source_seller_id=observation.source_seller_id,
                    )
                    self._session.add(logical_offer)
                observation_offer_pairs.append((logical_offer, observation,))
            self._session.flush()

            for logical_offer, observation_input in observation_offer_pairs:
                offer_observation = OfferObservation(
                    logical_offer_id=logical_offer.id,
                    run_id=pipeline_run.id,
                    observed_at=observation_input.observed_at,
                    price=observation_input.price,
                    currency=observation_input.currency,
                )
                self._session.add(offer_observation)
            self._session.flush()
