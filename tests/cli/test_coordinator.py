from pathlib import Path
from typing import Never

import pytest

from market_pipeline.application.models import (
    GameSearchCandidate,
    GameSearchFailure,
    GameSearchFailureOutcome,
    GameSearchResult,
    GameSearchSuccess,
    LatestOffersReportOutcome,
    LatestOffersReportResult,
    RunPipelineOutcome,
    RunPipelineResult,
)
from market_pipeline.cli.coordinator import CliCoordinator


VALID_ARGS = ["--query", "The Witcher 3"]
VALID_QUERY = "The Witcher 3"


class FakeSearchGames:
    def __init__(self, result: GameSearchResult) -> None:
        self.result = result

    def search(self, query: str) -> GameSearchResult:
        self.called_query = query
        return self.result


class FakeRunPipeline:
    def __init__(self, result: RunPipelineResult) -> None:
        self.result = result
        self.called_game_id: int | None = None

    def execute(self, game_id: int) -> RunPipelineResult:
        self.called_game_id = game_id
        return self.result


class UnexpectedCallRunPipeline:
    def execute(self, game_id: int) -> Never:
        raise AssertionError("run pipeline must not be called")


class FakeLatestOffersReportGenerator:
    def __init__(self, result: LatestOffersReportResult) -> None:
        self.result = result
        self.called_external_product_id: int | None = None
        self.called_path: Path | None = None

    def execute(
        self,
        external_product_id: int,
        path: Path,
    ) -> LatestOffersReportResult:
        self.called_external_product_id = external_product_id
        self.called_path = path
        return self.result


class UnexpectedCallLatestOffersReportGenerator:
    def execute(
        self,
        external_product_id: int,
        path: Path,
    ) -> Never:
        raise AssertionError("latest offers report generator must not be called")


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


def _make_report_saved_result() -> LatestOffersReportResult:
    return LatestOffersReportResult(
        outcome=LatestOffersReportOutcome.REPORT_SAVED,
        exported_offer_count=1,
    )


def _make_run_pipeline_failure_result(
    outcome: RunPipelineOutcome,
    retry_after_seconds: int | None = None,
) -> RunPipelineResult:
    return RunPipelineResult(
        outcome=outcome,
        retry_after_seconds=retry_after_seconds,
        source_record_count=None,
        saved_observation_count=None,
        rejected_record_count=None,
    )


def fake_selection_input(_prompt: str) -> str:
    return "2"


def test_select_game_returns_selected_game_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game_search_result = _make_game_search_success()

    fake_search = FakeSearchGames(game_search_result)

    monkeypatch.setattr("builtins.input", fake_selection_input)

    coordinator = CliCoordinator(
        fake_search,
        UnexpectedCallRunPipeline(),
        UnexpectedCallLatestOffersReportGenerator(),
    )

    result = coordinator.select_game(VALID_QUERY)

    assert result == 42
    assert fake_search.called_query == "The Witcher 3"


def test_run_searches_with_normalized_query() -> None:
    game_search_failure = GameSearchFailure(
        outcome=GameSearchFailureOutcome.CONNECTION_FAILED,
    )
    fake_search = FakeSearchGames(game_search_failure)
    coordinator = CliCoordinator(
        fake_search,
        UnexpectedCallRunPipeline(),
        UnexpectedCallLatestOffersReportGenerator(),
    )

    coordinator.run(["--query", " The Witcher 3 "])

    assert fake_search.called_query == "The Witcher 3"


def test_run_displays_search_failure_message_without_executing_pipeline(
    capsys: pytest.CaptureFixture[str],
) -> None:
    game_search_failure = GameSearchFailure(
        outcome=GameSearchFailureOutcome.CONNECTION_FAILED,
    )

    fake_search = FakeSearchGames(game_search_failure)

    run_pipeline = UnexpectedCallRunPipeline()

    coordinator = CliCoordinator(
        fake_search,
        run_pipeline,
        UnexpectedCallLatestOffersReportGenerator(),
    )

    coordinator.run(VALID_ARGS)

    expected_message = (
        "Could not connect to the game search service. "
        "Check your internet connection and try again."
    )
    expected_output = f"{expected_message}\n"

    captured = capsys.readouterr()

    assert captured.out == expected_output


