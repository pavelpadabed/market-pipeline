import pytest

from market_pipeline.application.models import (
    GameSearchFailure,
    GameSearchFailureOutcome,
    RunPipelineOutcome,
    RunPipelineResult,
)


def _make_run_pipeline_result(**overrides: object) -> RunPipelineResult:
    data = {
        "outcome": RunPipelineOutcome.OFFERS_SAVED,
        "retry_after_seconds": None,
        "source_record_count": 10,
        "saved_observation_count": 10,
        "rejected_record_count": 0,
    }
    data.update(overrides)

    return RunPipelineResult(**data)


@pytest.mark.parametrize(
    "non_rate_limited_outcome",
    [
        GameSearchFailureOutcome.CONNECTION_FAILED,
        GameSearchFailureOutcome.INVALID_SOURCE_RESPONSE,
        GameSearchFailureOutcome.SEARCH_REQUEST_FAILED,
    ],
)
def test_game_search_failure_rejects_retry_after_seconds_for_non_rate_limited_outcome(
    non_rate_limited_outcome: GameSearchFailureOutcome,
) -> None:
    with pytest.raises(
        ValueError,
        match="retry_after_seconds must be None unless outcome is rate_limited",
    ):
        GameSearchFailure(
            outcome=non_rate_limited_outcome,
            retry_after_seconds=30,
        )


@pytest.mark.parametrize(
    "retry_after_seconds",
    [None, 0, 30],
)
def test_game_search_failure_accepts_retry_after_seconds_when_rate_limited(
    retry_after_seconds: int | None,
) -> None:
    failure = GameSearchFailure(
        outcome=GameSearchFailureOutcome.RATE_LIMITED,
        retry_after_seconds=retry_after_seconds,
    )

    assert failure.retry_after_seconds == retry_after_seconds


def test_run_pipeline_result_preserves_counts_for_offers_saved() -> None:
    expected_result = {
        "outcome": RunPipelineOutcome.OFFERS_SAVED,
        "retry_after_seconds": None,
        "source_record_count": 10,
        "saved_observation_count": 10,
        "rejected_record_count": 0,
    }

    result = RunPipelineResult(**expected_result)

    assert result.outcome is RunPipelineOutcome.OFFERS_SAVED
    assert result.retry_after_seconds is None
    assert result.source_record_count == 10
    assert result.saved_observation_count == 10
    assert result.rejected_record_count == 0


def test_run_pipeline_result_accepts_no_offers_with_zero_counts() -> None:
    expected_result = {
        "outcome": RunPipelineOutcome.NO_OFFERS,
        "retry_after_seconds": None,
        "source_record_count": 0,
        "saved_observation_count": 0,
        "rejected_record_count": 0,
    }

    result = RunPipelineResult(**expected_result)

    assert result.outcome is RunPipelineOutcome.NO_OFFERS
    assert result.retry_after_seconds is None
    assert result.source_record_count == 0
    assert result.saved_observation_count == 0
    assert result.rejected_record_count == 0


def test_run_pipeline_result_accepts_partially_saved_offers() -> None:
    expected_result = {
        "outcome": RunPipelineOutcome.OFFERS_PARTIALLY_SAVED,
        "retry_after_seconds": None,
        "source_record_count": 2,
        "saved_observation_count": 1,
        "rejected_record_count": 1,
    }

    result = RunPipelineResult(**expected_result)

    assert result.outcome is RunPipelineOutcome.OFFERS_PARTIALLY_SAVED
    assert result.retry_after_seconds is None
    assert result.source_record_count == 2
    assert result.saved_observation_count == 1
    assert result.rejected_record_count == 1


def test_run_pipeline_result_accepts_all_offers_rejected() -> None:
    expected_result = {
        "outcome": RunPipelineOutcome.ALL_OFFERS_REJECTED,
        "retry_after_seconds": None,
        "source_record_count": 2,
        "saved_observation_count": 0,
        "rejected_record_count": 2,
    }

    result = RunPipelineResult(**expected_result)

    assert result.outcome is RunPipelineOutcome.ALL_OFFERS_REJECTED
    assert result.retry_after_seconds is None
    assert result.source_record_count == 2
    assert result.saved_observation_count == 0
    assert result.rejected_record_count == 2


