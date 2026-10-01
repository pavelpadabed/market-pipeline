from datetime import datetime
from zoneinfo import ZoneInfo

from market_pipeline.acquisition.models import (
    AcquisitionMethod,
    AcquisitionSuccess,
)
from market_pipeline.normalization.cheapshark_game_search_normalizer import (
    CheapSharkGameSearchNormalizer,
)
from market_pipeline.normalization.models import (
    NormalizedCheapSharkGameCandidate,
    NormalizedCheapSharkGameSearch,
)
from market_pipeline.validation.models import (
    CheapSharkGameCandidate,
    CheapSharkGameSearchSuccess,
)

WARSAW = ZoneInfo("Europe/Warsaw")


def _make_acquisition_success(**overrides: object) -> AcquisitionSuccess:
    data = {
        "requested_url": "https://www.cheapshark.com/api/1.0/games?title=Batman",
        "method": AcquisitionMethod.HTTP,
        "started_at": datetime(
            2026, 9, 28, 12, 15, tzinfo=WARSAW,
        ),
        "finished_at": datetime(
            2026, 9, 28, 12, 16, tzinfo=WARSAW,
        ),
        "final_url": "https://www.cheapshark.com/api/1.0/games?title=Batman",
        "status_code": 200,
        "content_type": "application/json",
        "content": '[{"gameID": " 1 ", "external": " Batman "}]',
    }
    data.update(overrides)
    return AcquisitionSuccess(**data)


def test_cheapshark_game_search_normalizer_normalizes_candidate_and_preserves_validation(
) -> None:
    acquisition = _make_acquisition_success()
    source_mapping = {
        "gameID": " 1 ",
        "external": " Batman ",
    }
    candidate = CheapSharkGameCandidate.model_validate(source_mapping)

    validation = CheapSharkGameSearchSuccess(
        acquisition=acquisition,
        games=(candidate,),
    )

    normalizer = CheapSharkGameSearchNormalizer()

    result = normalizer.normalize(validation)

    assert isinstance(result, NormalizedCheapSharkGameSearch)
    assert result.validation is validation
    normalized_candidate, = result.games
    assert isinstance(normalized_candidate, NormalizedCheapSharkGameCandidate)
    assert normalized_candidate.game_id == 1
    assert normalized_candidate.title == "Batman"


def test_cheapshark_game_search_normalizer_preserves_candidate_source_order() -> None:
    content = (
        "["
        '{"gameID": "2", "external": "LEGO Batman"},'
        '{"gameID": "1", "external": "Batman"}'
        "]"
    )
    acquisition = _make_acquisition_success(
        content=content,
    )

    batman_source_mapping = {"gameID": "1", "external": "Batman"}
    lego_batman_source_mapping = {
        "gameID": "2",
        "external": "LEGO Batman",
    }

    batman_candidate = CheapSharkGameCandidate.model_validate(
        batman_source_mapping,
    )
    lego_batman_candidate = CheapSharkGameCandidate.model_validate(
        lego_batman_source_mapping,
    )

    validation = CheapSharkGameSearchSuccess(
        acquisition=acquisition,
        games=(lego_batman_candidate, batman_candidate),
    )

    normalizer = CheapSharkGameSearchNormalizer()

    result = normalizer.normalize(validation)

    assert isinstance(result, NormalizedCheapSharkGameSearch)
    assert result.validation is validation
    normalized_lego_batman, normalized_batman = result.games
    assert isinstance(normalized_lego_batman, NormalizedCheapSharkGameCandidate)
    assert normalized_lego_batman.game_id == 2
    assert normalized_lego_batman.title == "LEGO Batman"
    assert isinstance(normalized_batman, NormalizedCheapSharkGameCandidate)
    assert normalized_batman.game_id == 1
    assert normalized_batman.title == "Batman"


def test_cheapshark_game_search_normalizer_preserves_empty_search_result() -> None:
    acquisition = _make_acquisition_success(content="[]")
    validation = CheapSharkGameSearchSuccess(
        acquisition=acquisition,
        games=(),
    )

    normalizer = CheapSharkGameSearchNormalizer()

    result = normalizer.normalize(validation)

    assert isinstance(result, NormalizedCheapSharkGameSearch)
    assert result.validation is validation
    assert result.games == ()
