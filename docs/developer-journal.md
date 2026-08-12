# Developer Journal

## Purpose

This journal records development time, completed outcomes, engineering
decisions, verification evidence, and the next small step. It is intended to
support later analysis of where development time goes and how collaboration
with Codex can become more effective.

Time entries are estimates unless a timer or another exact source is named.
Breaks are excluded from focused development time. Verification is recorded
separately from implementation so that an earlier successful run is not
mistaken for a fresh test run.

## 2026-08-10

### Time

- First work window: 07:30-11:15 Europe/Warsaw (3 h 45 min elapsed).
- Breaks during the first window: approximately 40 min total for breakfast and
  a shower.
- Second work window: 11:45-12:08 (23 min).
- Third work window: 13:52-16:22 (2 h 30 min).
- Fourth work window: 17:40-19:32 (1 h 52 min).
- Estimated focused development time for the day: 7 h 50 min.
- Main area: acquisition boundary and acquisition strategies.

### Completed

- Finished the deterministic HTTP acquisition slice in commit `57531d9`
  (`feat: implement HTTP acquisition classification`).
- Defined immutable acquisition success and failure DTOs with timestamps,
  response metadata, acquisition method, and explicit failure outcomes.
- Implemented `RequestsAcquirer` classification for successful HTML, timeout,
  connection failure, request failure, redirect-limit failure, non-2xx HTTP
  responses, missing or unsupported content type, and blank response body.
- Confirmed that HTTP `403` is classified as `HTTP_ERROR`; an acquirer does not
  select a browser fallback. Acquisition-strategy selection belongs to the
  orchestrator.
- Closed the browser-fallback spike without implementing `PlaywrightAcquirer`:
  no permitted production source requiring browser acquisition was confirmed.
- Selected the official CheapShark REST API as the next permitted learning
  vertical slice and began the acquisition-contract design for lookup of one
  game by a known CheapShark `gameID`.

### Verification evidence

- At approximately 11:19, Pavel ran `pytest tests/acquisition` manually in the
  project virtual environment.
- Environment: Python 3.13.5, pytest 9.1.1, pluggy 1.6.0, macOS (`darwin`).
- Result: 30 tests collected, 30 passed in 0.12 seconds.
- The run covers the deterministic acquisition model and `RequestsAcquirer`
  suites in `tests/acquisition`.

### Decisions and boundaries

- `HTTP` remains the acquisition method for REST APIs. An `API` enum value will
  not be introduced without a distinct semantic need.
- The first CheapShark adapter will accept a known `game_id`; it will own the
  fixed `/api/1.0/games` endpoint and the `id` query parameter.
- `AcquisitionSuccess.content` can preserve the JSON response as a string, so
  the existing acquisition DTO can be reused.
- CheapShark acquisition success means that a successful HTTP response contains
  a non-blank, syntactically valid JSON representation. It does not prove that
  expected `info` or `deals` exist.
- Finding CheapShark-specific fields belongs to extraction. Determining whether
  extracted values can form an `OfferObservation` belongs to validation and
  normalization.
- Do not generalize an `ApiAcquirer` in advance. Compare the CheapShark adapter
  with a later real API integration, such as the Eurasian Economic Union API,
  before extracting shared HTTP/API infrastructure.

### CheapShark adapter design session (11:45-12:08)

- Confirmed that the adapter owns the fixed CheapShark Games endpoint and sends
  a single changing `game_id` as the `id` query parameter.
- Kept HTTP as the acquisition method: REST describes the API contract and JSON
  representation, not a new acquisition transport.
- Agreed that the adapter constructor receives the HTTP session, timeout, and a
  descriptive User-Agent. The endpoint remains an adapter constant.
- The User-Agent identifies the application, is not an API key or secret, and
  is configured once while still being sent with every CheapShark request.
- Agreed on a strict integer input contract for `game_id`. Wrong argument types
  are rejected before a network request and are not represented as acquisition
  failures.
