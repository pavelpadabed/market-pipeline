from datetime import datetime
from typing import Never
from zoneinfo import ZoneInfo

import pytest

from market_pipeline.acquisition.models import (
    AcquisitionFailure,
    AcquisitionFailureOutcome,
    AcquisitionMethod,
    AcquisitionResult,
    AcquisitionSuccess,
)
from market_pipeline.application.models import (
    GameSearchCandidate,
    GameSearchFailure,
    GameSearchFailureOutcome,
    GameSearchSuccess,
)
from market_pipeline.application.search_games import SearchGames
from market_pipeline.normalization.models import (
    NormalizedCheapSharkGameCandidate,
    NormalizedCheapSharkGameSearch,
)
from market_pipeline.validation.models import (
    CheapSharkGameCandidate,
    CheapSharkGameSearchFailure,
    CheapSharkGameSearchResult,
    CheapSharkGameSearchSuccess,
)

WARSAW = ZoneInfo("Europe/Warsaw")
QUERY = "Batman"
FINAL_URL = "https://www.cheapshark.com/api/1.0/games?title=Batman"
CONTENT_TYPE = "application/json"


def _make_acquisition_success(**overrides: object) -> AcquisitionSuccess:
    data = {
        "requested_url": "https://www.cheapshark.com/api/1.0/games?title=Batman",
        "method": AcquisitionMethod.HTTP,
        "started_at": datetime(
            2026, 10, 1, 10, 13, tzinfo=WARSAW,
        ),
        "finished_at": datetime(
            2026, 10, 1, 10, 14, tzinfo=WARSAW,
        ),
        "final_url": "https://www.cheapshark.com/api/1.0/games?title=Batman",
        "status_code": 200,
        "content_type": "application/json",
        "content": (
            '['
            '{"gameID": "2", "external": "LEGO Batman"},'
            '{"gameID": "1", "external": "Batman"}'
            ']'
        ),
    }
    data.update(overrides)
    return AcquisitionSuccess(**data)


def _make_acquisition_failure(
    final_url: str | None,
    status_code: int | None,
    content_type: str | None,
    retry_after_seconds: int | None = None,
    **overrides: object,
) -> AcquisitionFailure:
    data = {
        "requested_url": "https://www.cheapshark.com/api/1.0/games?title=Batman",
        "method": AcquisitionMethod.HTTP,
        "started_at": datetime(
            2026, 10, 1, 10, 13, tzinfo=WARSAW,
        ),
        "finished_at": datetime(
            2026, 10, 1, 10, 14, tzinfo=WARSAW,
        ),
        "outcome": AcquisitionFailureOutcome.HTTP_ERROR,
        "diagnostic_message": "HTTP connection failed",
        "final_url": final_url,
        "status_code": status_code,
        "content_type": content_type,
        "retry_after_seconds": retry_after_seconds,
    }
    data.update(overrides)
    return AcquisitionFailure(**data)


def _make_game_search_validation_success(
    acquisition: AcquisitionSuccess,
) -> CheapSharkGameSearchSuccess:
    lego_batman_mapping = {"gameID": "2", "external": "LEGO Batman"}
    batman_mapping = {"gameID": "1", "external": "Batman"}
    games = (
        CheapSharkGameCandidate.model_validate(lego_batman_mapping),
        CheapSharkGameCandidate.model_validate(batman_mapping),
    )
    return CheapSharkGameSearchSuccess(
        acquisition=acquisition,
        games=games,
    )


def _make_normalized_game_search(
    validation: CheapSharkGameSearchSuccess,
) -> NormalizedCheapSharkGameSearch:
    games = (
        NormalizedCheapSharkGameCandidate(
            game_id=2,
            title="LEGO Batman",
        ),
        NormalizedCheapSharkGameCandidate(
            game_id=1,
            title="Batman",
        ),
    )
    return NormalizedCheapSharkGameSearch(
        validation=validation,
        games=games,
    )


class FakeGameSearchAcquirer:
    def __init__(self, result: AcquisitionResult) -> None:
        self.result = result

    def acquire(self, query: str) -> AcquisitionResult:
        self.called_query = query
        return self.result