def test_run_displays_no_games_message_without_executing_pipeline(
    capsys: pytest.CaptureFixture[str],
) -> None:
    search_result = _make_game_search_success(
        candidates=(),
    )

    fake_search = FakeSearchGames(search_result)

    run_pipeline = UnexpectedCallRunPipeline()

    coordinator = CliCoordinator(
        fake_search,
        run_pipeline,
        UnexpectedCallLatestOffersReportGenerator(),
    )

    coordinator.run(VALID_ARGS)

    expected_message = "No games found for your query."

    expected_output = f"{expected_message}\n"

    captured = capsys.readouterr()

    assert captured.out == expected_output


@pytest.mark.parametrize(
    "raw_input",
    ["q", " Q "],
)
def test_run_does_not_execute_pipeline_when_user_quits(
    monkeypatch: pytest.MonkeyPatch,
    raw_input: str,
) -> None:
    search_result = _make_game_search_success()

    fake_search = FakeSearchGames(search_result)

    def fake_quit_input(_prompt: str) -> str:
        return raw_input

    monkeypatch.setattr("builtins.input", fake_quit_input)

    coordinator = CliCoordinator(
        fake_search,
        UnexpectedCallRunPipeline(),
        UnexpectedCallLatestOffersReportGenerator(),
    )

    coordinator.run(VALID_ARGS)


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

    coordinator = CliCoordinator(
        fake_search,
        UnexpectedCallRunPipeline(),
        UnexpectedCallLatestOffersReportGenerator(),
    )

    result = coordinator.select_game(VALID_QUERY)

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

    coordinator = CliCoordinator(
        fake_search,
        UnexpectedCallRunPipeline(),
        UnexpectedCallLatestOffersReportGenerator(),
    )

    result = coordinator.select_game(VALID_QUERY)

    expected_retry_prompt = (
        "Invalid selection. Enter a listed game number or 'q' to quit: "
    )

    assert result == 42
    assert received_prompts[1] == expected_retry_prompt


