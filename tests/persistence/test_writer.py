from datetime import UTC, datetime
from decimal import Decimal

import pytest
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
from market_pipeline.persistence.types import (
    PipelineRunOutcome,
    ProcessingStage,
)
from market_pipeline.persistence.writer import SqlAlchemyPipelineRunWriter


def _make_completed_run(**overrides: object) -> CompletedPipelineRunInput:
    started_at = datetime(2026, 9, 13, 10, 50, tzinfo=UTC)
    finished_at = datetime(2026, 9, 13, 10, 51, tzinfo=UTC)

    product = ProductInput(
        source="cheapshark",
        external_product_id=612,
        title="Batman",
    )
    observation = OfferObservationInput(
        source_seller_id="23",
        observed_at=finished_at,
        price=Decimal("10.23"),
        currency="USD",
    )

    data = {
        "requested_source": "cheapshark",
        "requested_external_product_id": 612,
        "started_at": started_at,
        "finished_at": finished_at,
        "outcome": PipelineRunOutcome.SUCCESS,
        "product": product,
        "observations": (observation,),
        "failures": (),
    }

    data.update(overrides)
    return CompletedPipelineRunInput(**data)


@pytest.mark.integration
def test_sqlalchemy_pipeline_run_writer_persists_failed_run_without_product(
    database_session: Session,
) -> None:
    failure = ProcessingFailureInput(
        stage=ProcessingStage.ACQUISITION,
        source_index=None,
        diagnostic_message="request failed",
    )
    completed_failed_run = _make_completed_run(
        outcome=PipelineRunOutcome.FAILURE,
        product=None,
        observations=(),
        failures=(failure,),
    )

    writer = SqlAlchemyPipelineRunWriter(database_session)
    writer.persist(completed_failed_run)

    statement = select(PipelineRun)
    result = database_session.execute(statement)
    returned_pipeline_run = result.scalars().one()

    assert type(returned_pipeline_run.id) is int
    assert (
        returned_pipeline_run.requested_source
        == completed_failed_run.requested_source
    )
    assert (
        returned_pipeline_run.requested_external_product_id
        == completed_failed_run.requested_external_product_id
    )
    assert returned_pipeline_run.started_at == completed_failed_run.started_at
    assert returned_pipeline_run.finished_at == completed_failed_run.finished_at
    assert returned_pipeline_run.outcome is completed_failed_run.outcome


@pytest.mark.integration
def test_sqlalchemy_pipeline_run_writer_persists_processing_failure_for_run(
    database_session: Session,
) -> None:
    failure = ProcessingFailureInput(
        stage=ProcessingStage.ACQUISITION,
        source_index=None,
        diagnostic_message="request failed",
    )
    completed_failed_run = _make_completed_run(
        outcome=PipelineRunOutcome.FAILURE,
        product=None,
        observations=(),
        failures=(failure,),
    )

    writer = SqlAlchemyPipelineRunWriter(database_session)
    writer.persist(completed_failed_run)

    pipeline_run_result = database_session.execute(select(PipelineRun))
    returned_pipeline_run = pipeline_run_result.scalars().one()
    processing_failure_result = database_session.execute(
        select(ProcessingFailure)
    )
    returned_processing_failure = processing_failure_result.scalars().one()

    assert returned_processing_failure.run_id == returned_pipeline_run.id
    assert returned_processing_failure.stage is failure.stage
    assert returned_processing_failure.source_index == failure.source_index
    assert (
        returned_processing_failure.diagnostic_message
        == failure.diagnostic_message
    )


@pytest.mark.integration
def test_sqlalchemy_pipeline_run_writer_persists_source_product(
    database_session: Session,
) -> None:
    completed_success_run = _make_completed_run()

    writer = SqlAlchemyPipelineRunWriter(database_session)
    writer.persist(completed_success_run)

    source_product_result = database_session.execute(select(SourceProduct))
    returned_source_product = source_product_result.scalars().one()

    assert completed_success_run.product is not None
    assert type(returned_source_product.id) is int
    assert returned_source_product.source == completed_success_run.product.source
    assert (
        returned_source_product.external_product_id
        == completed_success_run.product.external_product_id
    )
    assert returned_source_product.title == completed_success_run.product.title


