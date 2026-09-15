from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from market_pipeline.persistence.inputs import (
    CompletedPipelineRunInput,
    OfferObservationInput,
    ProductInput,
)
from market_pipeline.persistence.queries import (
    CurrentOffer,
    OfferHistoryEntry,
    SqlAlchemyOfferQuery,
)
from market_pipeline.persistence.types import PipelineRunOutcome
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
def test_sqlalchemy_offer_query_returns_offers_for_requested_product(
    database_session: Session,
) -> None:
    requested_source = "cheapshark"
    requested_external_product_id = 612
    observed_at = datetime(2026, 9, 13, 10, 51, tzinfo=UTC)
    observation = OfferObservationInput(
        source_seller_id="23",
        observed_at=observed_at,
        price=Decimal("10.23"),
        currency="USD",
    )
    another_observation = OfferObservationInput(
        source_seller_id="64",
        observed_at=observed_at,
        price=Decimal("7.23"),
        currency="USD",
    )
    completed_run = _make_completed_run(
        observations=(observation, another_observation),
    )

    writer = SqlAlchemyPipelineRunWriter(database_session)
    writer.persist(completed_run)

    query = SqlAlchemyOfferQuery(database_session)

    returned_offers = query.get_current_offers(
        requested_source,
        requested_external_product_id,
    )
    actual = set(returned_offers)
    expected = {
        CurrentOffer(
            product_title="Batman",
            source_seller_id="23",
            observed_at=observed_at,
            price=Decimal("10.23"),
            currency="USD",
        ),
        CurrentOffer(
            product_title="Batman",
            source_seller_id="64",
            observed_at=observed_at,
            price=Decimal("7.23"),
            currency="USD",
        ),
    }

    assert actual == expected


@pytest.mark.integration
def test_sqlalchemy_offer_query_returns_only_offers_from_latest_pipeline_run(
    database_session: Session,
) -> None:
    requested_source = "cheapshark"
    requested_external_product_id = 612
    earlier_started_at = datetime(2026, 9, 14, 16, 22, tzinfo=UTC)
    earlier_observed_at = datetime(2026, 9, 14, 16, 23, tzinfo=UTC)
    latest_started_at = datetime(2026, 9, 14, 16, 33, tzinfo=UTC)
    latest_observed_at = datetime(2026, 9, 14, 16, 34, tzinfo=UTC)

    observation_1 = OfferObservationInput(
        source_seller_id="23",
        observed_at=earlier_observed_at,
        price=Decimal("10.23"),
        currency="USD",
    )

    observation_2 = OfferObservationInput(
        source_seller_id="64",
        observed_at=earlier_observed_at,
        price=Decimal("7.23"),
        currency="USD",
    )

    earlier_run = _make_completed_run(
        started_at=earlier_started_at,
        finished_at=earlier_observed_at,
        observations=(observation_1, observation_2),
    )

    observation_3 = OfferObservationInput(
        source_seller_id="23",
        observed_at=latest_observed_at,
        price=Decimal("12.99"),
        currency="USD",
    )

    latest_run = _make_completed_run(
        started_at=latest_started_at,
        finished_at=latest_observed_at,
        observations=(observation_3,),
    )

    writer = SqlAlchemyPipelineRunWriter(database_session)
    writer.persist(earlier_run)
    writer.persist(latest_run)

    query = SqlAlchemyOfferQuery(database_session)

    returned_offers = query.get_current_offers(
        requested_source,
        requested_external_product_id,
    )
    actual = set(returned_offers)

    expected = {
        CurrentOffer(
            product_title="Batman",
            source_seller_id="23",
            observed_at=latest_observed_at,
            price=Decimal("12.99"),
            currency="USD",
        ),
    }

    assert actual == expected


