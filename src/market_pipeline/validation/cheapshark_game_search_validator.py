from pydantic import TypeAdapter, ValidationError

from market_pipeline.acquisition.models import AcquisitionSuccess
from market_pipeline.validation.error_formatting import _format_validation_error
from market_pipeline.validation.models import (
    CheapSharkGameCandidate,
    CheapSharkGameSearchFailure,
    CheapSharkGameSearchResult,
    CheapSharkGameSearchSuccess,
)

_GAME_SEARCH_ADAPTER = TypeAdapter(tuple[CheapSharkGameCandidate, ...])


class CheapSharkGameSearchValidator:
    def validate(
        self,
        acquisition: AcquisitionSuccess,
    ) -> CheapSharkGameSearchResult:
        content = acquisition.content

        try:
            games = _GAME_SEARCH_ADAPTER.validate_json(content)
        except ValidationError as exc:
            diagnostic_message = _format_validation_error(exc)
            return CheapSharkGameSearchFailure(
                acquisition=acquisition,
                diagnostic_message=diagnostic_message,
            )

        return CheapSharkGameSearchSuccess(
            acquisition=acquisition,
            games=games,
        )