@pytest.mark.parametrize(
    "outcome",
    [RunPipelineOutcome.PROCESSING_FAILED, RunPipelineOutcome.CONNECTION_ERROR],
)
def test_run_pipeline_result_accepts_early_failure_without_counts(
    outcome: RunPipelineOutcome,
) -> None:
    expected_result = {
        "outcome": outcome,
        "retry_after_seconds": None,
        "source_record_count": None,
        "saved_observation_count": None,
        "rejected_record_count": None,
    }

    result = RunPipelineResult(**expected_result)

    assert result.outcome is outcome
    assert result.retry_after_seconds is None
    assert result.source_record_count is None
    assert result.saved_observation_count is None
    assert result.rejected_record_count is None


@pytest.mark.parametrize("retry_after_seconds", [None, 0, 30])
def test_run_pipeline_result_accepts_rate_limit_with_optional_retry_delay(
    retry_after_seconds: int | None,
) -> None:
    expected_result = {
        "outcome": RunPipelineOutcome.RATE_LIMITED,
        "retry_after_seconds": retry_after_seconds,
        "source_record_count": None,
        "saved_observation_count": None,
        "rejected_record_count": None,
    }

    result = RunPipelineResult(**expected_result)

    assert result.outcome is RunPipelineOutcome.RATE_LIMITED
    assert result.retry_after_seconds == retry_after_seconds
    assert result.source_record_count is None
    assert result.saved_observation_count is None
    assert result.rejected_record_count is None


@pytest.mark.parametrize(
    "invalid_outcome",
    ["offers_saved", None, True, 13],
)
def test_run_pipeline_result_rejects_invalid_outcome_value(
    invalid_outcome: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="outcome must be an instance of RunPipelineOutcome",
    ):
        _make_run_pipeline_result(
            outcome=invalid_outcome,
        )


@pytest.mark.parametrize(
    "invalid_retry_after_seconds",
    [True, False, 1.5, "60"],
)
def test_run_pipeline_result_rejects_invalid_retry_after_seconds_type(
    invalid_retry_after_seconds: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="retry_after_seconds must have type int or be None",
    ):
        _make_run_pipeline_result(
            outcome=RunPipelineOutcome.RATE_LIMITED,
            retry_after_seconds=invalid_retry_after_seconds,
            source_record_count=None,
            saved_observation_count=None,
            rejected_record_count=None,
        )


def test_run_pipeline_result_rejects_negative_retry_after_seconds() -> None:
    with pytest.raises(
        ValueError,
        match="retry_after_seconds must be non-negative",
    ):
        _make_run_pipeline_result(
            outcome=RunPipelineOutcome.RATE_LIMITED,
            retry_after_seconds=-1,
            source_record_count=None,
            saved_observation_count=None,
            rejected_record_count=None,
        )


@pytest.mark.parametrize(
    "invalid_source_record_count",
    [True, False, 1.5, "10"],
)
def test_run_pipeline_result_rejects_invalid_source_record_count_type(
    invalid_source_record_count: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="source_record_count must have type int or be None",
    ):
        _make_run_pipeline_result(
            source_record_count=invalid_source_record_count,
        )


def test_run_pipeline_result_rejects_negative_source_record_count() -> None:
    with pytest.raises(
        ValueError,
        match="source_record_count must be non-negative",
    ):
        _make_run_pipeline_result(source_record_count=-1)


@pytest.mark.parametrize(
    "field_name",
    ["saved_observation_count", "rejected_record_count"],
)
@pytest.mark.parametrize("invalid_count", [True, False, 1.5, "10"])
def test_run_pipeline_result_rejects_invalid_remaining_count_types(
    field_name: str,
    invalid_count: object,
) -> None:
    with pytest.raises(
        TypeError,
        match=f"{field_name} must have type int or be None",
    ):
        _make_run_pipeline_result(**{field_name: invalid_count})


@pytest.mark.parametrize(
    "field_name",
    ["saved_observation_count", "rejected_record_count"],
)
def test_run_pipeline_result_rejects_negative_remaining_counts(
    field_name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=f"{field_name} must be non-negative",
    ):
        _make_run_pipeline_result(**{field_name: -1})


def test_run_pipeline_result_rejects_rejected_records_when_offers_saved() -> None:
    with pytest.raises(
        ValueError,
        match="offers_saved requires saved > 0 and rejected = 0",
    ):
        _make_run_pipeline_result(
            source_record_count=10,
            saved_observation_count=9,
            rejected_record_count=1,
        )