- Distinguished caller contract violations from HTTP client failures: an
  invalid input belongs to input validation, while an attempted request that
  fails is represented by `AcquisitionFailure`.

### CheapShark adapter TDD session (13:52-16:22)

- Aligned PyCharm and Codex on the same worktree so that production code, tests,
  project guidance, and this journal are visible from one workspace.
- Created the initial `CheapSharkApiAcquirer` walking skeleton with injected
  session, timeout, and User-Agent dependencies, plus an `acquire(game_id)`
  boundary.
- Designed and implemented the first deterministic happy-path unit test using a
  fake session and fake response; no network access is involved.
- Worked through the flow from integer `game_id`, to the API `id` query mapping,
  to request headers, fake HTTP response, and the shared acquisition DTO.
- Implemented only enough production behaviour to make the happy path green:
  call the fixed Games endpoint with params, headers, and timeout, then return
  `AcquisitionSuccess` with HTTP metadata and raw JSON text.
- Deliberately deferred input-type validation, network exception handling,
  non-2xx classification, content checks, JSON syntax checks, rate-limit
  metadata, and redirect-specific requested/final URL semantics to later TDD
  cycles.

### Verification evidence for the TDD session

- The new CheapShark happy-path test passed independently: 1 passed in 0.10 s.
- The complete deterministic acquisition suite passed after the change:
  31 passed in 0.11 s.
- Tests were run against this worktree through the existing project virtual
  environment with the worktree `src` directory explicitly selected for
  imports.

### CheapShark adapter TDD session (17:40-19:32)

- Created a dedicated `.venv` for the Codex worktree, installed the project in
  editable mode with development dependencies, and switched PyCharm to the
  worktree interpreter. Imports now resolve to this worktree rather than the
  original checkout.
- Added and completed a redirect scenario that preserves the original full
  `requested_url` while recording the redirected response URL as `final_url`.
  The requested URL is prepared from the fixed endpoint and `id` params without
  performing a network request.
- Added strict runtime validation for `game_id`: only the exact built-in `int`
  type is accepted, so strings and boolean values cannot silently enter the API
  request boundary. Invalid types raise `TypeError` before acquisition starts
  or the HTTP session is called.
- Added deterministic timeout handling with a no-response test double and
  `AcquisitionFailureOutcome.TIMEOUT`.
- Added deterministic connection-error handling with a no-response test double
  and `AcquisitionFailureOutcome.NETWORK_ERROR`.
- Introduced and reused a narrow `_build_failure` helper for shared HTTP failure
  DTO construction, including timestamps and optional response metadata.
- Applied a green refactor for clearer helper parameter names, formatting,
  imports, and test signatures without changing behaviour.
- Reviewed duplication between `RequestsAcquirer` and
  `CheapSharkApiAcquirer`. Decided to finish the concrete CheapShark contract
  before extracting common HTTP machinery. Composition is preferred over an
  inheritance-heavy template if a shared transport boundary is later
  justified.

### Final verification for 2026-08-10

- The complete deterministic acquisition suite passed after the timeout and
  connection-error slices: 35 passed in 0.12 s.
- `git diff --check` passed.
- No live CheapShark network request was used by the unit tests.

### Next small step

Continue the `CheapSharkApiAcquirer` with the general
`RequestException -> REQUEST_ERROR` scenario, including the decision about
preserving response metadata when an exception contains a response. Then cover
redirect-limit failures, non-2xx HTTP outcomes, JSON media type, blank or
malformed JSON, and `429` rate limiting with `Retry-After` metadata. Do not
extract shared HTTP machinery until the concrete CheapShark contract is stable
enough to compare with `RequestsAcquirer`.

## 2026-08-11

### Time

- First work window: 08:41-11:02 Europe/Warsaw (2 h 21 min).
- Estimated focused development time for the day so far: 2 h 21 min.
- Main area: completing the CheapShark HTTP/JSON acquisition contract.

### Completed

- Added `TooManyRedirects` handling before the general `RequestException`
  fallback so the exception hierarchy preserves the intended outcome.
