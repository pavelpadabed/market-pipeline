from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from market_pipeline.persistence.inputs import (
    CompletedPipelineRunInput,
    OfferObservationInput,
    ProductInput,
    ProcessingFailureInput,
)
from market_pipeline.persistence.types import (
    PipelineRunOutcome,
    ProcessingStage,
)

def _make_completed_run(**overrides: object) -> CompletedPipelineRunInput:
    started_at = datetime(2026, 9, 12, 17, 13, tzinfo=UTC)
    finished_at = datetime(2026, 9, 12, 17, 14, tzinfo=UTC)

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


def test_product_input_preserves_required_values() -> None:
    product = ProductInput(
        source="cheapshark",
        external_product_id=612,
        title="Batman",
    )

    assert product.source == "cheapshark"
    assert product.external_product_id == 612
    assert product.title == "Batman"


@pytest.mark.parametrize(
    "invalid_source",
    [
        None,
        612,
        True,
        12.99,
        [],
        {},
    ],
    ids=(
        "none",
        "integer",
        "boolean",
        "float",
        "list",
        "mapping",
    ),
)
def test_product_input_rejects_non_string_source(
    invalid_source: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="source must be an instance of str",
    ):
        ProductInput(
            source=invalid_source,
            external_product_id=612,
            title="Batman",
        )


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
def test_product_input_rejects_blank_source(
    blank_source: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="source must not be blank",
    ):
        ProductInput(
            source=blank_source,
            external_product_id=612,
            title="Batman",
        )


@pytest.mark.parametrize(
    "invalid_external_product_id",
    [
        None,
        "612",
        True,
        612.0,
        [],
        {},
    ],
    ids=(
        "none",
        "string",
        "boolean",
        "float",
        "list",
        "mapping",
    ),
)
def test_product_input_rejects_non_integer_external_product_id(
    invalid_external_product_id: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="external_product_id must have type int",
    ):
        ProductInput(
            source="cheapshark",
            external_product_id=invalid_external_product_id,
            title="Batman",
        )


@pytest.mark.parametrize(
    "invalid_title",
    [
        None,
        612,
        True,
        12.99,
        [],
        {},
    ],
    ids=(
        "none",
        "integer",
        "boolean",
        "float",
        "list",
        "mapping",
    ),
)
def test_product_input_rejects_non_string_title(
    invalid_title: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="title must be an instance of str",
    ):
        ProductInput(
            source="cheapshark",
            external_product_id=612,
            title=invalid_title,
        )


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
def test_product_input_rejects_blank_title(
    blank_title: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="title must not be blank",
    ):
        ProductInput(
            source="cheapshark",
            external_product_id=612,
            title=blank_title,
        )


def test_offer_observation_input_preserves_required_values() -> None:
    expected_observed_at = datetime(
        2026,
        9,
        12,
        10,
        9,
        tzinfo=UTC,
    )
    observation = OfferObservationInput(
        source_seller_id="23",
        observed_at=expected_observed_at,
        price=Decimal("12.99"),
        currency="USD",
    )

    assert isinstance(observation, OfferObservationInput)
    assert observation.source_seller_id == "23"
    assert observation.observed_at == expected_observed_at
    assert observation.price == Decimal("12.99")
    assert observation.currency == "USD"


@pytest.mark.parametrize(
    "invalid_source_seller_id",
    [
        None,
        23,
        True,
        12.99,
        [],
        {},
    ],
    ids=(
        "none",
        "integer",
        "boolean",
        "float",
        "list",
        "mapping",
    ),
)
def test_offer_observation_input_rejects_non_string_source_seller_id(
    invalid_source_seller_id: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="source_seller_id must be an instance of str",
    ):
        OfferObservationInput(
            source_seller_id=invalid_source_seller_id,
            observed_at=datetime(2026, 9, 12, 10, 9, tzinfo=UTC),
            price=Decimal("12.99"),
            currency="USD",
        )


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
def test_offer_observation_input_rejects_blank_source_seller_id(
    blank_source_seller_id: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="source_seller_id must not be blank",
    ):
        OfferObservationInput(
            source_seller_id=blank_source_seller_id,
            observed_at=datetime(2026, 9, 12, 10, 9, tzinfo=UTC),
            price=Decimal("12.99"),
            currency="USD",
        )


