from datetime import datetime
from zoneinfo import ZoneInfo

from market_pipeline.acquisition.models import (
    AcquisitionMethod,
    AcquisitionSuccess,
)
from market_pipeline.validation.cheapshark_game_search_validator import (
    CheapSharkGameSearchValidator,
)
from market_pipeline.validation.models import (
    CheapSharkGameCandidate,
    CheapSharkGameSearchFailure,
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
        "content": '[{"gameID": "1", "external": "Batman"}]',
    }
    data.update(overrides)
    return AcquisitionSuccess(**data)


def test_game_search_validator_returns_success_for_valid_search_results() -> None:
    acquisition = _make_acquisition_success()

    validator = CheapSharkGameSearchValidator()

    result = validator.validate(acquisition)

    assert isinstance(result, CheapSharkGameSearchSuccess)
    assert result.acquisition is acquisition
    game_candidate, = result.games
    assert isinstance(game_candidate, CheapSharkGameCandidate)
    assert game_candidate.game_id == "1"
    assert game_candidate.title == "Batman"


def test_game_search_validator_returns_failure_when_any_candidate_is_invalid() -> None:
    acquisition = _make_acquisition_success(
        content=(
            '['
            '{"gameID": "1", "external": "Batman"},'
            '{"gameID": "abc", "external": "LEGO Batman"}'
            ']'
        ),
    )

    validator = CheapSharkGameSearchValidator()

    result = validator.validate(acquisition)

    assert isinstance(result, CheapSharkGameSearchFailure)
    assert result.acquisition is acquisition
    assert result.diagnostic_message == (
        "1.gameID: Value error, game_id must contain only ASCII decimal digits"
    )


def test_game_search_validator_returns_failure_for_malformed_json() -> None:
    malformed_content = (
        '['
        '{"gameID": "1", "external": "Batman"}'
    )

    acquisition = _make_acquisition_success(
        content=malformed_content,
    )

    validator = CheapSharkGameSearchValidator()

    result = validator.validate(acquisition)

    expected_message = "Invalid JSON: EOF while parsing a list at line 1 column 38"

    assert isinstance(result, CheapSharkGameSearchFailure)
    assert result.acquisition is acquisition
    assert result.diagnostic_message == expected_message


def test_game_search_validator_returns_failure_when_json_root_is_not_array() -> None:
    unexpected_content = (
        '{'
        '"gameID": "1",'
        '"external": "Batman"'
        '}'
    )
    acquisition = _make_acquisition_success(
        content=unexpected_content,
    )

    validator = CheapSharkGameSearchValidator()

    result = validator.validate(acquisition)

    expected_message = "Input should be a valid array"

    assert isinstance(result, CheapSharkGameSearchFailure)
    assert result.acquisition is acquisition
    assert result.diagnostic_message == expected_message


def test_game_search_validator_returns_success_for_empty_search_results() -> None:
    acquisition = _make_acquisition_success(
        content="[]",
    )

    validator = CheapSharkGameSearchValidator()

    result = validator.validate(acquisition)

    assert isinstance(result, CheapSharkGameSearchSuccess)
    assert result.acquisition is acquisition
    assert result.games == ()
