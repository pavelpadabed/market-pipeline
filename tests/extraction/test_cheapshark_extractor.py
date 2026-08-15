import json
from datetime import UTC, datetime

from market_pipeline.acquisition.models import (
    AcquisitionMethod,
    AcquisitionSuccess,
)
from market_pipeline.extraction.cheapshark_extractor import CheapSharkExtractor
from market_pipeline.extraction.models import (
    CheapSharkDealCandidate,
    CheapSharkDealExtractionFailure,
    CheapSharkExtractionFailure,
    CheapSharkExtractionFailureOutcome,
    CheapSharkExtractionSuccess,
)

VALID_GAME_DATA = {
    "info": {
        "title": "Batman: Arkham City",
    },
    "deals": [
        {
            "storeID": "1",
            "price": "4.99",
        },
        {
            "storeID": "2",
            "price": "7.49",
        },
    ],
}


def make_acquisition_success(**overrides) -> AcquisitionSuccess:
    started_at = datetime(
        2026, 8, 4, 8, tzinfo=UTC
    )
    finished_at = datetime(
        2026, 8, 4, 8, 1, tzinfo=UTC
    )
    data = {
        "requested_url": "https://example.test/product",
        "method": AcquisitionMethod.HTTP,
        "started_at": started_at,
        "finished_at": finished_at,
        "final_url": "https://example.test/products/123",
        "status_code": 200,
        "content_type": "application/json",
        "content": '{"info": {}, "deals": []}',
    }
    data.update(overrides)

    return AcquisitionSuccess(**data)


def test_cheapshark_extractor_returns_success_for_empty_info_and_deals() -> None:
    acquisition = make_acquisition_success()
    extractor = CheapSharkExtractor()
    result = extractor.extract(acquisition)

    assert isinstance(result, CheapSharkExtractionSuccess)
    assert result.acquisition is acquisition
    assert result.raw_game_metadata == {}
    assert result.deal_results == ()


def test_cheapshark_extractor_preserves_valid_deal_candidates_in_source_order(
) -> None:
    content = json.dumps(VALID_GAME_DATA)
    acquisition = make_acquisition_success(content=content)
    extractor = CheapSharkExtractor()
    result = extractor.extract(acquisition)

    expected_deal_results = (
        CheapSharkDealCandidate(
            raw={"storeID": "1", "price": "4.99"},
        ),
        CheapSharkDealCandidate(
            raw={"storeID": "2", "price": "7.49"},
        ),
    )

    assert isinstance(result, CheapSharkExtractionSuccess)
    assert result.raw_game_metadata == {"title": "Batman: Arkham City"}
    assert result.deal_results == expected_deal_results


def test_cheapshark_extractor_preserves_candidates_around_non_mapping_deal(
) -> None:
    data = {
        "info": {"title": "Batman: Arkham City"},
        "deals": [
            {"storeID": "1", "price": "4.99"},
            "invalid_deal",
            {"storeID": "2", "price": "7.49"},
        ],
    }
    content = json.dumps(data)
    acquisition = make_acquisition_success(content=content)
    extractor = CheapSharkExtractor()
    result = extractor.extract(acquisition)

    expected_deal_results = (
        CheapSharkDealCandidate(
            raw={"storeID": "1", "price": "4.99"},
        ),
        CheapSharkDealExtractionFailure(
            index=1,
            raw="invalid_deal",
            diagnostic_message="Deal candidate must be a mapping",
        ),
        CheapSharkDealCandidate(
            raw={"storeID": "2", "price": "7.49"},
        ),
    )

    assert isinstance(result, CheapSharkExtractionSuccess)
    assert result.deal_results == expected_deal_results


def test_cheapshark_extractor_returns_failure_for_invalid_json() -> None:
    acquisition = make_acquisition_success(content='{"info": {}, "deals": []')
    extractor = CheapSharkExtractor()
    result = extractor.extract(acquisition)

    assert isinstance(result, CheapSharkExtractionFailure)
    assert result.acquisition is acquisition
    assert result.outcome == CheapSharkExtractionFailureOutcome.INVALID_JSON
    assert result.diagnostic_message == "Acquired content is not valid JSON"


def test_cheapshark_extractor_returns_failure_when_json_root_is_not_mapping(
) -> None:
    acquisition = make_acquisition_success(content='[]')
    extractor = CheapSharkExtractor()
    result = extractor.extract(acquisition)

    assert isinstance(result, CheapSharkExtractionFailure)
    assert result.acquisition is acquisition
    assert result.outcome == CheapSharkExtractionFailureOutcome.ROOT_NOT_MAPPING
    assert result.diagnostic_message == "CheapShark JSON root must be a mapping"


def test_cheapshark_extractor_returns_failure_when_info_is_missing() -> None:
    acquisition = make_acquisition_success(content='{"deals": []}')
    extractor = CheapSharkExtractor()
    result = extractor.extract(acquisition)

    assert isinstance(result, CheapSharkExtractionFailure)
    assert result.acquisition is acquisition
    assert result.outcome == CheapSharkExtractionFailureOutcome.INFO_MISSING
    assert result.diagnostic_message == "CheapShark JSON document is missing info"


def test_cheapshark_extractor_returns_failure_when_info_is_not_mapping() -> None:
    acquisition = make_acquisition_success(content='{"info": [], "deals": []}')
    extractor = CheapSharkExtractor()
    result = extractor.extract(acquisition)

    assert isinstance(result, CheapSharkExtractionFailure)
    assert result.acquisition is acquisition
    assert result.outcome == CheapSharkExtractionFailureOutcome.INFO_NOT_MAPPING
    assert result.diagnostic_message == "CheapShark info must be a mapping"


def test_cheapshark_extractor_returns_failure_when_deals_are_missing() -> None:
    acquisition = make_acquisition_success(content='{"info": {}}')
    extractor = CheapSharkExtractor()
    result = extractor.extract(acquisition)

    assert isinstance(result, CheapSharkExtractionFailure)
    assert result.acquisition is acquisition
    assert result.outcome == CheapSharkExtractionFailureOutcome.DEALS_MISSING
    assert result.diagnostic_message == "CheapShark JSON document is missing deals"


def test_cheapshark_extractor_returns_failure_when_deals_are_not_list() -> None:
    acquisition = make_acquisition_success(content='{"info": {}, "deals": {}}')
    extractor = CheapSharkExtractor()
    result = extractor.extract(acquisition)

    assert isinstance(result, CheapSharkExtractionFailure)
    assert result.acquisition is acquisition
    assert result.outcome == CheapSharkExtractionFailureOutcome.DEALS_NOT_LIST
    assert result.diagnostic_message == "CheapShark deals must be a list"
