import json
from datetime import datetime

from market_pipeline.acquisition.http_transport import HttpGetTransport
from market_pipeline.acquisition.models import (
    AcquisitionFailure,
    AcquisitionFailureOutcome,
    AcquisitionMethod,
    AcquisitionResult,
    AcquisitionSuccess,
)

STORES_ENDPOINT = "https://www.cheapshark.com/api/1.0/stores"


class CheapSharkStoresAcquirer:
    def __init__(
        self,
        transport: HttpGetTransport,
        user_agent: str,
    ) -> None:
        self.transport = transport
        self.user_agent = user_agent

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
        retry_after_seconds: int | None = None,
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
            retry_after_seconds=retry_after_seconds,
        )

    def acquire(self) -> AcquisitionResult:
        params = None
        headers = {"User-Agent": self.user_agent}

        http_result = self.transport.get(
            STORES_ENDPOINT,
            params=params,
            headers=headers,
        )

        if isinstance(http_result, AcquisitionFailure):
            return http_result

        status_code = http_result.status_code
        requested_url = http_result.requested_url
        final_url = http_result.final_url
        started_at = http_result.started_at
        finished_at = http_result.finished_at
        content_type = http_result.headers.get("Content-Type")

        if status_code == 429:
            retry_after_seconds = None
            raw_retry_after = http_result.headers.get("Retry-After")
            if raw_retry_after is not None:
                try:
                    retry_after_seconds = int(raw_retry_after)
                except ValueError:
                    pass
            return self._build_failure(
                requested_url=requested_url,
                started_at=started_at,
                finished_at=finished_at,
                outcome=AcquisitionFailureOutcome.HTTP_ERROR,
                diagnostic_message="HTTP request returned status 429",
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
                retry_after_seconds=retry_after_seconds,
            )
        if not 200 <= status_code <= 299:
            return self._build_failure(
                requested_url=requested_url,
                started_at=started_at,
                finished_at=finished_at,
                outcome=AcquisitionFailureOutcome.HTTP_ERROR,
                diagnostic_message=(
                    f"HTTP request returned status {status_code}"
                ),
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
            )
        if content_type is None:
            return self._build_failure(
                requested_url=requested_url,
                started_at=started_at,
                finished_at=finished_at,
                outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
                diagnostic_message="Missing Content-Type header",
                final_url=final_url,
                status_code=status_code,
                content_type=None,
            )
        media_type, _, _ = content_type.partition(";")
        if media_type.strip().lower() != "application/json":
            return self._build_failure(
                requested_url=requested_url,
                started_at=started_at,
                finished_at=finished_at,
                outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
                diagnostic_message=f"Unsupported Content-Type: {content_type}",
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
            )
        content = http_result.content
        if not content.strip():
            return self._build_failure(
                requested_url=requested_url,
                started_at=started_at,
                finished_at=finished_at,
                outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
                diagnostic_message="HTTP response body is blank",
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
            )
        try:
            json.loads(content)
        except json.JSONDecodeError:
            return self._build_failure(
                requested_url=requested_url,
                started_at=started_at,
                finished_at=finished_at,
                outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
                diagnostic_message="HTTP response body is not valid JSON",
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
            )
        return AcquisitionSuccess(
            requested_url=http_result.requested_url,
            method=AcquisitionMethod.HTTP,
            started_at=http_result.started_at,
            finished_at=http_result.finished_at,
            final_url=http_result.final_url,
            status_code=http_result.status_code,
            content_type=content_type,
            content=http_result.content,
        )