- Covered redirect-limit failures both with response metadata and without an
  available response. Both are classified as `HTTP_ERROR`.
- Covered general `RequestException` both with and without response metadata.
  Both are classified as `REQUEST_ERROR`.
- Added non-2xx response classification as `HTTP_ERROR`, parameterized for 403
  and 503 responses. Content parsing does not run after an HTTP status failure.
- Added `UNEXPECTED_CONTENT` handling for a missing Content-Type header, an
  unsupported media type, and a blank response body.
- Normalized JSON media types using the part before the first semicolon,
  whitespace trimming, and case-insensitive comparison. Tests cover plain JSON,
  charset parameters, and case variants.
- Added syntactic JSON validation with `json.loads` and specific handling of
  `JSONDecodeError` while preserving the original JSON text in the acquisition
  success DTO.
- Added an explicit contract test showing that syntactically valid JSON without
  CheapShark `info` or `deals` is still an acquisition success. Expected game
  fields remain the responsibility of extraction.
- Corrected copy/paste mistakes where tests selected the wrong exception session
  and where a parameterized Content-Type value was not used by the fixture.

### Decisions and boundaries

- HTTP 429 means `Too Many Requests`, not `TooManyRedirects`. It is an ordinary
  non-2xx response and remains `HTTP_ERROR`.
- `CheapSharkApiAcquirer` will not sleep or retry automatically. A future
  orchestrator may decide retry policy using captured acquisition metadata.
- Extend `AcquisitionFailure` with an optional
  `retry_after_seconds: int | None` field rather than hiding the server hint in
  a diagnostic message.
- For a valid numeric CheapShark `Retry-After` header, store the number of
  seconds. If the header is missing, empty, or invalid, keep the optional field
  as `None` without masking the primary 429 failure.

### Verification evidence

- The deterministic acquisition suite currently passes: 49 tests.
- `git diff --check` passes.
- No live CheapShark request is used by the unit tests.

### Next small step

After the break, start the 429 slice at the shared DTO boundary: add a model
test for optional `retry_after_seconds`, extend `AcquisitionFailure`, pass the
field through `_build_failure`, and then cover a CheapShark 429 response with a
numeric `Retry-After` header. Keep automatic retry outside the acquirer.

### Second work window

- Time: 11:28-13:37 Europe/Warsaw (2 h 09 min).
- Total focused development time for the day so far: 4 h 30 min.
- Added the optional `retry_after_seconds` field to `AcquisitionFailure` and
  protected its invariants: exact `int` values greater than or equal to zero
  are accepted; `None` means that no usable server hint is available.
- Added model coverage for default and explicit values, invalid types,
  booleans, and negative values.
- Implemented the CheapShark 429 branch without automatic retry. A numeric
  `Retry-After` response header is normalized from text to seconds and carried
  by the HTTP failure DTO.
- Worked through the `try`/`except` control flow: parsing determines the
  optional value, while one subsequent failure-builder call returns the 429
  result for both present and missing metadata.
- Final deterministic acquisition verification: 55 tests passed in 0.08 s.
- No live CheapShark network request was used by the tests.

### Third work window

- Time: 15:43-18:44 Europe/Warsaw (3 h 01 min elapsed).
- Total elapsed development time recorded for the day: 7 h 31 min.
- Starting point: complete the defensive `Retry-After` cases, then review the
  finished CheapShark acquisition contract before considering refactoring.
- Completed the CheapShark API acquisition vertical slice in checkpoint commit
  `dea3498` (`Add CheapShark API acquisition adapter`). Before the refactoring
  cycle began, the complete deterministic suite passed with 61 tests and
  `git diff --check` was clean.
- Audited four Git worktrees after development had become split between the
  primary checkout and detached Codex worktrees. Confirmed that `dea3498` is a
  direct descendant of `57531d9`, preserved all diagnostic and parsing work in
  a named stash, fast-forwarded the primary `main` branch to `dea3498`, and
  restored the unrelated uncommitted diagnostic files. A safety branch and the
  full stash remain available; old worktrees were not removed.
