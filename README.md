# Market Pipeline

Market Pipeline is an in-progress Python backend project for acquiring,
validating, normalizing, and persisting product-offer data from permitted
external sources.

The current vertical slice uses the public CheapShark REST API to demonstrate
explicit pipeline boundaries, typed success and failure contracts, partial
failure preservation, runtime validation with Pydantic, and PostgreSQL
persistence through SQLAlchemy 2.

The repository is under active development. It currently provides the tested
backend boundaries and persistence layer, but not yet a complete CLI, report
exporter, scheduler, or graphical interface.

## Implemented scope

```text
HTTP transport
    -> CheapShark acquisition adapters
    -> extraction
    -> Pydantic validation
    -> normalization
    -> PostgreSQL persistence
    -> current-offer and price-history queries
```

Implemented capabilities include:

- a shared HTTP GET transport with explicit handling of network and request
  failures;
- source-specific acquisition adapters for CheapShark game data and its store
  catalogue;
- typed acquisition success and failure DTOs with request provenance;
- JSON extraction with whole-response and per-deal failure modelling;
- strict Pydantic validation for game metadata, deal prices, and store catalogue
  records;
- normalization of validated prices to `Decimal` while preserving prior-stage
  failures;
- SQLAlchemy 2 models for source products, logical offers, pipeline runs,
  observations, and processing failures;
- PostgreSQL-backed writing with reuse of stable business identities;
- queries for current offers from the latest run and chronological offer-price
  history;
- deterministic unit tests and PostgreSQL integration tests.

## Architecture

Each stage has an explicit input and result contract. A successful transport
request does not imply successful extraction, and successful extraction does
not imply valid business data.

```text
AcquisitionResult
    -> CheapSharkExtractionResult
    -> CheapSharkValidationResult
    -> CheapSharkNormalizationSuccess
    -> persistence input DTOs
    -> PostgreSQL
```

The implementation deliberately preserves provenance and partial failures.
For example, one malformed deal does not discard valid deals returned in the
same response. Persistence models are also kept separate from boundary DTOs so
that external API contracts do not leak into the database model.

The original MVP design baseline is documented in
[`docs/architecture.md`](docs/architecture.md). Implementation evidence has
since narrowed the first source to CheapShark and moved PostgreSQL persistence
ahead of report export; this README describes the current repository state.

## Technology stack

- Python 3.13+
- Requests
- Pydantic 2
- SQLAlchemy 2
- PostgreSQL with Psycopg 3
- Pytest
- Playwright for controlled browser diagnostics only
- `uv` for dependency locking and project commands

## Project structure

```text
src/market_pipeline/
├── acquisition/      # HTTP transport and source acquisition adapters
├── extraction/       # CheapShark response-shape extraction
├── validation/       # Pydantic boundary models and validators
├── normalization/    # trusted normalized offer values
└── persistence/      # SQLAlchemy models, writer, and queries

tests/
├── acquisition/
├── extraction/
├── validation/
├── normalization/
└── persistence/

http_diagnostics/     # early HTTP and Playwright feasibility probes
docs/                 # architecture documentation
```

## Local setup

Requirements:

- Python 3.13 or newer;
- `uv`;
- PostgreSQL for integration tests.

Create the environment and install the locked dependencies:

```bash
uv sync
```

Run the deterministic test suite without PostgreSQL integration tests:

```bash
uv run pytest -m "not integration"
```

## PostgreSQL integration tests

Integration tests require a dedicated local database named
`market_pipeline_test`. The test fixture verifies the database name before
creating the schema and rolls individual test changes back.

Create the test database with PostgreSQL tooling appropriate for your system,
then run:

```bash
MARKET_PIPELINE_TEST_DATABASE_URL="postgresql+psycopg:///market_pipeline_test" \
  uv run pytest tests/persistence -m integration
```

Do not point this variable at a development or production database.

## Current development direction

The next narrow vertical slice is the presentation and output boundary:

1. map persisted current-offer query DTOs and the validated CheapShark store
   catalogue into user-facing report rows;
2. export those rows to an `.xlsx` report;
3. add a small application use case and CLI entry point without coupling the
   pipeline core to the interface.

GUI, scheduling, concurrency, automatic product matching, currency conversion,
and additional marketplace adapters remain future candidates rather than
current commitments.

## Responsible use

This project prefers official APIs, feeds, or explicit permission over browser
automation. It does not implement CAPTCHA bypass, fingerprint spoofing, stealth
plugins, proxy rotation, credential misuse, or other protection-evasion
techniques.

Live network and browser diagnostics are kept separate from deterministic unit
tests. Credentials, cookies, browser state, tokens, customer data, local
environment files, and development journals must not be committed.

## Project status

Active development. The repository is published as an engineering portfolio
project and a record of an evolving backend system; it is not yet a packaged
end-user application.

## License

No open-source license is currently granted. The source is publicly available
for review, but reuse and redistribution are not permitted unless a license is
added later.
