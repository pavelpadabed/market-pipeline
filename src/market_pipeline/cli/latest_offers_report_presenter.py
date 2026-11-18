from market_pipeline.application.models import (
    LatestOffersReportOutcome,
    LatestOffersReportResult,
)


def format_latest_offers_report(
    result: LatestOffersReportResult,
) -> str:
    match result.outcome:
        case LatestOffersReportOutcome.NO_CURRENT_OFFERS:
            return "No current offers found. Report was not created."
        case LatestOffersReportOutcome.STORE_CATALOG_UNAVAILABLE:
            return (
                "Required marketplace information is unavailable. "
                "Report was not created. Please try again later."
            )
        case LatestOffersReportOutcome.REPORT_SAVED:
            return (
                "Report saved successfully.\n"
                "\n"
                f"Exported offers: {result.exported_offer_count}"
            )
        case _:
            raise ValueError(
                f"unsupported latest offers report outcome: {result.outcome}"
            )
