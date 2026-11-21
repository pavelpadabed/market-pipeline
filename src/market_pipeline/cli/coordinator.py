from market_pipeline.application.latest_offers_report import (
    GenerateCheapSharkLatestOffersReport,
)
from market_pipeline.application.models import GameSearchFailure, RunPipelineOutcome
from market_pipeline.application.run_pipeline import RunPipeline
from market_pipeline.application.search_games import SearchGames
from market_pipeline.cli.argument_parser import parse_cli_arguments
from market_pipeline.cli.console import (
    display_message,
    prompt_user,
)
from market_pipeline.cli.game_search_presenter import (
    format_game_search_failure,
    format_game_selection,
    format_invalid_game_selection,
    format_no_games_found,
)
from market_pipeline.cli.latest_offers_report_presenter import (
    format_latest_offers_report,
)
from market_pipeline.cli.run_pipeline_presenter import format_run_pipeline_result


class CliCoordinator:
    def __init__(
        self,
        searcher: SearchGames,
        run_pipeline: RunPipeline,
        report_generator: GenerateCheapSharkLatestOffersReport,
    ) -> None:
        self.searcher = searcher
        self.run_pipeline = run_pipeline
        self.report_generator = report_generator

    def run(self, args: list[str]) -> None:
        cli_arguments = parse_cli_arguments(args)
        query = cli_arguments.query
        game_id = self.select_game(query)
        if game_id is None:
            return
        pipeline_result = self.run_pipeline.execute(game_id)
        pipeline_message = format_run_pipeline_result(pipeline_result)
        display_message(pipeline_message)
        match pipeline_result.outcome:
            case (
                RunPipelineOutcome.OFFERS_SAVED
                | RunPipelineOutcome.OFFERS_PARTIALLY_SAVED
            ):
                report_filename = f"latest_offers_{game_id}.xlsx"
                report_path = cli_arguments.output_dir / report_filename
                report_result = self.report_generator.execute(game_id, report_path)
                report_message = format_latest_offers_report(report_result)
                display_message("")
                display_message(report_message)
            case (
                RunPipelineOutcome.NO_OFFERS
                | RunPipelineOutcome.ALL_OFFERS_REJECTED
                | RunPipelineOutcome.PROCESSING_FAILED
                | RunPipelineOutcome.CONNECTION_ERROR
                | RunPipelineOutcome.RATE_LIMITED
            ):
                return
            case _:
                raise ValueError(
                    f"unsupported run pipeline outcome: {pipeline_result.outcome}"
                )

    def select_game(self, query: str) -> int | None:
        search_result = self.searcher.search(query)

        if isinstance(search_result, GameSearchFailure):
            failure_message = format_game_search_failure(search_result)
            display_message(failure_message)
            return None

        candidates = search_result.candidates

        if not candidates:
            message = format_no_games_found()
            display_message(message)
            return None

        message = format_game_selection(candidates)

        while True:
            raw_selection = prompt_user(message)
            selection = raw_selection.strip().lower()

            if selection == "q":
                return None
            try:
                selection_number = int(selection)
            except ValueError:
                message = format_invalid_game_selection()
                continue
            if not 1 <= selection_number <= len(candidates):
                message = format_invalid_game_selection()
                continue
            break

        selected_candidate = candidates[selection_number - 1]

        game_id = selected_candidate.game_id

        return game_id
