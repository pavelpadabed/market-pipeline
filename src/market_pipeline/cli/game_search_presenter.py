from market_pipeline.application.models import (
    GameSearchCandidate,
    GameSearchFailure,
    GameSearchFailureOutcome,
)


def format_game_selection(
    candidates: tuple[GameSearchCandidate, ...],
) -> str:
    lines: list[str] = [
        "Games matching your query:",
        "",
    ]
    for index, candidate in enumerate(candidates, start=1):
        lines.append(f"{index}. {candidate.title}")

    lines.extend([
        "",
        "Select a game number or 'q' to quit: ",
    ])

    return "\n".join(lines)


def format_no_games_found() -> str:
    return "No games found for your query."


def format_game_search_failure(failure: GameSearchFailure) -> str:
    match failure.outcome:
        case GameSearchFailureOutcome.CONNECTION_FAILED:
            return (
                "Could not connect to the game search service. "
                "Check your internet connection and try again."
            )
        case GameSearchFailureOutcome.RATE_LIMITED:
            retry_after_seconds = failure.retry_after_seconds

            if retry_after_seconds is None:
                return (
                    "The game search service is receiving too many requests. "
                    "Please try again later."
                )
            if retry_after_seconds == 0:
                return (
                    "The game search service is receiving too many requests. "
                    "You can try again now."
                )
            if retry_after_seconds == 1:
                return (
                    "The game search service is receiving too many requests. "
                    "Please try again in 1 second."
                )

            return (
                "The game search service is receiving too many requests. "
                f"Please try again in {retry_after_seconds} seconds."
            )
        case (
            GameSearchFailureOutcome.SEARCH_REQUEST_FAILED
            | GameSearchFailureOutcome.INVALID_SOURCE_RESPONSE
        ):
            return (
                "Could not complete the game search. "
                "Please try again later."
            )
        case _:
            raise ValueError(
                f"unsupported game search failure outcome: {failure.outcome}"
            )


def format_invalid_game_selection() -> str:
    return (
        "Invalid selection. Enter a listed game number or 'q' to quit: "
    )
