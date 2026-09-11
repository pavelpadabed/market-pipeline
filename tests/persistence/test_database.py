from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import (
    Engine,
    text,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from market_pipeline.persistence.models import (
    LogicalOffer,
    OfferObservation,
    PipelineRun,
    PipelineRunOutcome,
    ProcessingFailure,
    ProcessingStage,
    SourceProduct,
)


def _make_source_product(**overrides) -> SourceProduct:
    data = {
        "source": "cheapshark",
        "external_product_id": 612,
        "title": "Batman",
    }
    data.update(overrides)
    return SourceProduct(**data)


def _make_logical_offer(
    source_product_id: int,
    **overrides,
) -> LogicalOffer:
    data = {
        "source_product_id": source_product_id,
        "source_seller_id": "23",
    }
    data.update(overrides)
    return LogicalOffer(**data)


def _make_pipeline_run(**overrides) -> PipelineRun:
    started_at = datetime(2026, 9, 9, 19, 34, tzinfo=UTC)
    finished_at = datetime(2026, 9, 9, 19, 34, tzinfo=UTC)
    data = {
        "started_at": started_at,
        "finished_at": finished_at,
        "outcome": PipelineRunOutcome.SUCCESS,
    }
    data.update(overrides)
    return PipelineRun(**data)


def _make_offer_observation(
    logical_offer_id: int,
    run_id: int,
    **overrides,
) -> OfferObservation:
    observed_at = datetime(2026, 9, 9, 19, 34, tzinfo=UTC)
    data = {
        "logical_offer_id": logical_offer_id,
        "run_id": run_id,
        "observed_at": observed_at,
        "price": Decimal("12.99"),
        "currency": "USD",
    }
    data.update(overrides)
    return OfferObservation(**data)


def _make_processing_failure(
    pipeline_run_id: int,
    **overrides,
) -> ProcessingFailure:
    data = {
        "run_id": pipeline_run_id,
        "stage": ProcessingStage.EXTRACTION,
        "source_index": 1,
        "diagnostic_message": "invalid mapping",
    }
    data.update(overrides)
    return ProcessingFailure(**data)


@pytest.mark.integration
def test_database_engine_connects_to_expected_test_database(
    database_engine: Engine,
) -> None:
    with database_engine.connect() as connection:
        database_name = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

    assert database_name == "market_pipeline_test"


@pytest.mark.integration
def test_source_product_persists_required_fields_with_generated_identity(
    database_session: Session,
) -> None:
    source_product = SourceProduct(
        source="cheapshark",
        external_product_id=612,
        title="Batman",
    )
    assert source_product.id is None
    database_session.add(source_product)
    database_session.flush()
    assert type(source_product.id) is int
    assert source_product.source == "cheapshark"
    assert source_product.external_product_id == 612
    assert source_product.title == "Batman"


@pytest.mark.integration
def test_source_product_rejects_duplicate_business_identity(
    database_session: Session,
) -> None:
    source_product = SourceProduct(
        source="cheapshark",
        external_product_id=612,
        title="Batman",
    )

    same_source_product = SourceProduct(
        source="cheapshark",
        external_product_id=612,
        title="Batman: Gotham City",
    )

    database_session.add_all(
        [
            source_product,
            same_source_product,
        ],
    )
    with pytest.raises(IntegrityError):
        database_session.flush()


@pytest.mark.integration
def test_source_product_allows_same_external_id_for_different_sources(
    database_session: Session,
) -> None:
    source_product = SourceProduct(
        source="cheapshark",
        external_product_id=612,
        title="Batman",
    )
    another_source_product = SourceProduct(
        source="ceneo",
        external_product_id=612,
        title="Batman",
    )

    database_session.add_all(
        [
            source_product,
            another_source_product,
        ],
    )
    database_session.flush()


@pytest.mark.parametrize(
    "blank_source",
    [
        "",
        " ",
        "\t",
        "\n",
        "\r",
        "\f",
        "\v",
        " \t\n\r\f\v ",
    ],
    ids=(
        "empty",
        "space",
        "tab",
        "newline",
        "carriage-return",
        "form-feed",
        "vertical-tab",
        "mixed",
    ),
)
@pytest.mark.integration
def test_source_product_rejects_blank_source(
    blank_source: str,
    database_session: Session,
) -> None:
    source_product = SourceProduct(
        source=blank_source,
        external_product_id=612,
        title="Batman",
    )
    database_session.add(source_product)

    with pytest.raises(IntegrityError):
        database_session.flush()


@pytest.mark.parametrize(
    "blank_title",
    [
        "",
        " ",
        "\t",
        "\n",
        "\r",
        "\f",
        "\v",
        " \t\n\r\f\v ",
    ],
    ids=(
        "empty",
        "space",
        "tab",
        "newline",
        "carriage-return",
        "form-feed",
        "vertical-tab",
        "mixed",
    ),
)
@pytest.mark.integration
def test_source_product_rejects_blank_title(
    blank_title: str,
    database_session: Session,
) -> None:
    source_product = SourceProduct(
        source="cheapshark",
        external_product_id=612,
        title=blank_title,
    )
    database_session.add(source_product)

    with pytest.raises(IntegrityError):
        database_session.flush()


@pytest.mark.integration
def test_logical_offer_persists_for_existing_source_product_with_generated_identity(
    database_session: Session,
) -> None:
    source_product = SourceProduct(
        source="cheapshark",
        external_product_id=612,
        title="Batman",
    )

    database_session.add(source_product)
    database_session.flush()
    logical_offer = LogicalOffer(
        source_product_id=source_product.id,
        source_seller_id="23",
    )
    database_session.add(logical_offer)
    assert logical_offer.id is None
    database_session.flush()
    assert type(logical_offer.id) is int
    assert logical_offer.source_product_id == source_product.id
    assert logical_offer.source_seller_id == "23"


@pytest.mark.integration
def test_logical_offer_rejects_nonexistent_source_product(
    database_session: Session,
) -> None:
    logical_offer = LogicalOffer(
        source_product_id=234,
        source_seller_id="75",
    )
    database_session.add(logical_offer)

    with pytest.raises(IntegrityError):
        database_session.flush()


@pytest.mark.integration
def test_logical_offer_rejects_duplicate_business_identity(
    database_session: Session,
) -> None:
    source_product = _make_source_product()
    database_session.add(source_product)
    database_session.flush()
    logical_offer = LogicalOffer(
        source_product_id=source_product.id,
        source_seller_id="23",
    )
    database_session.add(logical_offer)
    database_session.flush()

    duplicate_logical_offer = LogicalOffer(
        source_product_id=source_product.id,
        source_seller_id="23",
    )
    database_session.add(duplicate_logical_offer)

    with pytest.raises(IntegrityError):
        database_session.flush()


@pytest.mark.integration
def test_logical_offer_allows_same_seller_id_for_different_source_products(
    database_session: Session,
) -> None:
    cheapshark_source_product = _make_source_product()
    database_session.add(cheapshark_source_product)
    database_session.flush()
    logical_offer = _make_logical_offer(cheapshark_source_product.id)
    database_session.add(logical_offer)
    database_session.flush()
    another_source_product = _make_source_product(source="ceneo")
    database_session.add(another_source_product)
    database_session.flush()
    another_logical_offer = _make_logical_offer(another_source_product.id)
    database_session.add(another_logical_offer)
    database_session.flush()
    assert (
        logical_offer.source_seller_id
        == another_logical_offer.source_seller_id
        == "23"
    )
    assert logical_offer.source_product_id != another_logical_offer.source_product_id


@pytest.mark.parametrize(
    "blank_source_seller_id",
    [
        "",
        " ",
        "\t",
        "\n",
        "\r",
        "\f",
        "\v",
        " \t\n\r\f\v ",
    ],
    ids=(
        "empty",
        "space",
        "tab",
        "newline",
        "carriage-return",
        "form-feed",
        "vertical-tab",
        "mixed",
    ),
)
@pytest.mark.integration
def test_logical_offer_rejects_blank_source_seller_id(
    blank_source_seller_id: str,
    database_session: Session,
) -> None:
    source_product = _make_source_product()
    database_session.add(source_product)
    database_session.flush()
    logical_offer = _make_logical_offer(
        source_product.id,
        source_seller_id=blank_source_seller_id,
    )
    database_session.add(logical_offer)

    with pytest.raises(IntegrityError):
        database_session.flush()


@pytest.mark.integration
def test_pipeline_run_persists_required_fields_with_generated_identity(
    database_session: Session,
) -> None:
    started_at = datetime(2026, 9, 9, 19, 0, tzinfo=UTC)
    finished_at = datetime(2026, 9, 9, 19, 1, tzinfo=UTC)

    pipeline_run = PipelineRun(
        started_at=started_at,
        finished_at=finished_at,
        outcome=PipelineRunOutcome.SUCCESS,
    )

    database_session.add(pipeline_run)
    assert pipeline_run.id is None
    database_session.flush()
    database_session.refresh(pipeline_run)

    assert type(pipeline_run.id) is int
    assert pipeline_run.started_at == started_at
    assert pipeline_run.finished_at == finished_at
    assert pipeline_run.outcome is PipelineRunOutcome.SUCCESS


@pytest.mark.integration
def test_pipeline_run_rejects_finished_at_before_started_at(
    database_session: Session,
) -> None:
    finished_at = datetime(2026, 9, 9, 19, 33, tzinfo=UTC)
    pipeline_run = _make_pipeline_run(finished_at=finished_at)

    database_session.add(pipeline_run)

    with pytest.raises(IntegrityError):
        database_session.flush()


@pytest.mark.integration
def test_pipeline_run_rejects_unsupported_outcome(
    database_session: Session,
) -> None:
    pipeline_run = _make_pipeline_run(outcome="cancelled")

    database_session.add(pipeline_run)

    with pytest.raises(IntegrityError):
        database_session.flush()


@pytest.mark.integration
def test_offer_observation_persists_required_fields_with_generated_identity(
    database_session: Session,
) -> None:
    source_product = _make_source_product()
    database_session.add(source_product)
    database_session.flush()

    logical_offer = _make_logical_offer(source_product.id)
    pipeline_run = _make_pipeline_run()
    database_session.add_all(
        [logical_offer, pipeline_run],
    )
    database_session.flush()

    observed_at = datetime(2026, 9, 9, 19, 34, tzinfo=UTC)
    offer_observation = OfferObservation(
        logical_offer_id=logical_offer.id,
        run_id=pipeline_run.id,
        observed_at=observed_at,
        price=Decimal("12.99"),
        currency="USD",
    )
    database_session.add(offer_observation)
    assert offer_observation.id is None
    database_session.flush()
    database_session.refresh(offer_observation)

    assert type(offer_observation.id) is int
    assert offer_observation.logical_offer_id == logical_offer.id
    assert offer_observation.run_id == pipeline_run.id
    assert offer_observation.observed_at == observed_at
    assert offer_observation.price == Decimal("12.99")
    assert offer_observation.currency == "USD"


@pytest.mark.integration
def test_offer_observation_rejects_negative_price(
    database_session: Session,
) -> None:
    source_product = _make_source_product()
    database_session.add(source_product)
    database_session.flush()

    logical_offer = _make_logical_offer(source_product.id)
    pipeline_run = _make_pipeline_run()
    database_session.add_all(
        [logical_offer, pipeline_run],
    )
    database_session.flush()

    offer_observation = _make_offer_observation(
        logical_offer.id,
        pipeline_run.id,
        price=Decimal("-0.01"),
    )
    database_session.add(offer_observation)

    with pytest.raises(IntegrityError):
        database_session.flush()


@pytest.mark.parametrize(
    "blank_currency",
    [
        "",
        " ",
        "\t",
        "\n",
        "\r",
        "\f",
        "\v",
        " \t\n\r\f\v ",
    ],
    ids=(
        "empty",
        "space",
        "tab",
        "newline",
        "carriage-return",
        "form-feed",
        "vertical-tab",
        "mixed",
    ),
)
@pytest.mark.integration
def test_offer_observation_rejects_blank_currency(
    blank_currency: str,
    database_session: Session,
) -> None:
    source_product = _make_source_product()
    database_session.add(source_product)
    database_session.flush()

    logical_offer = _make_logical_offer(source_product.id)
    pipeline_run = _make_pipeline_run()
    database_session.add_all(
        [logical_offer, pipeline_run],
    )
    database_session.flush()

    offer_observation = _make_offer_observation(
        logical_offer.id,
        pipeline_run.id,
        currency=blank_currency,
    )
    database_session.add(offer_observation)

    with pytest.raises(IntegrityError):
        database_session.flush()


@pytest.mark.parametrize(
    "non_finite_price",
    [
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
    ids=(
        "nan",
        "positive-infinity",
        "negative-infinity",
    ),
)
@pytest.mark.integration
def test_offer_observation_rejects_non_finite_price(
    database_session: Session,
    non_finite_price: Decimal,
) -> None:
    source_product = _make_source_product()
    database_session.add(source_product)
    database_session.flush()

    logical_offer = _make_logical_offer(source_product.id)
    pipeline_run = _make_pipeline_run()
    database_session.add_all(
        [logical_offer, pipeline_run],
    )
    database_session.flush()

    offer_observation = _make_offer_observation(
        logical_offer.id,
        pipeline_run.id,
        price=non_finite_price,
    )
    database_session.add(offer_observation)

    with pytest.raises(IntegrityError):
        database_session.flush()


@pytest.mark.integration
def test_offer_observation_rejects_nonexistent_logical_offer(
    database_session: Session,
) -> None:
    pipeline_run = _make_pipeline_run()
    database_session.add(pipeline_run)
    database_session.flush()

    offer_observation = _make_offer_observation(
        logical_offer_id=492,
        run_id=pipeline_run.id,
    )
    database_session.add(offer_observation)

    with pytest.raises(IntegrityError):
        database_session.flush()


@pytest.mark.integration
def test_offer_observation_rejects_nonexistent_pipeline_run(
    database_session: Session,
) -> None:
    source_product = _make_source_product()
    database_session.add(source_product)
    database_session.flush()

    logical_offer = _make_logical_offer(source_product.id)
    database_session.add(logical_offer)
    database_session.flush()

    offer_observation = _make_offer_observation(
        logical_offer_id=logical_offer.id,
        run_id=493,
    )
    database_session.add(offer_observation)

    with pytest.raises(IntegrityError):
        database_session.flush()


@pytest.mark.integration
def test_offer_observation_preserves_same_price_across_pipeline_runs(
    database_session: Session,
) -> None:
    source_product = _make_source_product()
    database_session.add(source_product)
    database_session.flush()

    logical_offer = _make_logical_offer(source_product.id)
    pipeline_run = _make_pipeline_run()
    database_session.add_all(
        [logical_offer, pipeline_run],
    )
    database_session.flush()

    offer_observation = _make_offer_observation(
        logical_offer.id,
        pipeline_run.id,
        price=Decimal("12.99"),
    )
    database_session.add(offer_observation)
    database_session.flush()

    aware_datetime = datetime(2026, 9, 11, 15, 38, tzinfo=UTC)
    pipeline_run_2 = _make_pipeline_run(
        started_at=aware_datetime,
        finished_at=aware_datetime,
    )
    database_session.add(pipeline_run_2)
    database_session.flush()

    offer_observation_2 = _make_offer_observation(
        logical_offer.id,
        pipeline_run_2.id,
        observed_at=aware_datetime,
        price=Decimal("12.99"),
    )
    database_session.add(offer_observation_2)
    database_session.flush()

    assert offer_observation.id != offer_observation_2.id
    assert (
        offer_observation.logical_offer_id
        == offer_observation_2.logical_offer_id
        == logical_offer.id
    )
    assert offer_observation.run_id == pipeline_run.id
    assert offer_observation_2.run_id == pipeline_run_2.id
    assert pipeline_run.id != pipeline_run_2.id
    assert offer_observation.price == offer_observation_2.price == Decimal("12.99")


@pytest.mark.integration
def test_processing_failure_persists_item_level_failure_with_generated_identity(
    database_session: Session,
) -> None:
    pipeline_run = _make_pipeline_run()
    database_session.add(pipeline_run)
    database_session.flush()

    processing_failure = ProcessingFailure(
        run_id=pipeline_run.id,
        stage=ProcessingStage.EXTRACTION,
        source_index=1,
        diagnostic_message="invalid mapping",
    )
    database_session.add(processing_failure)
    assert processing_failure.id is None
    database_session.flush()
    database_session.refresh(processing_failure)

    assert type(processing_failure.id) is int
    assert processing_failure.run_id == pipeline_run.id
    assert processing_failure.stage == ProcessingStage.EXTRACTION
    assert processing_failure.source_index == 1
    assert processing_failure.diagnostic_message == "invalid mapping"


@pytest.mark.integration
def test_processing_failure_persists_stage_level_failure_without_source_index(
    database_session: Session,
) -> None:
    pipeline_run = _make_pipeline_run()
    database_session.add(pipeline_run)
    database_session.flush()

    processing_failure = _make_processing_failure(
        pipeline_run.id,
        source_index=None,
    )
    database_session.add(processing_failure)
    database_session.flush()
    database_session.refresh(processing_failure)

    assert processing_failure.source_index is None


@pytest.mark.integration
def test_processing_failure_rejects_negative_source_index(
    database_session: Session,
) -> None:
    pipeline_run = _make_pipeline_run()
    database_session.add(pipeline_run)
    database_session.flush()

    processing_failure = _make_processing_failure(
        pipeline_run.id,
        source_index=-1,
    )
    database_session.add(processing_failure)

    with pytest.raises(IntegrityError):
        database_session.flush()


@pytest.mark.parametrize(
    "blank_diagnostic_message",
    [
        "",
        " ",
        "\t",
        "\n",
        "\r",
        "\f",
        "\v",
        " \t\n\r\f\v ",
    ],
    ids=(
        "empty",
        "space",
        "tab",
        "newline",
        "carriage-return",
        "form-feed",
        "vertical-tab",
        "mixed",
    ),
)
@pytest.mark.integration
def test_processing_failure_rejects_blank_diagnostic_message(
    blank_diagnostic_message: str,
    database_session: Session,
) -> None:
    pipeline_run = _make_pipeline_run()
    database_session.add(pipeline_run)
    database_session.flush()

    processing_failure = _make_processing_failure(
        pipeline_run.id,
        diagnostic_message=blank_diagnostic_message,
    )
    database_session.add(processing_failure)

    with pytest.raises(IntegrityError):
        database_session.flush()


@pytest.mark.integration
def test_processing_failure_rejects_nonexistent_pipeline_run(
    database_session: Session,
) -> None:
    processing_failure = _make_processing_failure(
        pipeline_run_id=205,
    )
    database_session.add(processing_failure)

    with pytest.raises(IntegrityError):
        database_session.flush()


@pytest.mark.integration
def test_processing_failure_rejects_unsupported_stage(
    database_session: Session,
) -> None:
    pipeline_run = _make_pipeline_run()
    database_session.add(pipeline_run)
    database_session.flush()

    processing_failure = _make_processing_failure(
        pipeline_run.id,
        stage="transform",
    )
    database_session.add(processing_failure)

    with pytest.raises(IntegrityError):
        database_session.flush()
