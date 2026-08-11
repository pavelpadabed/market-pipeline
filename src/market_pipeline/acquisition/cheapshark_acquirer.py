from datetime import UTC, datetime
import json

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
    AcquisitionResult,
    AcquisitionSuccess,
)

GAMES_ENDPOINT = "https://www.cheapshark.com/api/1.0/games"


class CheapSharkApiAcquirer:
    def __init__(
        self,
        session,
        timeout: float,
        user_agent: str,
    ) -> None:
        self.session = session
        self.timeout = timeout
        self.user_agent = user_agent

    def _build_failure(
        self,
        requested_url: str,
        started_at: datetime,
        outcome: AcquisitionFailureOutcome,
        diagnostic_message: str,
        final_url: str | None = None,
        status_code: int | None = None,
        content_type: str | None = None,
        retry_after_seconds: int | None = None,
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
            retry_after_seconds=retry_after_seconds,
        )

    def acquire(self, game_id: int) -> AcquisitionResult:
        if type(game_id) is not int:
            raise TypeError("game_id must have type int")
        params = {"id": game_id}
        headers = {"User-Agent": self.user_agent}
        prepared_request = requests.Request(
            method="GET",
            url=GAMES_ENDPOINT,
            params=params,
        ).prepare()
        requested_url = prepared_request.url
        started_at = datetime.now(tz=UTC)
        try:
            response = self.session.get(
                GAMES_ENDPOINT,
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
        status_code = response.status_code
        final_url = response.url
        content_type = response.headers.get("Content-Type")
        retry_after_seconds = None
        raw_retry_after = response.headers.get("Retry-After")

        if status_code == 429:
            if raw_retry_after is not None:
                try:
                    parsed_after_seconds = int(raw_retry_after)
                except ValueError:
                    pass
                else:
                    if parsed_after_seconds >= 0:
                        retry_after_seconds = parsed_after_seconds
            return self._build_failure(
                requested_url=requested_url,
                started_at=started_at,
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
                outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
                diagnostic_message="Missing Content-Type header",
                final_url=final_url,
                status_code=status_code,
            )
        media_type, _, _ = content_type.partition(";")
        if media_type.strip().lower() != "application/json":
            return self._build_failure(
                requested_url=requested_url,
                started_at=started_at,
                outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
                diagnostic_message=(
                    f"Unsupported Content-Type: {content_type}"
                ),
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
            )

        content = response.text
        if not content.strip():
            return self._build_failure(
                requested_url=requested_url,
                started_at=started_at,
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
                outcome=AcquisitionFailureOutcome.UNEXPECTED_CONTENT,
                diagnostic_message=(
                    "HTTP response body is not valid JSON"
                ),
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
            )

        finished_at = datetime.now(tz=UTC)
        return AcquisitionSuccess(
            requested_url=requested_url,
            method=AcquisitionMethod.HTTP,
            started_at=started_at,
            finished_at=finished_at,
            final_url=response.url,
            status_code=response.status_code,
            content_type=response.headers.get("Content-Type"),
            content=response.text,
        )
