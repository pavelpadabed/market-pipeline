# Product Data Pipeline Architecture

## Status

This document records the current MVP baseline. It is a living engineering
decision, not a complete product specification. It should change when product
discovery or implementation provides better evidence.

## Product hypothesis

An operator needs to collect offers for the same product from several supported
public or otherwise permitted sources and receive a normalized, comparable
dataset without copying prices and seller information manually.

The MVP tests whether a small product-data pipeline can turn a limited set of
product URLs into useful offer observations and an explicit failure report.

## MVP user

The initial user is an operator who:

- knows which product should be compared;
- provides the product URLs;
- understands the resulting table;
- does not need a public self-service SaaS interface yet.

The operator may initially be the developer, a product analyst, an online-shop
owner, a purchasing specialist, or an early pilot customer.

## MVP scenario

One run represents one target product selected by the operator.

The operator provides between one and ten URLs for that product. The URLs must
belong to explicitly supported sources. A source page may contain zero, one, or
many seller offers.

The pipeline:

1. acquires source content;
2. verifies the response and expected page identity;
3. extracts raw product and offer values;
4. validates and normalizes the extracted values;
5. persists the run, valid observations, and failures;
6. exports valid observations as CSV and JSON;
7. reports whether enough valid observations exist for comparison.

```text
1 target product
    -> 1-10 input URLs
    -> 0-N source pages
    -> 0-N seller offers
    -> validated OfferObservation records
    -> CSV / JSON + failure report
```

The operator declares that the input URLs refer to the same target product.
Automatic product matching across sources is outside the MVP.

## Terminology

- **Source**: the platform from which data is acquired, for example Ceneo.
- **Product**: the target item selected by the operator.
- **Seller**: the merchant presenting an offer through a source.
- **Offer**: a seller-specific commercial proposal for a product.
- **Offer observation**: an offer as observed during one run at a particular
  time.

One product page can produce several offer observations when it lists offers
from several sellers.

## Minimum normalized observation

The primary business result is `OfferObservation`, with these baseline fields:

| Field | Meaning |
| --- | --- |
| `source` | Supported platform identifier |
| `source_product_id` | Product identifier on the source |
| `source_offer_id` | Offer identifier on the source, when available |
| `requested_url` | URL supplied by the operator |
| `product_title` | Product title extracted from the source |
| `seller_name` | Seller presenting the offer |
| `seller_url` | Seller or offer URL, when available |
| `price_amount` | Normalized numeric price |
| `currency` | Currency code such as `PLN` |
| `observed_at` | Time at which the offer was observed |

Technical acquisition and processing metadata is recorded separately from the
business observation. It may include:

- acquisition method (`http` or `browser`);
- response status and final URL;
- parser version;
- processing outcome;
- error code and error message.

Boundary, domain, persistence, and export models may share fields, but they do
not have to be represented by one class. Pydantic models validate runtime data;
Django ORM models represent persisted state; Pyright checks static type usage.

## Success semantics

Completing the processing steps does not prove that a run produced enough data
for a useful comparison. Technical processing evidence and business success are
therefore recorded separately.

A valid comparison requires at least two comparable offer observations:

- both observations passed validation;
- both contain `price_amount`, `currency`, and `seller_name`;
- both belong to the operator-declared target product;
- their currencies are directly comparable in the MVP;
- they represent distinct offers, preferably from different sellers.

Currency conversion is outside the MVP. Observations with different currencies
may be exported, but do not satisfy the minimum comparison criterion.

### Run status

| Status | Meaning |
| --- | --- |
| `pending` | The run has been accepted but not started |
| `running` | At least one input is being processed |
| `completed` | Processing has ended and at least two comparable observations exist |
| `partially_completed` | Processing has ended and at least one valid observation exists, but the comparison criterion is not satisfied or some inputs failed |
| `failed` | Processing has ended without any valid offer observation |

A run may be `completed` even when some URLs fail, provided that at least two
comparable observations remain. The failure report must preserve every partial
failure rather than hiding it behind the successful run status.

