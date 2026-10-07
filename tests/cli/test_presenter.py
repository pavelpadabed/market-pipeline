import pytest

from market_pipeline.application.models import (
    GameSearchCandidate,
    GameSearchFailure,
    GameSearchFailureOutcome,
)
from market_pipeline.cli.presenter import (
    format_game_search_failure,
    format_game_selection,
    format_invalid_game_selection,
    format_no_games_found,
)


def test_format_game_selection_returns_numbered_candidates() -> None:
    candidates = (
        GameSearchCandidate(
            game_id=1,
            title="The Witcher",
        ),
        GameSearchCandidate(
            game_id=2,
            title="The Witcher 3",
        ),
    )

    expected = (
        "Games matching your query:\n"
        "\n"
        "1. The Witcher\n"
        "2. The Witcher 3\n"
        "\n"
        "Select a game number or 'q' to quit: "
    )

    actual = format_game_selection(candidates)

    assert actual == expected


def test_format_no_games_found_returns_message() -> None:
    expected = "No games found for your query."
    actual = format_no_games_found()

    assert actual == expected


def test_format_game_search_failure_returns_connection_message() -> None:
    failure = GameSearchFailure(
        outcome=GameSearchFailureOutcome.CONNECTION_FAILED,
    )

    expected = (
        "Could not connect to the game search service. "
        "Check your internet connection and try again."
    )

    actual = format_game_search_failure(failure)

    assert actual == expected


def test_format_game_search_failure_returns_rate_limited_message_when_retry_delay_is_unknown(
) -> None:
    failure = GameSearchFailure(
        outcome=GameSearchFailureOutcome.RATE_LIMITED,
    )

    expected = (
        "The game search service is receiving too many requests. "
        "Please try again later."
    )

    actual = format_game_search_failure(failure)

    assert actual == expected


def test_format_game_search_failure_returns_rate_limited_message_when_retry_delay_is_zero(
) -> None:
    failure = GameSearchFailure(
        outcome=GameSearchFailureOutcome.RATE_LIMITED,
        retry_after_seconds=0,
    )

    expected = (
        "The game search service is receiving too many requests. "
        "You can try again now."
    )

    actual = format_game_search_failure(failure)

    assert actual == expected


def test_format_game_search_failure_returns_rate_limited_message_when_retry_delay_is_one_second(
) -> None:
    failure = GameSearchFailure(
        outcome=GameSearchFailureOutcome.RATE_LIMITED,
        retry_after_seconds=1,
    )

    expected = (
        "The game search service is receiving too many requests. "
        "Please try again in 1 second."
    )

    actual = format_game_search_failure(failure)

    assert actual == expected


def test_format_game_search_failure_returns_rate_limited_message_when_retry_delay_is_multiple_seconds(
) -> None:
    failure = GameSearchFailure(
        outcome=GameSearchFailureOutcome.RATE_LIMITED,
        retry_after_seconds=30,
    )

    expected = (
        "The game search service is receiving too many requests. "
        "Please try again in 30 seconds."
    )

    actual = format_game_search_failure(failure)

    assert actual == expected


@pytest.mark.parametrize(
    "outcome",
    [
        GameSearchFailureOutcome.SEARCH_REQUEST_FAILED,
        GameSearchFailureOutcome.INVALID_SOURCE_RESPONSE,
    ],
)
def test_format_game_search_failure_returns_generic_message(
    outcome: GameSearchFailureOutcome,
) -> None:
    failure = GameSearchFailure(
        outcome=outcome,
    )

    expected = (
        "Could not complete the game search. Please try again later."
    )

    actual = format_game_search_failure(failure)

    assert actual == expected


def test_format_invalid_game_selection_returns_retry_message() -> None:
    expected = "Invalid selection. Enter a listed game number or 'q' to quit: "

    actual = format_invalid_game_selection()

    assert actual == expected
