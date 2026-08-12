from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

import requests
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
)


@dataclass(frozen=True, slots=True)
class HttpResponseSnapshot:
    requested_url: str
    started_at: datetime
    finished_at: datetime
    status_code: int
    final_url: str
    headers: dict[str, str]
    content: str

type HttpTransportResult = HttpResponseSnapshot | AcquisitionFailure


class HttpGetTransport:
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

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str | int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpTransportResult:
        prepared_request = requests.Request(
            method="GET",
            url=url,
            params=params,
        ).prepare()
        requested_url = prepared_request.url
        started_at = datetime.now(tz=UTC)
        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
        except Timeout:
            return self._build_failure(
                requested_url=requested_url,
                started_at=started_at,
                outcome=AcquisitionFailureOutcome.TIMEOUT,
                diagnostic_message="HTTP request timed out",
            )
        except ConnectionError:
            return self._build_failure(
                requested_url=requested_url,
                started_at=started_at,
                outcome=AcquisitionFailureOutcome.NETWORK_ERROR,
                diagnostic_message="HTTP connection failed",
            )
        except TooManyRedirects as exc:
            redirect_response = exc.response
            if redirect_response is None:
                return self._build_failure(
                    requested_url=requested_url,
                    started_at=started_at,
                    outcome=AcquisitionFailureOutcome.HTTP_ERROR,
                    diagnostic_message="HTTP request exceeded redirect limit",
                )
            return self._build_failure(
                requested_url=requested_url,
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
                    requested_url=requested_url,
                    started_at=started_at,
                    outcome=AcquisitionFailureOutcome.REQUEST_ERROR,
                    diagnostic_message=f"HTTP request failed: {type(exc).__name__}",
                )
            return self._build_failure(
                requested_url=requested_url,
                started_at=started_at,
                outcome=AcquisitionFailureOutcome.REQUEST_ERROR,
                diagnostic_message=f"HTTP request failed: {type(exc).__name__}",
                final_url=request_response.url,
                status_code=request_response.status_code,
                content_type=request_response.headers.get("Content-Type"),
            )

        finished_at = datetime.now(tz=UTC)
        status_code = response.status_code
        final_url = response.url
        headers = response.headers
        content = response.text

        return HttpResponseSnapshot(
            requested_url=requested_url,
            started_at=started_at,
            finished_at=finished_at,
            final_url=final_url,
            status_code=status_code,
            headers=headers,
            content=content,
        )
