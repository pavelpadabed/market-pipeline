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

### Second work window

- Time: 13:20-15:55 Europe/Warsaw (2 h 35 min elapsed).
- Total elapsed development time recorded for the day: 5 h 43 min.
- Migrated `CheapSharkApiAcquirer` from direct session and timeout ownership to
  an injected `HttpGetTransport` plus its source-specific User-Agent.
- Added a guard clause that returns transport-level `AcquisitionFailure`
  objects unchanged. Replaced six duplicated CheapShark exception scenarios
  with one delegation test that verifies object identity; low-level exception
  classification remains covered by the transport suite.
- Preserved transport timestamps in both acquisition success and
  response-policy failures instead of creating a second timing interval inside
  the adapter.
- Migrated all CheapShark characterization tests from fake sessions and fake
  responses to `FakeHttpTransport` with real `HttpResponseSnapshot` or
  `AcquisitionFailure` DTOs.
- Kept response-level policy in the source adapter: non-2xx classification,
  JSON Content-Type handling, blank-body rejection, syntactic JSON validation,
  valid JSON without expected game fields, and numeric `Retry-After`
  normalization for 429 responses.
- Removed the now-unused CheapShark session-level test doubles and requests
  exception imports.
- Created checkpoint commit `7099f8f`
  (`refactor: extract HTTP transport for CheapShark acquisition`) containing
  only the transport, CheapShark adapter, their tests, and this journal. Pavel
  pushed `main`; local `main` and `origin/main` now point to `7099f8f`.

### Final verification for 2026-08-12

- The complete deterministic suite passed before the checkpoint commit:
  64 tests passed.
- The focused CheapShark and transport suites passed after the test migration:
  29 tests passed.
- `git diff --check` passed.
- Diagnostic and parsing work remains deliberately uncommitted and outside the
  checkpoint scope.

### Next small step

Continue the shared-transport refactor by migrating `RequestsAcquirer` to an
injected `HttpGetTransport`. Preserve its HTML-specific response policy and
public `AcquisitionResult` behaviour, replace duplicated session exception
tests with transport-failure delegation coverage, and use the existing suite as
a characterization safety net. Re-run the complete deterministic suite before
the next checkpoint.

## 2026-08-13

### Time

- Work session: 08:55-11:53 Europe/Warsaw (2 h 58 min elapsed).
- Main areas: completing the acquisition checkpoint review and beginning the
  CheapShark extraction boundary.

### Completed

- Completed the shared HTTP transport refactor by migrating
  `RequestsAcquirer` from direct session and timeout ownership to an injected
  `HttpGetTransport`.
- Added the same transport-failure guard used by the CheapShark adapter:
  request-level `AcquisitionFailure` objects are returned unchanged, while
  received `HttpResponseSnapshot` objects continue through the adapter's HTML
  response policy.
- Preserved the transport's `started_at` and `finished_at` timestamps in every
  adapter-created success and failure result.
- Kept Requests-specific policy in the adapter: non-2xx classification,
  required HTML Content-Type validation, charset and case-insensitive media-type
  acceptance, and blank-body rejection.
- Migrated the Requests characterization tests from fake sessions and fake
  responses to `FakeHttpTransport` with real `HttpResponseSnapshot` or
  `AcquisitionFailure` DTOs.
- Removed duplicated timeout, connection, redirect, and request-exception tests
  from the adapter suite. Their classification remains covered at the shared
  transport boundary; one adapter test verifies unchanged failure delegation.
- Created checkpoint commit `f672914`
  (`refactor: migrate Requests acquirer to HTTP transport`) containing only the
  Requests adapter and its tests. Diagnostic and parsing work remained outside
  the commit.

### Verification evidence

- The focused Requests adapter suite passed: 9 tests.
- The complete deterministic suite passed: 59 tests.
- `git diff --check` passed before the checkpoint commit.

### Current checkpoint

- Both current HTTP acquisition adapters now compose the same narrow
  `HttpGetTransport` and retain only their source- or representation-specific
  response policy.
- The acquisition bundle is a candidate for completion for the current MVP.
  The next architecture review should confirm that no additional acquisition
  capability is required before work moves to the next pipeline area.