@pytest.mark.parametrize(
    "invalid_observed_at",
    [
        None,
        "2026-09-12T10:09:00Z",
        0,
        True,
        date(2026, 9, 12),
        {},
    ],
    ids=(
        "none",
        "string",
        "integer",
        "boolean",
        "date",
        "mapping",
    ),
)
def test_offer_observation_input_rejects_non_datetime_observed_at(
    invalid_observed_at: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="observed_at must be an instance of datetime",
    ):
        OfferObservationInput(
            source_seller_id="23",
            observed_at=invalid_observed_at,
            price=Decimal("12.99"),
            currency="USD",
        )


def test_offer_observation_input_rejects_naive_observed_at() -> None:
    naive_observed_at = datetime(2026, 9, 12, 11, 21)

    with pytest.raises(
        ValueError,
        match="observed_at must be timezone-aware",
    ):
        OfferObservationInput(
            source_seller_id="23",
            observed_at=naive_observed_at,
            price=Decimal("12.99"),
            currency="USD",
        )


@pytest.mark.parametrize(
    "invalid_price",
    [
        None,
        "12.99",
        12,
        12.99,
        True,
        {},
    ],
    ids=(
        "none",
        "string",
        "integer",
        "float",
        "boolean",
        "mapping",
    ),
)
def test_offer_observation_input_rejects_non_decimal_price(
    invalid_price: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="price must be an instance of Decimal",
    ):
        OfferObservationInput(
            source_seller_id="23",
            observed_at=datetime(2026, 9, 12, 11, 21, tzinfo=UTC),
            price=invalid_price,
            currency="USD",
        )


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
def test_offer_observation_input_rejects_non_finite_price(
    non_finite_price: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="price must be finite",
    ):
        OfferObservationInput(
            source_seller_id="23",
            observed_at=datetime(2026, 9, 12, 11, 21, tzinfo=UTC),
            price=non_finite_price,
            currency="USD",
        )


def test_offer_observation_input_rejects_negative_price() -> None:
    with pytest.raises(
        ValueError,
        match="price must be non-negative",
    ):
        OfferObservationInput(
            source_seller_id="23",
            observed_at=datetime(2026, 9, 12, 11, 21, tzinfo=UTC),
            price=Decimal("-0.01"),
            currency="USD",
        )


def test_offer_observation_input_accepts_zero_price() -> None:
    observation = OfferObservationInput(
        source_seller_id="23",
        observed_at=datetime(2026, 9, 12, 11, 21, tzinfo=UTC),
        price=Decimal("0"),
        currency="USD",
    )

    assert observation.price == Decimal("0")


@pytest.mark.parametrize(
    "invalid_currency",
    [
        None,
        840,
        True,
        12.99,
        [],
        {},
    ],
    ids=(
        "none",
        "integer",
        "boolean",
        "float",
        "list",
        "mapping",
    ),
)
def test_offer_observation_input_rejects_non_string_currency(
    invalid_currency: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="currency must be an instance of str",
    ):
        OfferObservationInput(
            source_seller_id="23",
            observed_at=datetime(2026, 9, 12, 11, 21, tzinfo=UTC),
            price=Decimal("12.99"),
            currency=invalid_currency,
        )


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
def test_offer_observation_input_rejects_blank_currency(
    blank_currency: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="currency must not be blank",
    ):
        OfferObservationInput(
            source_seller_id="23",
            observed_at=datetime(2026, 9, 12, 11, 21, tzinfo=UTC),
            price=Decimal("12.99"),
            currency=blank_currency,
        )