class FakeGameSearchValidator:
    def __init__(self, result: CheapSharkGameSearchResult) -> None:
        self.result = result

    def validate(
        self,
        acquisition: AcquisitionSuccess,
    ) -> CheapSharkGameSearchResult:
        self.called_acquisition = acquisition
        return self.result


class FakeGameSearchNormalizer:
    def __init__(
        self,
        result: NormalizedCheapSharkGameSearch,
    ) -> None:
        self.result = result

    def normalize(
        self,
        validation: CheapSharkGameSearchSuccess,
    ) -> NormalizedCheapSharkGameSearch:
        self.called_validation = validation
        return self.result


class FailIfCalledGameSearchValidator:
    def validate(self, acquisition: AcquisitionResult) -> Never:
        raise AssertionError(
            "validator must not be called after acquisition failure"
        )


class FailIfCalledGameSearchNormalizer:
    def normalize(self, validation: CheapSharkGameSearchResult) -> Never:
        raise AssertionError(
            "normalizer must not be called after acquisition failure"
        )


def test_search_games_returns_success_and_preserves_normalized_candidate_order(
) -> None:
    query = "Batman"

    acquisition = _make_acquisition_success()
    validation = _make_game_search_validation_success(acquisition)
    normalization = _make_normalized_game_search(validation)

    acquirer = FakeGameSearchAcquirer(acquisition)
    validator = FakeGameSearchValidator(validation)
    normalizer = FakeGameSearchNormalizer(normalization)

    searcher = SearchGames(
        acquirer,
        validator,
        normalizer,
    )

    result = searcher.search(query)

    assert acquirer.called_query == query
    assert validator.called_acquisition is acquisition
    assert normalizer.called_validation is validation

    assert isinstance(result, GameSearchSuccess)
    lego_batman_candidate, batman_candidate = result.candidates
    assert isinstance(lego_batman_candidate, GameSearchCandidate)
    assert lego_batman_candidate.game_id == 2
    assert lego_batman_candidate.title == "LEGO Batman"
    assert isinstance(batman_candidate, GameSearchCandidate)
    assert batman_candidate.game_id == 1
    assert batman_candidate.title == "Batman"


def test_search_games_maps_acquisition_network_error_to_connection_failed() -> None:
    acquisition = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.NETWORK_ERROR,
        diagnostic_message="HTTP connection failed",
        final_url=None,
        status_code=None,
        content_type=None,
    )

    acquirer = FakeGameSearchAcquirer(acquisition)
    validator = FailIfCalledGameSearchValidator()
    normalizer = FailIfCalledGameSearchNormalizer()

    searcher = SearchGames(
        acquirer,
        validator,
        normalizer,
    )

    result = searcher.search(QUERY)

    assert isinstance(result, GameSearchFailure)
    assert result.outcome == GameSearchFailureOutcome.CONNECTION_FAILED
    assert result.retry_after_seconds is None


@pytest.mark.parametrize(
    "retry_after_seconds",
    [None, 0, 30],
)
def test_search_games_maps_acquisition_http_429_to_rate_limited_and_preserves_retry_after(
    retry_after_seconds: int | None,
) -> None:
    acquisition = _make_acquisition_failure(
        diagnostic_message="HTTP request returned status 429",
        final_url=FINAL_URL,
        status_code=429,
        content_type=CONTENT_TYPE,
        retry_after_seconds=retry_after_seconds,
    )
    acquirer = FakeGameSearchAcquirer(acquisition)
    validator = FailIfCalledGameSearchValidator()
    normalizer = FailIfCalledGameSearchNormalizer()

    searcher = SearchGames(
        acquirer,
        validator,
        normalizer,
    )

    result = searcher.search(QUERY)

    assert isinstance(result, GameSearchFailure)
    assert result.outcome == GameSearchFailureOutcome.RATE_LIMITED
    assert result.retry_after_seconds == retry_after_seconds


def test_search_games_maps_non_429_acquisition_http_error_to_search_request_failed() -> None:
    acquisition = _make_acquisition_failure(
        diagnostic_message="HTTP request returned status 503",
        final_url=FINAL_URL,
        status_code=503,
        content_type=CONTENT_TYPE,
    )

    acquirer = FakeGameSearchAcquirer(acquisition)
    validator = FailIfCalledGameSearchValidator()
    normalizer = FailIfCalledGameSearchNormalizer()

    searcher = SearchGames(
        acquirer,
        validator,
        normalizer,
    )

    result = searcher.search(QUERY)

    assert isinstance(result, GameSearchFailure)
    assert result.outcome == GameSearchFailureOutcome.SEARCH_REQUEST_FAILED
    assert result.retry_after_seconds is None