@pytest.mark.integration
def test_sqlalchemy_pipeline_run_writer_persists_logical_offer_for_source_product(
    database_session: Session,
) -> None:
    completed_success_run = _make_completed_run()
    (observation,) = completed_success_run.observations

    writer = SqlAlchemyPipelineRunWriter(database_session)
    writer.persist(completed_success_run)

    source_product_result = database_session.execute(select(SourceProduct))
    returned_source_product = source_product_result.scalars().one()
    logical_offer_result = database_session.execute(select(LogicalOffer))
    returned_logical_offer = logical_offer_result.scalars().one()

    assert type(returned_logical_offer.id) is int
    assert (
        returned_logical_offer.source_product_id
        == returned_source_product.id
    )
    assert (
        returned_logical_offer.source_seller_id
        == observation.source_seller_id
    )


@pytest.mark.integration
def test_sqlalchemy_pipeline_run_writer_persists_offer_observation(
    database_session: Session,
) -> None:
    completed_run = _make_completed_run()
    (observation,) = completed_run.observations

    writer = SqlAlchemyPipelineRunWriter(database_session)
    writer.persist(completed_run)

    pipeline_run_result = database_session.execute(select(PipelineRun))
    returned_pipeline_run = pipeline_run_result.scalars().one()

    logical_offer_result = database_session.execute(select(LogicalOffer))
    returned_logical_offer = logical_offer_result.scalars().one()

    offer_observation_result = database_session.execute(select(OfferObservation))
    returned_offer_observation = offer_observation_result.scalars().one()

    assert type(returned_offer_observation.id) is int
    assert (
        returned_offer_observation.run_id == returned_pipeline_run.id
    )
    assert (
        returned_offer_observation.logical_offer_id
        == returned_logical_offer.id
    )
    assert (
        returned_offer_observation.observed_at == observation.observed_at
    )
    assert returned_offer_observation.price == observation.price
    assert returned_offer_observation.currency == observation.currency


@pytest.mark.integration
def test_sqlalchemy_pipeline_run_writer_reuses_source_product_across_runs(
    database_session: Session,
) -> None:
    completed_run_1 = _make_completed_run(
        observations=(),
    )
    completed_run_2 = _make_completed_run(
        observations=(),
    )

    writer = SqlAlchemyPipelineRunWriter(database_session)
    writer.persist(completed_run_1)
    writer.persist(completed_run_2)

    pipeline_run_results = database_session.execute(select(PipelineRun))
    returned_runs = pipeline_run_results.scalars().all()

    source_product_result = database_session.execute(select(SourceProduct))
    source_product_result.scalars().one()

    assert len(returned_runs) == 2


@pytest.mark.integration
def test_sqlalchemy_pipeline_run_writer_updates_reused_source_product_title(
    database_session: Session,
) -> None:
    completed_run_1 = _make_completed_run(
        observations=(),
    )
    product_remastered = ProductInput(
        source="cheapshark",
        external_product_id=612,
        title="Batman: Remastered",
    )
    completed_run_2 = _make_completed_run(
        product=product_remastered,
        observations=(),
    )
    writer = SqlAlchemyPipelineRunWriter(database_session)
    writer.persist(completed_run_1)
    writer.persist(completed_run_2)

    returned_source_product = database_session.scalars(
        select(SourceProduct)
    ).one()

    assert returned_source_product.title == product_remastered.title


@pytest.mark.integration
def test_sqlalchemy_pipeline_run_writer_reuses_logical_offer_across_runs(
    database_session: Session,
) -> None:
    completed_run_1 = _make_completed_run()
    completed_run_2 = _make_completed_run()

    writer = SqlAlchemyPipelineRunWriter(database_session)
    writer.persist(completed_run_1)
    writer.persist(completed_run_2)

    returned_logical_offer = database_session.scalars(select(LogicalOffer)).one()
    returned_offer_observations = database_session.scalars(select(OfferObservation)).all()

    assert len(returned_offer_observations) == 2
    assert all(
        observation.logical_offer_id == returned_logical_offer.id
        for observation in returned_offer_observations
    )