- `docs/developer-journal.md` remains the single chronological record of
  implementation sessions, decisions, verification evidence, and hand-off
  checkpoints; no parallel status document is maintained.

### Skills and portfolio evidence

- Integrated a third-party REST API in Python while keeping source-specific
  request and response policy inside a dedicated adapter.
- Designed immutable, typed success and failure contracts for an
  external-system boundary, including timestamps, redirects, response metadata,
  explicit failure outcomes, and optional rate-limit hints.
- Implemented a reusable HTTP GET transport that classifies timeout,
  connection, redirect-limit, and general request failures without leaking
  `requests.Response` objects across the acquisition boundary.
- Applied dependency injection and composition so that two concrete adapters
  share transport behaviour without an inheritance-heavy framework.
- Preserved separation of concerns: the transport owns request execution,
  adapters own representation and source policy, and future orchestration owns
  fallback and retry decisions.
- Used test-driven development and deterministic test doubles to cover HTTP,
  HTML, JSON, redirect, content-type, blank-body, malformed-content, and
  rate-limit scenarios without live network requests.
- Refactored duplicated HTTP behaviour only after comparison of two concrete
  adapters confirmed the shared point of variation.
- Verification evidence: 59 deterministic acquisition tests pass at checkpoint
  commit `f672914`; earlier acquisition milestones are recorded in commits
  `7e7fd93`, `57531d9`, `dea3498`, and `7099f8f`.

These statements support claims such as REST API integration, HTTP client
integration with Requests, typed boundary design, dependency injection,
composition, deterministic pytest testing, failure modelling, and rate-limit
metadata handling. They do not claim REST API design, distributed processing,
or production-scale API operations.

### CheapShark extraction design and initial DTO session

- Defined the boundary from `AcquisitionSuccess.content` through
  source-specific JSON extraction to raw candidates for a future Pydantic
  validation boundary. Extraction does not validate or normalize deal fields.
- Interpreted the CheapShark Game Lookup response as shared raw `info` metadata
  plus zero or more elements from `deals`; deliberately excluded
  `cheapestPriceEver` from the current MVP slice.
- Chose whole-response `CheapSharkExtractionSuccess | CheapSharkExtractionFailure`
  semantics, with per-deal candidate or failure results preserved inside a
  successful extraction. Empty `info`, empty `deals`, and empty deal mappings
  remain valid extraction shapes; internal business-field validation is deferred.
- Created the initial extraction package and immutable typed DTOs. Added
  deterministic model tests for accepting an empty raw mapping and rejecting
  non-mapping deal candidates with parameterized invalid inputs.
- Added the first green contract test for `CheapSharkExtractionFailure`,
  preserving acquisition context, an explicit outcome, and a diagnostic message.
- Development paused when attention began to decline. The next session should
  resume with a small reviewable test rather than extending the extraction
  architecture in one step.
- Collaboration adjustment: Pavel wants to retain more ownership of architecture
  proposals. Codex should lead with focused questions and review Pavel's design
  before recommending a concrete contract.

### Verification evidence for the extraction session

- Pavel reported three parameterized deal-candidate model cases passing and the
  initial extraction-failure contract test passing in PyCharm.
- No full extraction or project suite run was recorded for this unfinished slice.

### Next small step

At the next rested session, review the initial extraction DTO diff and continue
with one small failure-contract test. Preserve Pavel's ownership of the design
by asking him to propose the next invariant before recommending implementation.

## 2026-08-14

### Time

- First work window: 08:18-09:29 Europe/Warsaw (1 h 11 min elapsed).
- Second work window: 10:15-12:29 Europe/Warsaw (2 h 14 min elapsed).
- Third work window: 17:33-19:22 Europe/Warsaw (1 h 49 min elapsed).
- Total elapsed work time recorded for the day: 5 h 14 min.
- Main areas: completing the initial CheapShark extraction result contracts and
  starting the extractor walking skeleton.

### Completed

- Completed the immutable raw deal candidate, per-deal extraction failure,
  whole-response extraction success, and whole-response extraction failure DTOs.
- Defined separate unions for one deal result and the complete extraction result.
- Protected deal-failure indexes against non-integer, boolean, and negative
  values, and protected both failure DTOs against blank diagnostic messages.