def test_run_executes_pipeline_for_selected_game(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    search_result = _make_game_search_success()
    fake_search = FakeSearchGames(search_result)
    monkeypatch.setattr("builtins.input", fake_selection_input)

    run_pipeline_result = RunPipelineResult(
        outcome=RunPipelineOutcome.OFFERS_SAVED,
        retry_after_seconds=None,
        source_record_count=1,
        saved_observation_count=1,
        rejected_record_count=0,
    )
    fake_run_pipeline = FakeRunPipeline(run_pipeline_result)
    fake_report_generator = FakeLatestOffersReportGenerator(
        _make_report_saved_result()
    )

    coordinator = CliCoordinator(
        fake_search,
        fake_run_pipeline,
        fake_report_generator,
    )
    coordinator.run(VALID_ARGS)

    assert fake_run_pipeline.called_game_id == 42


@pytest.mark.parametrize(
    "run_pipeline_result",
    [
        RunPipelineResult(
            outcome=RunPipelineOutcome.OFFERS_SAVED,
            retry_after_seconds=None,
            source_record_count=1,
            saved_observation_count=1,
            rejected_record_count=0,
        ),
        RunPipelineResult(
            outcome=RunPipelineOutcome.OFFERS_PARTIALLY_SAVED,
            retry_after_seconds=None,
            source_record_count=2,
            saved_observation_count=1,
            rejected_record_count=1,
        ),
    ],
)
def test_run_generates_latest_offers_report_when_pipeline_saves_offers(
    monkeypatch: pytest.MonkeyPatch,
    run_pipeline_result: RunPipelineResult,
) -> None:
    search_result = _make_game_search_success()
    fake_search = FakeSearchGames(search_result)
    monkeypatch.setattr("builtins.input", fake_selection_input)

    fake_run_pipeline = FakeRunPipeline(run_pipeline_result)
    fake_report_generator = FakeLatestOffersReportGenerator(
        _make_report_saved_result()
    )

    coordinator = CliCoordinator(
        fake_search,
        fake_run_pipeline,
        fake_report_generator,
    )

    coordinator.run(VALID_ARGS)

    assert fake_report_generator.called_external_product_id == 42
    assert fake_report_generator.called_path == Path(
        "outputs/latest_offers_42.xlsx"
    )


@pytest.mark.parametrize(
    "run_pipeline_result",
    [
        _make_run_pipeline_failure_result(
            outcome=RunPipelineOutcome.PROCESSING_FAILED,
        ),
        _make_run_pipeline_failure_result(
            outcome=RunPipelineOutcome.CONNECTION_ERROR,
        ),
        _make_run_pipeline_failure_result(
            outcome=RunPipelineOutcome.RATE_LIMITED,
            retry_after_seconds=30,
        ),
        RunPipelineResult(
            outcome=RunPipelineOutcome.NO_OFFERS,
            retry_after_seconds=None,
            source_record_count=0,
            saved_observation_count=0,
            rejected_record_count=0,
        ),
        RunPipelineResult(
            outcome=RunPipelineOutcome.ALL_OFFERS_REJECTED,
            retry_after_seconds=None,
            source_record_count=1,
            saved_observation_count=0,
            rejected_record_count=1,
        ),
    ],
)
def test_run_does_not_generate_latest_offers_report_when_pipeline_does_not_save_offers(
    monkeypatch: pytest.MonkeyPatch,
    run_pipeline_result: RunPipelineResult,
) -> None:
    search_result = _make_game_search_success()
    fake_search = FakeSearchGames(search_result)
    monkeypatch.setattr("builtins.input", fake_selection_input)

    fake_run_pipeline = FakeRunPipeline(run_pipeline_result)

    coordinator = CliCoordinator(
        fake_search,
        fake_run_pipeline,
        UnexpectedCallLatestOffersReportGenerator(),
    )

    coordinator.run(VALID_ARGS)


def test_run_displays_pipeline_result_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    search_result = _make_game_search_success()
    fake_search = FakeSearchGames(search_result)
    monkeypatch.setattr("builtins.input", fake_selection_input)

    run_pipeline_result = RunPipelineResult(
        outcome=RunPipelineOutcome.NO_OFFERS,
        retry_after_seconds=None,
        source_record_count=0,
        saved_observation_count=0,
        rejected_record_count=0,
    )
    fake_run_pipeline = FakeRunPipeline(run_pipeline_result)

    coordinator = CliCoordinator(
        fake_search,
        fake_run_pipeline,
        UnexpectedCallLatestOffersReportGenerator(),
    )
    coordinator.run(VALID_ARGS)

    expected_message = "Pipeline completed successfully. No offers found."

    expected_output = f"{expected_message}\n"

    captured = capsys.readouterr()

    assert captured.out == expected_output


def test_run_displays_latest_offers_report_result_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    search_result = _make_game_search_success()
    fake_search = FakeSearchGames(search_result)
    monkeypatch.setattr("builtins.input", fake_selection_input)

    run_pipeline_result = RunPipelineResult(
        outcome=RunPipelineOutcome.OFFERS_SAVED,
        retry_after_seconds=None,
        source_record_count=1,
        saved_observation_count=1,
        rejected_record_count=0,
    )
    fake_run_pipeline = FakeRunPipeline(run_pipeline_result)
    fake_report_generator = FakeLatestOffersReportGenerator(
        _make_report_saved_result()
    )

    coordinator = CliCoordinator(
        fake_search,
        fake_run_pipeline,
        fake_report_generator,
    )
    coordinator.run(VALID_ARGS)

    expected_message = (
        "Pipeline completed successfully:\n"
        "\n"
        "Offers found: 1\n"
        "Offers saved: 1\n"
        "\n"
        "Report saved successfully.\n"
        "\n"
        "Exported offers: 1"
    )
    expected_output = f"{expected_message}\n"

    captured = capsys.readouterr()

    assert captured.out == expected_output


def test_run_passes_user_provided_output_directory_to_report_generator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    search_result = _make_game_search_success()
    fake_search = FakeSearchGames(search_result)
    monkeypatch.setattr("builtins.input", fake_selection_input)

    run_pipeline_result = RunPipelineResult(
        outcome=RunPipelineOutcome.OFFERS_SAVED,
        retry_after_seconds=None,
        source_record_count=1,
        saved_observation_count=1,
        rejected_record_count=0,
    )
    fake_run_pipeline = FakeRunPipeline(run_pipeline_result)
    fake_report_generator = FakeLatestOffersReportGenerator(
        _make_report_saved_result()
    )

    coordinator = CliCoordinator(
        fake_search,
        fake_run_pipeline,
        fake_report_generator,
    )
    custom_path_args = [
        "--query",
        "The Witcher 3",
        "--output-dir",
        "reports/custom",
    ]
    coordinator.run(custom_path_args)

    assert fake_report_generator.called_path == Path(
        "reports/custom/latest_offers_42.xlsx"
    )
