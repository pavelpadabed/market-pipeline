from market_pipeline.application.models import (
    RunPipelineOutcome,
    RunPipelineResult,
)
from market_pipeline.cli.run_pipeline_presenter import (
    format_run_pipeline_result,
)


def _make_early_failure_result(
    outcome: RunPipelineOutcome,
    retry_after_seconds: int | None = None,
) -> RunPipelineResult:
    return RunPipelineResult(
        outcome=outcome,
        retry_after_seconds=retry_after_seconds,
        source_record_count=None,
        saved_observation_count=None,
        rejected_record_count=None,
    )


def test_format_run_pipeline_result_returns_offers_saved_message() -> None:
    result = RunPipelineResult(
        outcome=RunPipelineOutcome.OFFERS_SAVED,
        retry_after_seconds=None,
        source_record_count=2,
        saved_observation_count=2,
        rejected_record_count=0,
    )

    expected_message = (
        "Pipeline completed successfully:\n"
        "\n"
        "Offers found: 2\n"
        "Offers saved: 2"
    )

    actual_message = format_run_pipeline_result(result)

    assert actual_message == expected_message


def test_format_run_pipeline_result_returns_no_offers_message() -> None:
    result = RunPipelineResult(
        outcome=RunPipelineOutcome.NO_OFFERS,
        retry_after_seconds=None,
        source_record_count=0,
        saved_observation_count=0,
        rejected_record_count=0,
    )

    expected_message = "Pipeline completed successfully. No offers found."

    actual_message = format_run_pipeline_result(result)

    assert actual_message == expected_message


def test_format_run_pipeline_result_returns_partially_saved_message() -> None:
    result = RunPipelineResult(
        outcome=RunPipelineOutcome.OFFERS_PARTIALLY_SAVED,
        retry_after_seconds=None,
        source_record_count=2,
        saved_observation_count=1,
        rejected_record_count=1,
    )

    expected_message = (
        "Pipeline completed with some offers rejected:\n"
        "\n"
        "Offers found: 2\n"
        "Offers saved: 1\n"
        "Offers rejected: 1"
    )

    actual_message = format_run_pipeline_result(result)

    assert actual_message == expected_message


def test_format_run_pipeline_result_returns_all_offers_rejected_message() -> None:
    result = RunPipelineResult(
        outcome=RunPipelineOutcome.ALL_OFFERS_REJECTED,
        retry_after_seconds=None,
        source_record_count=2,
        saved_observation_count=0,
        rejected_record_count=2,
    )

    expected_message = (
        "Pipeline completed with all offers rejected:\n"
        "\n"
        "Offers found: 2\n"
        "Offers saved: 0\n"
        "Offers rejected: 2"
    )

    actual_message = format_run_pipeline_result(result)

    assert actual_message == expected_message


def test_format_run_pipeline_result_returns_connection_error_message() -> None:
    result = _make_early_failure_result(
        outcome=RunPipelineOutcome.CONNECTION_ERROR,
    )

    expected_message = (
        "Could not connect to the marketplace service. "
        "Check your internet connection and try again."
    )

    actual_message = format_run_pipeline_result(result)

    assert actual_message == expected_message


def test_format_run_pipeline_result_returns_rate_limited_message_with_retry_delay(
) -> None:
    result = _make_early_failure_result(
        outcome=RunPipelineOutcome.RATE_LIMITED,
        retry_after_seconds=30,
    )

    expected_message = (
        "The marketplace service is receiving too many requests. "
        "Please try again in 30 seconds."
    )

    actual_message = format_run_pipeline_result(result)

    assert actual_message == expected_message


def test_format_run_pipeline_result_returns_rate_limited_message_when_retry_delay_is_unknown(
) -> None:
    result = _make_early_failure_result(
        outcome=RunPipelineOutcome.RATE_LIMITED,
    )

    expected_message = (
        "The marketplace service is receiving too many requests. "
        "Please try again later."
    )

    actual_message = format_run_pipeline_result(result)

    assert actual_message == expected_message


def test_format_run_pipeline_result_returns_rate_limited_message_when_retry_delay_is_zero(
) -> None:
    result = _make_early_failure_result(
        outcome=RunPipelineOutcome.RATE_LIMITED,
        retry_after_seconds=0,
    )

    expected_message = (
        "The marketplace service is receiving too many requests. "
        "You can try again now."
    )

    actual_message = format_run_pipeline_result(result)

    assert actual_message == expected_message


def test_format_run_pipeline_result_returns_rate_limited_message_when_retry_delay_is_one_second(
) -> None:
    result = _make_early_failure_result(
        outcome=RunPipelineOutcome.RATE_LIMITED,
        retry_after_seconds=1,
    )

    expected_message = (
        "The marketplace service is receiving too many requests. "
        "Please try again in 1 second."
    )

    actual_message = format_run_pipeline_result(result)

    assert actual_message == expected_message


def test_format_run_pipeline_result_returns_processing_failed_message() -> None:
    result = _make_early_failure_result(
        outcome=RunPipelineOutcome.PROCESSING_FAILED,
    )

    expected_message = "Could not complete the pipeline. Please try again later."

    actual_message = format_run_pipeline_result(result)

    assert actual_message == expected_message
