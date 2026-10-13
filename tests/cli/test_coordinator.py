import pytest

from market_pipeline.application.models import (
    GameSearchCandidate,
    GameSearchFailure,
    GameSearchFailureOutcome,
    GameSearchResult,
    GameSearchSuccess,
)
from market_pipeline.cli.coordinator import CliCoordinator


VALID_ARGS = ["--query", "The Witcher 3"]


class FakeSearchGames:
    def __init__(self, result: GameSearchResult) -> None:
        self.result = result

    def search(self, query: str) -> GameSearchResult:
        self.called_query = query
        return self.result


def _make_game_search_success(
    **overrides: tuple[GameSearchCandidate, ...],
) -> GameSearchSuccess:
    data = {
        "candidates": (
            GameSearchCandidate(
                game_id=13,
                title="The Witcher 3: Wild Hunt",
            ),
            GameSearchCandidate(
                game_id=42,
                title="The Witcher 3: Wild Hunt - Remastered",
            ),
        ),
    }
    data.update(overrides)
    return GameSearchSuccess(**data)


def fake_selection_input(_prompt: str) -> str:
    return "2"


def test_select_game_returns_selected_game_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game_search_result = _make_game_search_success()

    fake_search = FakeSearchGames(game_search_result)

    monkeypatch.setattr("builtins.input", fake_selection_input)

    coordinator = CliCoordinator(fake_search)

    result = coordinator.select_game(VALID_ARGS)

    assert result == 42
    assert fake_search.called_query == "The Witcher 3"


def test_select_game_displays_failure_message_and_returns_none(
    capsys: pytest.CaptureFixture[str],
) -> None:
    game_search_failure = GameSearchFailure(
        outcome=GameSearchFailureOutcome.CONNECTION_FAILED,
    )

    fake_search = FakeSearchGames(game_search_failure)

    coordinator = CliCoordinator(fake_search)

    result = coordinator.select_game(VALID_ARGS)

    expected_message = (
        "Could not connect to the game search service. "
        "Check your internet connection and try again."
    )
    expected_output = f"{expected_message}\n"

    captured = capsys.readouterr()

    assert result is None
    assert captured.out == expected_output


def test_select_game_displays_no_games_message_and_returns_none(
    capsys: pytest.CaptureFixture[str],
) -> None:
    search_result = _make_game_search_success(
        candidates=(),
    )

    fake_search = FakeSearchGames(search_result)

    coordinator = CliCoordinator(fake_search)

    result = coordinator.select_game(VALID_ARGS)

    expected_message = "No games found for your query."

    expected_output = f"{expected_message}\n"

    captured = capsys.readouterr()

    assert result is None
    assert captured.out == expected_output


@pytest.mark.parametrize(
    "raw_input",
    ["q", " Q "],
)
def test_select_game_returns_none_when_user_quits(
    monkeypatch: pytest.MonkeyPatch,
    raw_input: str,
) -> None:
    search_result = _make_game_search_success()

    fake_search = FakeSearchGames(search_result)

    def fake_quit_input(_prompt: str) -> str:
        return raw_input

    monkeypatch.setattr("builtins.input", fake_quit_input)

    coordinator = CliCoordinator(fake_search)

    result = coordinator.select_game(VALID_ARGS)

    assert result is None


@pytest.mark.parametrize(
    "invalid_input",
    ["abc", "1.5", "   "],
)
def test_select_game_retries_after_non_integer_input(
    monkeypatch: pytest.MonkeyPatch,
    invalid_input: str,
) -> None:
    search_result = _make_game_search_success()

    fake_search = FakeSearchGames(search_result)

    responses = iter([invalid_input, "2"])
    received_prompts: list[str] = []

    def fake_input(prompt: str) -> str:
        received_prompts.append(prompt)
        return next(responses)

    monkeypatch.setattr("builtins.input", fake_input)

    coordinator = CliCoordinator(fake_search)

    result = coordinator.select_game(VALID_ARGS)

    expected_retry_prompt = (
        "Invalid selection. Enter a listed game number or 'q' to quit: "
    )

    assert result == 42
    assert received_prompts[1] == expected_retry_prompt


@pytest.mark.parametrize(
    "out_of_range_input",
    ["0", "-1", "3"],
)
def test_select_game_retries_after_out_of_range_selection(
    monkeypatch: pytest.MonkeyPatch,
    out_of_range_input: str,
) -> None:
    search_result = _make_game_search_success()

    fake_search = FakeSearchGames(search_result)

    responses = iter([out_of_range_input, "2"])
    received_prompts: list[str] = []

    def fake_input(prompt: str) -> str:
        received_prompts.append(prompt)
        return next(responses)

    monkeypatch.setattr("builtins.input", fake_input)

    coordinator = CliCoordinator(fake_search)

    result = coordinator.select_game(VALID_ARGS)

    expected_retry_prompt = (
        "Invalid selection. Enter a listed game number or 'q' to quit: "
    )

    assert result == 42
    assert received_prompts[1] == expected_retry_prompt
