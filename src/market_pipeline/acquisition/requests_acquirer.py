from datetime import datetime

from market_pipeline.acquisition.http_transport import HttpGetTransport
from market_pipeline.acquisition.models import (
    AcquisitionFailure,
    AcquisitionFailureOutcome,
    AcquisitionMethod,
    AcquisitionResult,
    AcquisitionSuccess,
)


class RequestsAcquirer:
    def __init__(self, transport: HttpGetTransport) -> None:
        self.transport = transport

    def _build_failure(
        self,
        requested_url: str,
        started_at: datetime,
        finished_at: datetime,
        outcome: AcquisitionFailureOutcome,
        diagnostic_message: str,
        final_url: str | None = None,
        status_code: int | None = None,
        content_type: str | None = None,
    ) -> AcquisitionFailure:
        return AcquisitionFailure(
            requested_url=requested_url,
            method=AcquisitionMethod.HTTP,
            started_at=started_at,
            finished_at=finished_at,
            outcome=outcome,
            diagnostic_message=diagnostic_message,
            final_url=final_url,
            status_code=status_code,
            content_type=content_type,
        )

    def acquire(self, url: str) -> AcquisitionResult:
        http_result = self.transport.get(url)
        if isinstance(http_result, AcquisitionFailure):
            return http_result

        started_at = http_result.started_at
        finished_at = http_result.finished_at
        content_type = http_result.headers.get("Content-Type")
        final_url = http_result.final_url
        status_code = http_result.status_code
        content = http_result.content

        if not 200 <= status_code <= 299:
            return self._build_failure(
                requested_url=url,
                started_at=started_at,
                finished_at=finished_at,
                outcome=AcquisitionFailureOutcome.HTTP_ERROR,
                diagnostic_message=f"HTTP request returned status {status_code}",
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
            )

        if content_type is None:
            return self._build_failure(
                requested_url=url,
                started_at=started_at,
                finished_at=finished_at,
                outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
                diagnostic_message="Missing Content-Type header",
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
            )

        media_type, _, _ = content_type.partition(";")

        if media_type.strip().lower() != "text/html":
            return self._build_failure(
                requested_url=url,
                started_at=started_at,
                finished_at=finished_at,
                outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
                diagnostic_message=f"Unsupported Content-Type: {content_type}",
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
            )

        if not content.strip():
            return self._build_failure(
                requested_url=url,
                started_at=started_at,
                finished_at=finished_at,
                outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
                diagnostic_message="HTTP response body is blank",
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
            )

        return AcquisitionSuccess(
            requested_url=url,
            method=AcquisitionMethod.HTTP,
            started_at=started_at,
            finished_at=finished_at,
            final_url=final_url,
            status_code=status_code,
            content_type=content_type,
            content=content,
        )