@pytest.mark.integration
def test_sqlalchemy_offer_query_orders_current_offers_by_price_ascending(
    database_session: Session,
) -> None:
    requested_source = "cheapshark"
    requested_external_product_id = 612
    observed_at = datetime(2026, 9, 15, 8, 24, tzinfo=UTC)
    observation = OfferObservationInput(
        source_seller_id="23",
        observed_at=observed_at,
        price=Decimal("10.23"),
        currency="USD",
    )
    cheapest_observation = OfferObservationInput(
        source_seller_id="45",
        observed_at=observed_at,
        price=Decimal("7.99"),
        currency="USD",
    )

    completed_run = _make_completed_run(
        started_at=datetime(2026, 9, 15, 8, 23, tzinfo=UTC),
        finished_at=datetime(2026, 9, 15, 8, 24, tzinfo=UTC),
        observations=(observation, cheapest_observation),
    )

    writer = SqlAlchemyPipelineRunWriter(database_session)
    writer.persist(completed_run)

    query = SqlAlchemyOfferQuery(database_session)
    returned_offers = query.get_current_offers(
        requested_source,
        requested_external_product_id,
    )

    expected_offers = (
        CurrentOffer(
            product_title="Batman",
            source_seller_id="45",
            observed_at=observed_at,
            price=Decimal("7.99"),
            currency="USD",
        ),
        CurrentOffer(
            product_title="Batman",
            source_seller_id="23",
            observed_at=observed_at,
            price=Decimal("10.23"),
            currency="USD",
        ),
    )

    assert returned_offers == expected_offers


@pytest.mark.integration
def test_sqlalchemy_offer_query_returns_offer_history_in_chronological_order(
    database_session: Session,
) -> None:
    requested_source = "cheapshark"
    requested_external_product_id = 612
    started_at = datetime(2026, 9, 15, 8, 24, tzinfo=UTC)
    finished_at = datetime(2026, 9, 15, 8, 25, tzinfo=UTC)

    earlier_observation = OfferObservationInput(
        source_seller_id="23",
        observed_at=finished_at,
        price=Decimal("10.23"),
        currency="USD",
    )
    latest_started_at = datetime(2026, 9, 15, 8, 44, tzinfo=UTC)
    latest_finished_at = datetime(2026, 9, 15, 8, 45, tzinfo=UTC)

    latest_observation = OfferObservationInput(
        source_seller_id="45",
        observed_at=latest_finished_at,
        price=Decimal("9.23"),
        currency="USD",
    )

    earlier_run = _make_completed_run(
        started_at=started_at,
        finished_at=finished_at,
        observations=(earlier_observation,),
    )
    latest_run = _make_completed_run(
        started_at=latest_started_at,
        finished_at=latest_finished_at,
        observations=(latest_observation,),
    )

    writer = SqlAlchemyPipelineRunWriter(database_session)
    writer.persist(latest_run)
    writer.persist(earlier_run)

    query = SqlAlchemyOfferQuery(database_session)

    returned_offers = query.get_offer_history(
        requested_source,
        requested_external_product_id,
    )

    expected_offers = (
        OfferHistoryEntry(
            product_title="Batman",
            source_seller_id="23",
            observed_at=finished_at,
            price=Decimal("10.23"),
            currency="USD",
        ),
        OfferHistoryEntry(
            product_title="Batman",
            source_seller_id="45",
            observed_at=latest_finished_at,
            price=Decimal("9.23"),
            currency="USD",
        ),
    )

    assert returned_offers == expected_offers


@pytest.mark.integration
def test_sqlalchemy_offer_query_returns_empty_tuple_for_unknown_product(
    database_session: Session,
) -> None:
    unknown_source = "unknown_source"
    unknown_external_product_id = 313

    query = SqlAlchemyOfferQuery(database_session)

    returned_offers = query.get_current_offers(
        unknown_source,
        unknown_external_product_id,
    )

    assert returned_offers == ()


@pytest.mark.integration
def test_sqlalchemy_offer_query_returns_empty_tuple_when_latest_run_has_no_observations(
    database_session: Session,
) -> None:
    requested_source = "cheapshark"
    requested_external_product_id = 612
    earlier_run = _make_completed_run()
    latest_started_at = datetime(2026, 9, 15, 10, 22, tzinfo=UTC)
    latest_finished_at = datetime(2026, 9, 15, 10, 23, tzinfo=UTC)
    latest_run = _make_completed_run(
        started_at=latest_started_at,
        finished_at=latest_finished_at,
        observations=(),
    )

    writer = SqlAlchemyPipelineRunWriter(database_session)
    writer.persist(earlier_run)
    writer.persist(latest_run)

    query = SqlAlchemyOfferQuery(database_session)

    returned_offers = query.get_current_offers(
        requested_source,
        requested_external_product_id,
    )

    assert returned_offers == ()
