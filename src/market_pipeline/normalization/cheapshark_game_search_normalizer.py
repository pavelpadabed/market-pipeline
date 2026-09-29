from market_pipeline.normalization.models import (
    NormalizedCheapSharkGameCandidate,
    NormalizedCheapSharkGameSearch,
)
from market_pipeline.validation.models import (
    CheapSharkGameSearchSuccess,
)


class CheapSharkGameSearchNormalizer:
    def normalize(
        self,
        validation: CheapSharkGameSearchSuccess,
    ) -> NormalizedCheapSharkGameSearch:
        normalized_candidates: list[NormalizedCheapSharkGameCandidate] = []

        for candidate in validation.games:
            stripped_game_id = candidate.game_id.strip()
            game_id = int(stripped_game_id)
            title = candidate.title.strip()
            normalized_candidate = NormalizedCheapSharkGameCandidate(
                game_id=game_id,
                title=title,
            )
            normalized_candidates.append(normalized_candidate)

        return NormalizedCheapSharkGameSearch(
            validation=validation,
            games=tuple(normalized_candidates),
        )