@pytest.mark.parametrize(
    "counts",
    [(1, 1, 0), (1, 0, 1)],
)
def test_run_pipeline_result_rejects_nonzero_counts_when_no_offers(
    counts: tuple[int, int, int],
) -> None:
    source_count, saved_count, rejected_count = counts
    with pytest.raises(
        ValueError,
        match="counts must be zero when outcome is no_offers",
    ):
        _make_run_pipeline_result(
            outcome=RunPipelineOutcome.NO_OFFERS,
            source_record_count=source_count,
            saved_observation_count=saved_count,
            rejected_record_count=rejected_count,
        )


@pytest.mark.parametrize(
    ("outcome", "counts"),
    [
        (RunPipelineOutcome.OFFERS_SAVED, (10, 10, 0)),
        (RunPipelineOutcome.NO_OFFERS, (0, 0, 0)),
        (RunPipelineOutcome.OFFERS_PARTIALLY_SAVED, (10, 9, 1)),
        (RunPipelineOutcome.ALL_OFFERS_REJECTED, (3, 0, 3)),
    ],
)
@pytest.mark.parametrize(
    "field_name",
    [
        "source_record_count",
        "saved_observation_count",
        "rejected_record_count",
    ],
)
def test_run_pipeline_result_requires_counts_for_completed_outcomes(
    outcome: RunPipelineOutcome,
    counts: tuple[int, int, int],
    field_name: str,
) -> None:
    record_count, saved_count, rejected_count = counts
    data = {
        "outcome": outcome,
        "retry_after_seconds": None,
        "source_record_count": record_count,
        "saved_observation_count": saved_count,
        "rejected_record_count": rejected_count,
    }

    data[field_name] = None

    with pytest.raises(
        ValueError,
        match="counts must be provided when per-record processing completed",
    ):
        RunPipelineResult(**data)


@pytest.mark.parametrize(
    "outcome",
    [
        RunPipelineOutcome.PROCESSING_FAILED,
        RunPipelineOutcome.CONNECTION_ERROR,
        RunPipelineOutcome.RATE_LIMITED,
    ],
)
@pytest.mark.parametrize(
    "field_name",
    [
        "source_record_count",
        "saved_observation_count",
        "rejected_record_count",
    ],
)
def test_run_pipeline_result_requires_none_for_uncompleted_outcomes(
    outcome: RunPipelineOutcome,
    field_name: str,
) -> None:
    data = {
        "outcome": outcome,
        "retry_after_seconds": None,
        "source_record_count": None,
        "saved_observation_count": None,
        "rejected_record_count": None,
    }
    data[field_name] = 0

    with pytest.raises(
        ValueError,
        match="counts must be None when per-record processing did not complete",
    ):
        RunPipelineResult(**data)


def test_run_pipeline_result_rejects_inconsistent_record_counts() -> None:
    with pytest.raises(
        ValueError,
        match="source_record_count must equal saved_observation_count plus rejected_record_count",
    ):
        _make_run_pipeline_result(saved_observation_count=9)


def test_run_pipeline_result_requires_saved_observations_when_offers_saved() -> None:
    with pytest.raises(
        ValueError,
        match="offers_saved requires saved > 0 and rejected = 0",
    ):
        _make_run_pipeline_result(
            source_record_count=0,
            saved_observation_count=0,
        )


@pytest.mark.parametrize(
    ("saved_count", "rejected_count"),
    [(0, 1), (1, 0)],
)
def test_run_pipeline_result_requires_saved_and_rejected_records_when_partially_saved(
    saved_count: int,
    rejected_count: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="offers_partially_saved requires saved > 0 and rejected > 0",
    ):
        _make_run_pipeline_result(
            outcome=RunPipelineOutcome.OFFERS_PARTIALLY_SAVED,
            source_record_count=1,
            saved_observation_count=saved_count,
            rejected_record_count=rejected_count,
        )


@pytest.mark.parametrize(
    ("source_count", "saved_count", "rejected_count"),
    [(2, 1, 1), (1, 1, 0), (0, 0, 0)],
)
def test_run_pipeline_result_requires_only_rejected_records_when_all_offers_rejected(
    source_count: int,
    saved_count: int,
    rejected_count: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="all_offers_rejected requires saved = 0 and rejected > 0",
    ):
        _make_run_pipeline_result(
            outcome=RunPipelineOutcome.ALL_OFFERS_REJECTED,
            source_record_count=source_count,
            saved_observation_count=saved_count,
            rejected_record_count=rejected_count,
        )


def test_run_pipeline_result_rejects_retry_delay_when_not_rate_limited() -> None:
    with pytest.raises(
        ValueError,
        match="retry_after_seconds must be None unless outcome is rate_limited",
    ):
        _make_run_pipeline_result(retry_after_seconds=30)
