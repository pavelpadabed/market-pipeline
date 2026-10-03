import pytest

from market_pipeline.application.models import (
    GameSearchFailure,
    GameSearchFailureOutcome,
)


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
