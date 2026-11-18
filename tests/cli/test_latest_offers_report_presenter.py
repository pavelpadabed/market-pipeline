from market_pipeline.application.models import (
    LatestOffersReportOutcome,
    LatestOffersReportResult,
)
from market_pipeline.cli.latest_offers_report_presenter import (
    format_latest_offers_report,
)


def test_latest_offers_report_presenter_returns_report_saved_message_with_exported_offer_count(
) -> None:
    result = LatestOffersReportResult(
        outcome=LatestOffersReportOutcome.REPORT_SAVED,
        exported_offer_count=1,
    )

    expected_message = (
        "Report saved successfully.\n"
        "\n"
        "Exported offers: 1"
    )

    actual_message = format_latest_offers_report(result)

    assert actual_message == expected_message


def test_latest_offers_report_presenter_returns_no_offers_message() -> None:
    result = LatestOffersReportResult(
        outcome=LatestOffersReportOutcome.NO_CURRENT_OFFERS,
        exported_offer_count=None,
    )

    expected_message = "No current offers found. Report was not created."

    actual_message = format_latest_offers_report(result)

    assert actual_message == expected_message


def test_latest_offers_report_presenter_returns_store_catalog_unavailable_message() -> None:
    result = LatestOffersReportResult(
        outcome=LatestOffersReportOutcome.STORE_CATALOG_UNAVAILABLE,
        exported_offer_count=None,
    )

    expected_message = (
        "Required marketplace information is unavailable. "
        "Report was not created. Please try again later."
    )

    actual_message = format_latest_offers_report(result)

    assert actual_message == expected_message