- Confirmed that empty game metadata and zero deal results form a valid
  extraction success; business-field validation remains deferred.
- Pavel independently designed the extractor API and control flow, then reviewed
  the proposal with Codex before implementation.
- Confirmed a dependency-free `CheapSharkExtractor.extract` boundary from
  `AcquisitionSuccess` to `CheapSharkExtractionResult`, with structural document
  failures and per-deal partial failures kept separate.
- Renamed the extraction model test module to remove the duplicate pytest module
  name and restored combined project collection.
- Implemented the first extractor walking skeleton: valid JSON with empty `info`
  and empty `deals` returns extraction success with preserved acquisition,
  empty metadata, and an empty deal-result tuple.
- Added the next red TDD test requiring two valid deal mappings to become
  `CheapSharkDealCandidate` objects in source order, then implemented one-pass
  candidate construction with a typed mutable buffer and immutable tuple result.
- Added partial-failure coverage with valid candidates around a non-mapping deal.
  The extractor now preserves source order, the malformed raw value, and its
  zero-based index without discarding neighbouring candidates.
- Added defensive invalid-JSON handling at the extraction boundary. Only
  `json.loads` is inside the `try` block, and `JSONDecodeError` becomes an
  explicit `INVALID_JSON` extraction failure preserving the acquisition object.

### Verification evidence

- The focused extraction model suite passed: 15 tests.
- After resolving the module-name collision, the combined deterministic suite
  passed at the walking-skeleton checkpoint: 75 tests passed in 0.12 s.
- Final focused extractor verification for the day: 4 tests passed in 0.01 s.
- Final combined deterministic verification for the day: 78 tests passed in
  0.12 s.
- `git diff --check` passed for the extraction models, tests, and journal.

### Next small step

Continue whole-response structural failures from the parsed JSON root, beginning
with `ROOT_NOT_MAPPING`. Add each outcome through its own red test and keep
Pydantic/business-field validation outside extraction.

## 2026-08-15

### Time

- Work window: 08:50-09:49 Europe/Warsaw (59 min elapsed).
- Main area: completing and auditing the CheapShark extraction slice.

### Completed

- Completed whole-response structural classification for a non-mapping JSON
  root, missing or non-mapping `info`, and missing or non-list `deals`.
- Used one private sentinel to distinguish a missing required key from a key
  whose present value is `null` or another invalid shape.
- Preserved empty `info` mappings and empty `deals` lists as successful raw
  extraction results rather than treating absence of offers as a parser error.
- Completed source-order candidate extraction and per-deal partial failures
  without discarding valid candidates around malformed list elements.
- Audited the production extractor, DTOs, type aliases, deterministic fixtures,
  failure outcomes, type narrowing, and boundary scope. Removed the final unused
  test import and normalized extraction test naming and formatting.
- Added the missing `HttpGetTransport` constructor annotation to the existing
  CheapShark acquisition adapter as a behaviour-neutral typing cleanup.

### Verification evidence

- The complete extraction suite passed: 24 tests.
- The complete deterministic project suite passed: 83 tests in 0.13 s.
- `git diff --check` passed for the extraction implementation, tests, and journal.
- Diagnostic and parsing work remains deliberately uncommitted and outside the
  extraction checkpoint scope.

### Skills and portfolio evidence

- Interpreted a third-party JSON document shape and translated it into an
  explicit source-specific extraction contract.
- Modelled whole-document failures separately from per-candidate failures while
  preserving partial results and source order.
- Applied immutable dataclasses, union type aliases, type narrowing, a typed
  mutable construction buffer, and tuple output at a boundary.
- Used a sentinel to distinguish a missing JSON key from a present invalid value.
- Built deterministic JSON fixtures and developed the slice through focused TDD
  cycles without network access.
- Kept raw extraction separate from future Pydantic validation and normalization.

These statements support claims such as JSON extraction, external schema
interpretation, partial-failure modelling, typed boundary design, and
deterministic pytest testing. They do not claim general API schema design,
streaming JSON processing, or production-scale data ingestion.

### Next small step

Define the next Pydantic validation boundary from successful raw CheapShark game
metadata and deal candidates to validated source DTOs. Do not add a generic
extractor protocol until a second concrete source provides evidence for it.