def test_processing_failure_input_preserves_required_values() -> None:
    failure = ProcessingFailureInput(
        stage=ProcessingStage.EXTRACTION,
        source_index=1,
        diagnostic_message="invalid mapping",
    )

    assert isinstance(failure, ProcessingFailureInput)
    assert failure.stage is ProcessingStage.EXTRACTION
    assert failure.source_index == 1
    assert failure.diagnostic_message == "invalid mapping"


def test_processing_failure_input_accepts_missing_source_index() -> None:
    failure = ProcessingFailureInput(
        stage=ProcessingStage.ACQUISITION,
        source_index=None,
        diagnostic_message="request failed",
    )

    assert failure.source_index is None


@pytest.mark.parametrize(
    "invalid_stage",
    [
        "extraction",
        1,
        PipelineRunOutcome.FAILURE,
        None,
    ],
    ids=("string", "integer", "different-enum", "none"),
)
def test_processing_failure_input_rejects_invalid_stage(
    invalid_stage: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="stage must be an instance of ProcessingStage",
    ):
        # noinspection PyTypeChecker
        ProcessingFailureInput(
            stage=invalid_stage,
            source_index=1,
            diagnostic_message="invalid mapping",
        )


@pytest.mark.parametrize(
    "invalid_source_index",
    [
        "1",
        1.0,
        Decimal("1"),
        True,
    ],
    ids=("string", "float", "decimal", "boolean"),
)
def test_processing_failure_input_rejects_non_integer_source_index(
    invalid_source_index: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="source_index must have type int or be None",
    ):
        # noinspection PyTypeChecker
        ProcessingFailureInput(
            stage=ProcessingStage.EXTRACTION,
            source_index=invalid_source_index,
            diagnostic_message="invalid mapping",
        )


def test_processing_failure_input_rejects_negative_source_index() -> None:
    with pytest.raises(
        ValueError,
        match="source_index must be non-negative",
    ):
        ProcessingFailureInput(
            stage=ProcessingStage.EXTRACTION,
            source_index=-1,
            diagnostic_message="invalid mapping",
        )


@pytest.mark.parametrize(
    "invalid_diagnostic_message",
    [None, 1, 1.0, True],
    ids=("none", "integer", "float", "boolean"),
)
def test_processing_failure_input_rejects_non_string_diagnostic_message(
    invalid_diagnostic_message: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="diagnostic_message must be an instance of str",
    ):
        # noinspection PyTypeChecker
        ProcessingFailureInput(
            stage=ProcessingStage.EXTRACTION,
            source_index=1,
            diagnostic_message=invalid_diagnostic_message,
        )


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
def test_processing_failure_input_rejects_blank_diagnostic_message(
    blank_diagnostic_message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="diagnostic_message must not be blank",
    ):
        ProcessingFailureInput(
            stage=ProcessingStage.EXTRACTION,
            source_index=1,
            diagnostic_message=blank_diagnostic_message,
        )


def test_completed_pipeline_run_input_preserves_successful_run_values() -> None:
    started_at = datetime(2026, 9, 12, 16, 48, tzinfo=UTC)
    finished_at = datetime(2026, 9, 12, 16, 49, tzinfo=UTC)
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

    completed_run = CompletedPipelineRunInput(
        requested_source="cheapshark",
        requested_external_product_id=612,
        started_at=started_at,
        finished_at=finished_at,
        outcome=PipelineRunOutcome.SUCCESS,
        product=product,
        observations=(observation,),
        failures=(),
    )

    assert completed_run.requested_source == "cheapshark"
    assert completed_run.requested_external_product_id == 612
    assert completed_run.started_at == started_at
    assert completed_run.finished_at == finished_at
    assert completed_run.outcome is PipelineRunOutcome.SUCCESS
    assert completed_run.product is product
    assert completed_run.observations == (observation,)
    assert completed_run.failures == ()


