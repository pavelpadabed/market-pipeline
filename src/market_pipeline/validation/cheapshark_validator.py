from pydantic import ValidationError

from market_pipeline.extraction.models import (
    CheapSharkDealExtractionFailure,
    CheapSharkExtractionSuccess,
)
from market_pipeline.validation.models import (
    CheapSharkDealValidationFailure,
    CheapSharkDealValidationResult,
    CheapSharkValidationFailure,
    CheapSharkValidationResult,
    CheapSharkValidationSuccess,
    ValidatedCheapSharkDeal,
    ValidatedCheapSharkGameMetadata,
)


def _format_validation_error(error: ValidationError) -> str:
    buffer_messages = []
    for error_value in error.errors():
        loc = error_value["loc"]
        msg = error_value["msg"]

        location = ".".join(str(el) for el in loc)
        message = f"{location}: {msg}"
        buffer_messages.append(message)

    return "\n".join(buffer_messages)


class CheapSharkValidator:
    def validate(
        self,
        extraction: CheapSharkExtractionSuccess,
    ) -> CheapSharkValidationResult:
        raw_game_metadata = extraction.raw_game_metadata
        try:
            validated_game_metadata = ValidatedCheapSharkGameMetadata.model_validate(
                raw_game_metadata
            )
        except ValidationError as exc:
            diagnostic_message = _format_validation_error(exc)
            return CheapSharkValidationFailure(
                extraction=extraction,
                diagnostic_message=diagnostic_message,
            )

        deal_results = extraction.deal_results
        buffer_deal_results: list[CheapSharkDealValidationResult] = []

        for index, candidate in enumerate(deal_results):
            if isinstance(candidate, CheapSharkDealExtractionFailure):
                buffer_deal_results.append(candidate)
                continue

            try:
                validated_deal = ValidatedCheapSharkDeal.model_validate(
                    candidate.raw
                )
                buffer_deal_results.append(validated_deal)
            except ValidationError as exc:
                diagnostic_message = _format_validation_error(exc)
                deal_validation_failure = CheapSharkDealValidationFailure(
                    index=index,
                    raw=candidate.raw,
                    diagnostic_message=diagnostic_message,
                )
                buffer_deal_results.append(deal_validation_failure)

        return CheapSharkValidationSuccess(
            extraction=extraction,
            validated_game_metadata=validated_game_metadata,
            deal_results=tuple(buffer_deal_results),
        )