The run summary should include at least:

- number of submitted URLs;
- number of processed URLs;
- number of successful and failed URLs;
- number of extracted offers;
- number of valid and invalid observations;
- whether comparison is available.

### Input outcome categories

The initial outcome vocabulary is:

- `success`;
- `unsupported_source`;
- `timeout`;
- `http_error`;
- `blocked`;
- `unexpected_content`;
- `no_offers_found`;
- `extraction_failed`;
- `validation_failed`.

The vocabulary may be refined when implementation reveals distinct failure
handling requirements.

## Sources and acquisition

The MVP targets two explicitly supported sources, not arbitrary websites.

Ceneo is the first prototype source because the existing diagnostic work has
identified product IDs, offer IDs, sellers, prices, and multiple offers on one
page. The second source is not selected yet.

Support for a source requires both technical feasibility and an acceptable form
of access. Official APIs, feeds, or written permission are preferred. A working
HTTP or browser probe does not by itself authorize commercial automated
collection.

HTTP is the preferred acquisition method when it reliably returns the permitted
content. Browser acquisition is used only when a permitted source genuinely
requires JavaScript execution. Source-specific extraction rules must not leak
into validation, normalization, persistence, or export logic.

## MVP output

The operator receives:

1. CSV containing valid normalized offer observations;
2. JSON containing observations and processing metadata;
3. an explicit report for failed URLs and invalid offers;
4. a run summary and comparison-availability result.

Partial failures do not discard valid observations.

## Constraints and non-goals

The MVP has these initial constraints:

- one target product per run;
- one to ten URLs per run;
- two explicitly supported sources;
- public or otherwise permitted source access only;
- no guarantee of support for arbitrary websites;
- no automatic matching of products across sources;
- no currency conversion;
- no separately normalized product variants;
- no authenticated user accounts or stored website credentials;
- no CAPTCHA bypass, fingerprint spoofing, proxy rotation, stealth plugins, or
  other protection-evasion techniques;
- no periodic scheduling, alerts, or automatic price monitoring;
- no user-defined CSS selector framework;
- no universal plugin framework designed in advance.

## Future candidates, not MVP commitments

Potential future capabilities include:

- several target products in one batch using an operator-supplied product key;
- authenticated acquisition with explicit permission and secure secret storage;
- scheduled runs, retries, price history, and notifications;
- currency conversion;
- product variant modelling;
- additional normalized fields such as availability, delivery cost, original
  price, promotional price, condition, and seller rating;
- automatic or assisted product matching;
- additional source adapters and export formats.

Each candidate requires a concrete user scenario before adoption.

## Architecture guardrails

- Implement the smallest end-to-end slice before generalizing it.
- Add abstractions at confirmed variation points, especially acquisition method
  and source-specific extraction.
- Let each processing stage have an explicit input, output, and failure model.
- Prefer producing new validated values over mutating one shared pipeline object.
- Keep deterministic validation and normalization independent from network and
  browser code.
- Keep browser/network tests separate from deterministic unit tests.
- Treat partial failure as business-visible data.
- Introduce concurrency only after a correct single-input and sequential batch
  flow exists and has been measured.
- Do not add Django, PostgreSQL, or a background worker to a stage merely to
  demonstrate a technology; integrate each one where the vertical slice needs
  its responsibility.

## Planned implementation sequence

1. Define a structured acquisition result for one URL.
2. Implement and test HTTP outcome classification.
3. Define extraction results for the first source.
4. Define Pydantic validation contracts and normalized offer observations.
5. Process a small sequential batch while preserving partial failures.
6. Add CSV/JSON export and deterministic tests.
7. Persist runs, observations, and failures in PostgreSQL.
8. Add a narrow Django operator workflow.
9. Measure the flow before deciding on concurrency, background execution, or
   scheduling.

The first implementation task is the acquisition boundary for one URL. Its
contract must represent successful content, redirects, timeouts, blocked or
other HTTP errors, and unexpected content without relying on console output.
