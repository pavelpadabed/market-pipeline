from market_pipeline.application.models import (
    RunPipelineOutcome,
    RunPipelineResult,
)


def format_run_pipeline_result(result: RunPipelineResult) -> str:
    """Format the main pipeline result for the CLI boundary."""
    match result.outcome:
        case RunPipelineOutcome.NO_OFFERS:
            return "Pipeline completed successfully. No offers found."

        case (
            RunPipelineOutcome.OFFERS_PARTIALLY_SAVED
            | RunPipelineOutcome.ALL_OFFERS_REJECTED
        ):
            rejection_scope = (
                "some" if result.outcome is RunPipelineOutcome.OFFERS_PARTIALLY_SAVED
                else "all"
            )
            return (
                f"Pipeline completed with {rejection_scope} offers rejected:\n"
                "\n"
                f"Offers found: {result.source_record_count}\n"
                f"Offers saved: {result.saved_observation_count}\n"
                f"Offers rejected: {result.rejected_record_count}"
            )

        case RunPipelineOutcome.CONNECTION_ERROR:
            return (
                "Could not connect to the marketplace service. "
                "Check your internet connection and try again."
            )

        case RunPipelineOutcome.RATE_LIMITED:
            if result.retry_after_seconds is None:
                return (
                    "The marketplace service is receiving too many requests. "
                    "Please try again later."
                )
            if result.retry_after_seconds == 0:
                return (
                    "The marketplace service is receiving too many requests. "
                    "You can try again now."
                )
            time_unit = ("second" if result.retry_after_seconds == 1 else "seconds")
            return (
                "The marketplace service is receiving too many requests. "
                f"Please try again in {result.retry_after_seconds} {time_unit}."
            )

        case RunPipelineOutcome.PROCESSING_FAILED:
            return "Could not complete the pipeline. Please try again later."

        case RunPipelineOutcome.OFFERS_SAVED:
            return (
                "Pipeline completed successfully:\n"
                "\n"
                f"Offers found: {result.source_record_count}\n"
                f"Offers saved: {result.saved_observation_count}"
            )

        case _:
            raise ValueError(f"unsupported run pipeline outcome: {result.outcome}")