- Performed a read-only responsibility and duplication review of
  `RequestsAcquirer` and `CheapSharkApiAcquirer`. Chose composition through a
  narrow `HttpGetTransport` rather than an inheritance template or a universal
  configurable API client.
- Defined the internal transport boundary: a received HTTP response is
  represented by `HttpResponseSnapshot`; request-level failures remain
  `AcquisitionFailure`; the internal union is `HttpTransportResult`. The
  orchestrator continues to receive only the public `AcquisitionResult` from
  source adapters.
- Kept source semantics in adapters: CheapShark owns `game_id`, endpoint params,
  User-Agent construction, JSON acceptance, and current `Retry-After`
  normalization. The transport owns GET execution, query-string preparation,
  timestamps, response metadata, and classification of failures where no
  normal response is available.
- Added the initial snapshot contract test and the first transport happy-path
  test with a fake session and fake response. The TDD cycle intentionally ends
  red: the snapshot contract test passes, while the transport test reaches the
  planned `NotImplementedError`.

### Next small step

Before implementing transport behaviour, align the fake response with the real
`requests.Response.url` attribute, assert timestamp ordering, and make
`params` and `headers` keyword-only in `HttpGetTransport.get`. Then implement
only enough GET behaviour to make
`test_http_get_transport_returns_response_snapshot` pass; do not move non-2xx,
media-type, blank-body, JSON, or retry policy into the transport in that step.

## 2026-08-12

### Time

- First work window: 08:52-12:00 Europe/Warsaw (3 h 08 min elapsed).
- Main area: extracting the shared HTTP GET transport and defining the next
  adapter-migration boundary.

### Completed

- Implemented the internal `HttpResponseSnapshot` contract and a narrow
  `HttpGetTransport` happy path. The transport prepares the requested URL from
  the endpoint and query params, delegates URL, params, headers, and timeout to
  the injected session, and preserves response status, final URL, all headers,
  body text, and timezone-aware timestamps.
- Implemented shared request-level failure construction through the transport's
  private `_build_failure` helper.
- Moved deterministic classification of `Timeout`, `ConnectionError`,
  `TooManyRedirects`, and general `RequestException` into the transport.
  Redirect-limit and general request failures preserve response URL, status,
  and Content-Type when an exception contains a response, while keeping those
  fields `None` when no response is available.
- Refactored repeated timeout and connection-error assertions into a
  parameterized test with explicit `timeout` and `connection-error` case IDs.
  Added separate parameterized response/no-response coverage for redirect-limit
  and general request failures.
- Restored PyCharm code analysis by changing current-file inspection level from
  `Syntax` to `All Problems`.

### Verification evidence

- The focused transport suite passes: 8 tests.
- `git diff --check` passes.
- Test execution remains deterministic and does not perform live HTTP requests.

### Decisions and boundaries

- Any normally received HTTP response, including 429 and other non-2xx
  responses, is a transport-level success represented by
  `HttpResponseSnapshot`. Source adapters decide whether the snapshot becomes
  an acquisition success or failure.
- CheapShark-specific `Retry-After` normalization remains in
  `CheapSharkApiAcquirer`; the transport only preserves the complete response
  headers.
- `CheapSharkApiAcquirer` should receive an injected `HttpGetTransport` and its
  own User-Agent rather than continuing to own a session and timeout.
- CheapShark unit tests should use a `FakeHttpTransport` returning real
  `HttpResponseSnapshot` or `AcquisitionFailure` DTOs. They should not invoke
  the real transport or repeat low-level session exception tests.

### Next small step

After the break, design the smallest safe migration of the CheapShark happy
path: introduce a fake transport in its tests, convert the happy-path fixture
from `FakeResponse` to `HttpResponseSnapshot`, update the adapter constructor to
accept the transport and User-Agent, and replace direct session access with
`transport.get`. Keep JSON, status, content-type, blank-body, and 429 policy in
the adapter and migrate the remaining characterization tests in small groups.