@pytest.mark.parametrize(
    "invalid_requested_source",
    [None, 1, 1.0, True],
    ids=("none", "integer", "float", "boolean"),
)
def test_completed_pipeline_run_input_rejects_non_string_requested_source(
    invalid_requested_source: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="requested_source must be an instance of str",
    ):
        # noinspection PyTypeChecker
        CompletedPipelineRunInput(
            requested_source=invalid_requested_source,
            requested_external_product_id=612,
            started_at=datetime(2026, 9, 12, 16, 48, tzinfo=UTC),
            finished_at=datetime(2026, 9, 12, 16, 49, tzinfo=UTC),
            outcome=PipelineRunOutcome.SUCCESS,
            product=ProductInput(
                source="cheapshark",
                external_product_id=612,
                title="Batman",
            ),
            observations=(),
            failures=(),
        )


@pytest.mark.parametrize(
    "blank_requested_source",
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
def test_completed_pipeline_run_input_rejects_blank_requested_source(
    blank_requested_source: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="requested_source must not be blank",
    ):
        CompletedPipelineRunInput(
            requested_source=blank_requested_source,
            requested_external_product_id=612,
            started_at=datetime(2026, 9, 12, 16, 48, tzinfo=UTC),
            finished_at=datetime(2026, 9, 12, 16, 49, tzinfo=UTC),
            outcome=PipelineRunOutcome.SUCCESS,
            product=ProductInput(
                source="cheapshark",
                external_product_id=612,
                title="Batman",
            ),
            observations=(),
            failures=(),
        )


@pytest.mark.parametrize(
    "invalid_requested_external_product_id",
    [None, "612", 612.0, Decimal("612"), True],
    ids=("none", "string", "float", "decimal", "boolean"),
)
def test_completed_pipeline_run_input_rejects_non_integer_requested_external_product_id(
    invalid_requested_external_product_id: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="requested_external_product_id must have type int",
    ):
        # noinspection PyTypeChecker
        _make_completed_run(
            requested_external_product_id=invalid_requested_external_product_id
        )


@pytest.mark.parametrize(
    "timestamp_field",
    ["started_at", "finished_at"],
    ids=("started-at", "finished-at"),
)
@pytest.mark.parametrize(
    "invalid_timestamp",
    [None, "2026-09-12T17:13:00+00:00", date(2026, 9, 12), True],
    ids=("none", "string", "date", "boolean"),
)
def test_completed_pipeline_run_input_rejects_non_datetime_timestamps(
    timestamp_field: str,
    invalid_timestamp: object,
) -> None:
    with pytest.raises(
        TypeError,
        match=f"{timestamp_field} must be an instance of datetime",
    ):
        _make_completed_run(**{timestamp_field: invalid_timestamp})


@pytest.mark.parametrize(
    "timestamp_field",
    ["started_at", "finished_at"],
    ids=("started-at", "finished-at"),
)
def test_completed_pipeline_run_input_rejects_naive_timestamps(
    timestamp_field: str,
) -> None:
    naive_timestamp = datetime(2026, 9, 12, 17, 13)

    with pytest.raises(
        ValueError,
        match=f"{timestamp_field} must be timezone-aware",
    ):
        _make_completed_run(**{timestamp_field: naive_timestamp})


def test_completed_pipeline_run_input_rejects_finished_at_before_started_at(
) -> None:
    with pytest.raises(
        ValueError,
        match="finished_at must not be earlier than started_at",
    ):
        _make_completed_run(
            finished_at=datetime(2026, 9, 12, 17, 12, tzinfo=UTC)
        )


def test_completed_pipeline_run_input_accepts_equal_timestamps() -> None:
    timestamp = datetime(2026, 9, 12, 17, 13, tzinfo=UTC)

    completed_run = _make_completed_run(
        started_at=timestamp,
        finished_at=timestamp,
    )

    assert completed_run.started_at == completed_run.finished_at


@pytest.mark.parametrize(
    "invalid_outcome",
    ["success", None, 1, 1.0, ProcessingStage.EXTRACTION],
    ids=("string", "none", "integer", "float", "different-enum"),
)
def test_completed_pipeline_run_input_rejects_invalid_outcome(
    invalid_outcome: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="outcome must be an instance of PipelineRunOutcome",
    ):
        # noinspection PyTypeChecker
        _make_completed_run(outcome=invalid_outcome)


def test_completed_pipeline_run_input_accepts_missing_product_for_failed_run() -> None:
    failure = ProcessingFailureInput(
        stage=ProcessingStage.ACQUISITION,
        source_index=None,
        diagnostic_message="request failed",
    )

    completed_run = _make_completed_run(
        outcome=PipelineRunOutcome.FAILURE,
        product=None,
        observations=(),
        failures=(failure,),
    )

    assert completed_run.product is None


@pytest.mark.parametrize(
    "invalid_product",
    [
        "Batman",
        {"source": "cheapshark"},
        612,
        OfferObservationInput(
            source_seller_id="23",
            observed_at=datetime(2026, 9, 12, 17, 14, tzinfo=UTC),
            price=Decimal("10.23"),
            currency="USD",
        ),
    ],
    ids=("string", "mapping", "integer", "observation-input"),
)
def test_completed_pipeline_run_input_rejects_invalid_product(
    invalid_product: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="product must be an instance of ProductInput or be None",
    ):
        _make_completed_run(product=invalid_product)


@pytest.mark.parametrize(
    "invalid_observations",
    [
        None,
        [],
        {},
        OfferObservationInput(
            source_seller_id="23",
            observed_at=datetime(2026, 9, 12, 17, 14, tzinfo=UTC),
            price=Decimal("10.23"),
            currency="USD",
        ),
    ],
    ids=("none", "list", "mapping", "single-observation"),
)
def test_completed_pipeline_run_input_rejects_non_tuple_observations(
    invalid_observations: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="observations must be an instance of tuple",
    ):
        _make_completed_run(observations=invalid_observations)


@pytest.mark.parametrize(
    "invalid_observation",
    [
        None,
        "offer",
        1,
        ProductInput(
            source="cheapshark",
            external_product_id=612,
            title="Batman",
        ),
    ],
    ids=("none", "string", "integer", "product-input"),
)
def test_completed_pipeline_run_input_rejects_invalid_observation_elements(
    invalid_observation: object,
) -> None:
    valid_observation = OfferObservationInput(
        source_seller_id="23",
        observed_at=datetime(2026, 9, 12, 17, 14, tzinfo=UTC),
        price=Decimal("10.23"),
        currency="USD",
    )

    with pytest.raises(
        TypeError,
        match="observations must contain only OfferObservationInput instances",
    ):
        _make_completed_run(
            observations=(valid_observation, invalid_observation)
        )


@pytest.mark.parametrize(
    "invalid_failures",
    [
        None,
        [],
        {},
        ProcessingFailureInput(
            stage=ProcessingStage.EXTRACTION,
            source_index=1,
            diagnostic_message="invalid mapping",
        ),
    ],
    ids=("none", "list", "mapping", "single-failure"),
)
def test_completed_pipeline_run_input_rejects_non_tuple_failures(
    invalid_failures: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="failures must be an instance of tuple",
    ):
        _make_completed_run(failures=invalid_failures)


@pytest.mark.parametrize(
    "invalid_failure",
    [
        None,
        "failure",
        1,
        OfferObservationInput(
            source_seller_id="23",
            observed_at=datetime(2026, 9, 12, 17, 14, tzinfo=UTC),
            price=Decimal("10.23"),
            currency="USD",
        ),
    ],
    ids=("none", "string", "integer", "observation-input"),
)
def test_completed_pipeline_run_input_rejects_invalid_failure_elements(
    invalid_failure: object,
) -> None:
    valid_failure = ProcessingFailureInput(
        stage=ProcessingStage.EXTRACTION,
        source_index=1,
        diagnostic_message="invalid mapping",
    )

    with pytest.raises(
        TypeError,
        match="failures must contain only ProcessingFailureInput instances",
    ):
        _make_completed_run(failures=(valid_failure, invalid_failure))


def test_completed_pipeline_run_input_rejects_failures_for_success_outcome() -> None:
    failure = ProcessingFailureInput(
        stage=ProcessingStage.EXTRACTION,
        source_index=1,
        diagnostic_message="invalid mapping",
    )

    with pytest.raises(
        ValueError,
        match="successful run must not contain failures",
    ):
        _make_completed_run(failures=(failure,))


def test_completed_pipeline_run_input_rejects_missing_product_for_success_outcome(
) -> None:
    with pytest.raises(
        ValueError,
        match="successful run must contain a product",
    ):
        _make_completed_run(product=None)


def test_completed_pipeline_run_input_accepts_success_without_observations() -> None:
    completed_run = _make_completed_run(observations=())

    assert completed_run.observations == ()


def test_completed_pipeline_run_input_rejects_empty_failures_for_partial_failure_outcome(
) -> None:
    with pytest.raises(
        ValueError,
        match="partially failed run must contain at least one failure",
    ):
        _make_completed_run(outcome=PipelineRunOutcome.PARTIAL_FAILURE)


def test_completed_pipeline_run_input_rejects_empty_observations_for_partial_failure_outcome(
) -> None:
    failure = ProcessingFailureInput(
        stage=ProcessingStage.EXTRACTION,
        source_index=1,
        diagnostic_message="invalid mapping",
    )

    with pytest.raises(
        ValueError,
        match="partially failed run must contain at least one observation",
    ):
        _make_completed_run(
            outcome=PipelineRunOutcome.PARTIAL_FAILURE,
            observations=(),
            failures=(failure,),
        )


def test_completed_pipeline_run_input_rejects_missing_product_for_partial_failure_outcome(
) -> None:
    failure = ProcessingFailureInput(
        stage=ProcessingStage.EXTRACTION,
        source_index=1,
        diagnostic_message="invalid mapping",
    )

    with pytest.raises(
        ValueError,
        match="partially failed run must contain a product",
    ):
        _make_completed_run(
            outcome=PipelineRunOutcome.PARTIAL_FAILURE,
            product=None,
            failures=(failure,),
        )


def test_completed_pipeline_run_input_accepts_partial_failure() -> None:
    failure = ProcessingFailureInput(
        stage=ProcessingStage.EXTRACTION,
        source_index=1,
        diagnostic_message="invalid mapping",
    )

    completed_run = _make_completed_run(
        outcome=PipelineRunOutcome.PARTIAL_FAILURE,
        failures=(failure,),
    )

    assert completed_run.outcome is PipelineRunOutcome.PARTIAL_FAILURE
    assert completed_run.failures == (failure,)


def test_completed_pipeline_run_input_rejects_observations_for_failure_outcome() -> None:
    failure = ProcessingFailureInput(
        stage=ProcessingStage.ACQUISITION,
        source_index=None,
        diagnostic_message="request failed",
    )

    with pytest.raises(
        ValueError,
        match="failed run must not contain observations",
    ):
        _make_completed_run(
            outcome=PipelineRunOutcome.FAILURE,
            failures=(failure,),
        )


def test_completed_pipeline_run_input_rejects_empty_failures_for_failure_outcome(
) -> None:
    with pytest.raises(
        ValueError,
        match="failed run must contain at least one failure",
    ):
        _make_completed_run(
            outcome=PipelineRunOutcome.FAILURE,
            product=None,
            observations=(),
        )


def test_completed_pipeline_run_input_accepts_failure_with_product() -> None:
    failure = ProcessingFailureInput(
        stage=ProcessingStage.EXTRACTION,
        source_index=1,
        diagnostic_message="invalid mapping",
    )

    completed_run = _make_completed_run(
        outcome=PipelineRunOutcome.FAILURE,
        observations=(),
        failures=(failure,),
    )

    assert completed_run.outcome is PipelineRunOutcome.FAILURE
    assert completed_run.product is not None
    assert completed_run.observations == ()
    assert completed_run.failures == (failure,)
