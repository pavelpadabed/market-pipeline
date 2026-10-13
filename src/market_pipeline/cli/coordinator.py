from market_pipeline.application.models import GameSearchFailure
from market_pipeline.application.search_games import SearchGames
from market_pipeline.cli.argument_parser import parse_query
from market_pipeline.cli.console import (
    display_message,
    prompt_user,
)
from market_pipeline.cli.presenter import (
    format_game_search_failure,
    format_game_selection,
    format_invalid_game_selection,
    format_no_games_found,
)


class CliCoordinator:
    def __init__(self, searcher: SearchGames) -> None:
        self.searcher = searcher

    def select_game(self, args: list[str]) -> int | None:
        query = parse_query(args)

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
