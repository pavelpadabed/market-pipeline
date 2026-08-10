from datetime import UTC, datetime

from requests.exceptions import (
    ConnectionError,
    RequestException,
    Timeout,
    TooManyRedirects,
)

from market_pipeline.acquisition.models import (
    AcquisitionFailure,
    AcquisitionFailureOutcome,
    AcquisitionMethod,
    AcquisitionResult,
    AcquisitionSuccess,
)


class RequestsAcquirer:
    def __init__(self, session, timeout: float) -> None:
        self.session = session
        self.timeout = timeout

    def _build_failure(
        self,
        requested_url: str,
        started_at: datetime,
        outcome: AcquisitionFailureOutcome,
        diagnostic_message: str,
        final_url: str | None = None,
        status_code: int | None = None,
        content_type: str | None = None,
    ) -> AcquisitionFailure:
        finished_at = datetime.now(tz=UTC)

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
        started_at = datetime.now(tz=UTC)

        try:
            response = self.session.get(url, timeout=self.timeout)
        except Timeout:
            return self._build_failure(
                requested_url=url,
                started_at=started_at,
                outcome=AcquisitionFailureOutcome.TIMEOUT,
                diagnostic_message="HTTP request timed out",
            )
        except ConnectionError:
            return self._build_failure(
                requested_url=url,
                started_at=started_at,
                outcome=AcquisitionFailureOutcome.NETWORK_ERROR,
                diagnostic_message="HTTP connection failed",
            )
        except TooManyRedirects as exc:
            redirect_response = exc.response
            if redirect_response is None:
                return self._build_failure(
                    requested_url=url,
                    started_at=started_at,
                    outcome=AcquisitionFailureOutcome.HTTP_ERROR,
                    diagnostic_message="HTTP request exceeded redirect limit",
                )

            return self._build_failure(
                requested_url=url,
                started_at=started_at,
                outcome=AcquisitionFailureOutcome.HTTP_ERROR,
                diagnostic_message="HTTP request exceeded redirect limit",
                final_url=redirect_response.url,
                status_code=redirect_response.status_code,
                content_type=redirect_response.headers.get("Content-Type"),
            )
        except RequestException as exc:
            request_response = exc.response
            if request_response is None:
                return self._build_failure(
                    requested_url=url,
                    started_at=started_at,
                    outcome=AcquisitionFailureOutcome.REQUEST_ERROR,
                    diagnostic_message=(
                        f"HTTP request failed: {type(exc).__name__}"
                    ),
                )
            return self._build_failure(
                requested_url=url,
                started_at=started_at,
                outcome=AcquisitionFailureOutcome.REQUEST_ERROR,
                diagnostic_message=(
                    f"HTTP request failed: {type(exc).__name__}"
                ),
                final_url=request_response.url,
                status_code=request_response.status_code,
                content_type=request_response.headers.get("Content-Type"),
            )

        content_type = response.headers.get("Content-Type")
        final_url = response.url
        status_code = response.status_code

        if not 200 <= status_code <= 299:
            return self._build_failure(
                requested_url=url,
                started_at=started_at,
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
                outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
                diagnostic_message=f"Unsupported Content-Type: {content_type}",
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
            )

        content = response.text

        if not content.strip():
            return self._build_failure(
                requested_url=url,
                started_at=started_at,
                outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
                diagnostic_message="HTTP response body is blank",
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
            )

        finished_at = datetime.now(tz=UTC)

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