@pytest.mark.parametrize(
    ("acquisition_outcome", "diagnostic_message"),
    [
        (
            AcquisitionFailureOutcome.TIMEOUT,
            "HTTP request timed out",
        ),
        (
            AcquisitionFailureOutcome.REQUEST_ERROR,
            "HTTP request failed",
        ),
        (
            AcquisitionFailureOutcome.BLOCKED,
            "Acquisition was blocked",
        ),
        (
            AcquisitionFailureOutcome.BROWSER_ERROR,
            "Browser acquisition failed",
        ),
    ],
)
def test_search_games_maps_acquisition_request_failures_to_search_request_failed(
    acquisition_outcome: AcquisitionFailureOutcome,
    diagnostic_message: str,
) -> None:
    acquisition = _make_acquisition_failure(
        outcome=acquisition_outcome,
        diagnostic_message=diagnostic_message,
        final_url=None,
        status_code=None,
        content_type=None,
    )

    acquirer = FakeGameSearchAcquirer(acquisition)
    validator = FailIfCalledGameSearchValidator()
    normalizer = FailIfCalledGameSearchNormalizer()

    searcher = SearchGames(
        acquirer,
        validator,
        normalizer,
    )

    result = searcher.search(QUERY)

    assert isinstance(result, GameSearchFailure)
    assert result.outcome == GameSearchFailureOutcome.SEARCH_REQUEST_FAILED
    assert result.retry_after_seconds is None


def test_search_games_maps_unexpected_content_to_invalid_source_response() -> None:
    acquisition = _make_acquisition_failure(
        outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
        diagnostic_message="HTTP response body is not valid JSON",
        final_url=FINAL_URL,
        status_code=200,
        content_type=CONTENT_TYPE,
    )

    acquirer = FakeGameSearchAcquirer(acquisition)
    validator = FailIfCalledGameSearchValidator()
    normalizer = FailIfCalledGameSearchNormalizer()

    searcher = SearchGames(
        acquirer,
        validator,
        normalizer,
    )

    result = searcher.search(QUERY)

    assert isinstance(result, GameSearchFailure)
    assert result.outcome == GameSearchFailureOutcome.INVALID_SOURCE_RESPONSE
    assert result.retry_after_seconds is None


def test_search_games_maps_validation_failure_to_invalid_source_response() -> None:
    acquisition = _make_acquisition_success()
    validation = CheapSharkGameSearchFailure(
        acquisition=acquisition,
        diagnostic_message=(
            "Invalid JSON: EOF while parsing a list at line 1 column 38"
        ),
    )

    acquirer = FakeGameSearchAcquirer(acquisition)
    validator = FakeGameSearchValidator(validation)
    normalizer = FailIfCalledGameSearchNormalizer()

    searcher = SearchGames(
        acquirer,
        validator,
        normalizer,
    )

    result = searcher.search(QUERY)

    assert acquirer.called_query == QUERY
    assert validator.called_acquisition is acquisition

    assert isinstance(result, GameSearchFailure)
    assert result.outcome == GameSearchFailureOutcome.INVALID_SOURCE_RESPONSE
    assert result.retry_after_seconds is None


def test_search_games_returns_success_with_no_candidates_when_normalized_search_is_empty() -> None:
    acquisition = _make_acquisition_success(content="[]")
    validation = CheapSharkGameSearchSuccess(
        acquisition=acquisition,
        games=(),
    )

    normalization = NormalizedCheapSharkGameSearch(
        validation=validation,
        games=(),
    )

    acquirer = FakeGameSearchAcquirer(acquisition)
    validator = FakeGameSearchValidator(validation)
    normalizer = FakeGameSearchNormalizer(normalization)

    searcher = SearchGames(
        acquirer,
        validator,
        normalizer,
    )

    result = searcher.search(QUERY)

    assert acquirer.called_query == QUERY
    assert validator.called_acquisition is acquisition
    assert normalizer.called_validation is validation

    assert isinstance(result, GameSearchSuccess)
    assert result.candidates == ()
