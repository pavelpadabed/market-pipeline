import logging

from market_pipeline.acquisition.cheapshark_game_search_acquirer import (
    CheapSharkGameSearchAcquirer,
)
from market_pipeline.acquisition.models import (
    AcquisitionFailure,
    AcquisitionFailureOutcome,
)
from market_pipeline.application.models import (
    GameSearchCandidate,
    GameSearchFailure,
    GameSearchFailureOutcome,
    GameSearchResult,
    GameSearchSuccess,
)
from market_pipeline.normalization.cheapshark_game_search_normalizer import (
    CheapSharkGameSearchNormalizer,
)
from market_pipeline.validation.cheapshark_game_search_validator import (
    CheapSharkGameSearchValidator,
)
from market_pipeline.validation.models import CheapSharkGameSearchFailure


logger = logging.getLogger(__name__)


class SearchGames:
    def __init__(
        self,
        acquirer: CheapSharkGameSearchAcquirer,
        validator: CheapSharkGameSearchValidator,
        normalizer: CheapSharkGameSearchNormalizer,
    ) -> None:
        self.acquirer = acquirer
        self.validator = validator
        self.normalizer = normalizer

    def search(self, query: str) -> GameSearchResult:
        logger.info('event="game search started"')
        acquisition = self.acquirer.acquire(query)

        if isinstance(acquisition, AcquisitionFailure):
            logger.error(
                'event="game search acquisition failed" '
                "acquisition_outcome=%s "
                "diagnostic_message=%r "
                "status_code=%s "
                "retry_after_seconds=%s",
                acquisition.outcome,
                acquisition.diagnostic_message,
                acquisition.status_code,
                acquisition.retry_after_seconds,
            )
            match acquisition.outcome:
                case AcquisitionFailureOutcome.NETWORK_ERROR:
                    return GameSearchFailure(
                        outcome=GameSearchFailureOutcome.CONNECTION_FAILED,
                    )
                case AcquisitionFailureOutcome.HTTP_ERROR if (
                    acquisition.status_code == 429
                ):
                    return GameSearchFailure(
                        outcome=GameSearchFailureOutcome.RATE_LIMITED,
                        retry_after_seconds=acquisition.retry_after_seconds,
                    )
                case (
                    AcquisitionFailureOutcome.HTTP_ERROR
                    | AcquisitionFailureOutcome.TIMEOUT
                    | AcquisitionFailureOutcome.REQUEST_ERROR
                    | AcquisitionFailureOutcome.BLOCKED
                    | AcquisitionFailureOutcome.BROWSER_ERROR
                ):
                    return GameSearchFailure(
                        outcome=GameSearchFailureOutcome.SEARCH_REQUEST_FAILED,
                    )
                case AcquisitionFailureOutcome.UNEXPECTED_CONTENT:
                    return GameSearchFailure(
                        outcome=GameSearchFailureOutcome.INVALID_SOURCE_RESPONSE,
                    )
                case _:
                    raise ValueError(
                        f"unsupported acquisition failure outcome: {acquisition.outcome}"
                    )

        validation = self.validator.validate(acquisition)

        if isinstance(validation, CheapSharkGameSearchFailure):
            logger.error(
                'event="game search validation failed" '
                "diagnostic_message=%r",
                validation.diagnostic_message,
            )
            return GameSearchFailure(
                outcome=GameSearchFailureOutcome.INVALID_SOURCE_RESPONSE,
            )

        normalization = self.normalizer.normalize(validation)

        candidates: list[GameSearchCandidate] = []

        for game in normalization.games:
            candidate = GameSearchCandidate(
                game_id=game.game_id,
                title=game.title,
            )
            candidates.append(candidate)

        logger.info(
            'event="game search completed" '
            "candidate_count=%s",
            len(candidates),
        )

        return GameSearchSuccess(candidates=tuple(candidates))
