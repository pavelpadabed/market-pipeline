import json
from collections.abc import Mapping

from market_pipeline.acquisition.models import AcquisitionSuccess
from market_pipeline.extraction.models import (
    CheapSharkDealCandidate,
    CheapSharkDealExtractionFailure,
    CheapSharkDealResult,
    CheapSharkExtractionFailure,
    CheapSharkExtractionFailureOutcome,
    CheapSharkExtractionResult,
    CheapSharkExtractionSuccess,
)

_MISSING = object()


class CheapSharkExtractor:
    def extract(
        self,
        acquisition: AcquisitionSuccess,
    ) -> CheapSharkExtractionResult:
        content = acquisition.content
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return CheapSharkExtractionFailure(
                acquisition=acquisition,
                outcome=CheapSharkExtractionFailureOutcome.INVALID_JSON,
                diagnostic_message="Acquired content is not valid JSON",
            )

        if not isinstance(data, Mapping):
            return CheapSharkExtractionFailure(
                acquisition=acquisition,
                outcome=CheapSharkExtractionFailureOutcome.ROOT_NOT_MAPPING,
                diagnostic_message="CheapShark JSON root must be a mapping",
            )

        info = data.get("info", _MISSING)
        if info is _MISSING:
            return CheapSharkExtractionFailure(
                acquisition=acquisition,
                outcome=CheapSharkExtractionFailureOutcome.INFO_MISSING,
                diagnostic_message="CheapShark JSON document is missing info",
            )
        if not isinstance(info, Mapping):
            return CheapSharkExtractionFailure(
                acquisition=acquisition,
                outcome=CheapSharkExtractionFailureOutcome.INFO_NOT_MAPPING,
                diagnostic_message="CheapShark info must be a mapping",
            )

        raw_game_metadata = info

        deals = data.get("deals", _MISSING)
        if deals is _MISSING:
            return CheapSharkExtractionFailure(
                acquisition=acquisition,
                outcome=CheapSharkExtractionFailureOutcome.DEALS_MISSING,
                diagnostic_message="CheapShark JSON document is missing deals",
            )
        if not isinstance(deals, list):
            return CheapSharkExtractionFailure(
                acquisition=acquisition,
                outcome=CheapSharkExtractionFailureOutcome.DEALS_NOT_LIST,
                diagnostic_message="CheapShark deals must be a list",
            )

        deal_results_buffer: list[CheapSharkDealResult] = []

        for index, deal in enumerate(deals):
            if isinstance(deal, Mapping):
                candidate = CheapSharkDealCandidate(
                    raw=deal,
                )
                deal_results_buffer.append(candidate)
            else:
                failure = CheapSharkDealExtractionFailure(
                    index=index,
                    raw=deal,
                    diagnostic_message="Deal candidate must be a mapping",
                )
                deal_results_buffer.append(failure)

        deal_results = tuple(deal_results_buffer)
        return CheapSharkExtractionSuccess(
            acquisition=acquisition,
            raw_game_metadata=raw_game_metadata,
            deal_results=deal_results,
        )
