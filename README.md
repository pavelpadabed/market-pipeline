# Market Pipeline

An early-stage Python project for evaluating data-access strategies for marketplace price monitoring.

The current repository contains small diagnostic probes rather than a production scraper or a complete data pipeline. Their purpose is to determine whether a product page can be accessed through a regular HTTP request or requires a JavaScript-capable browser.

## Current scope

The first diagnostic target is a public product offer on Allegro.

Two access methods have been tested:

| Method | Result |
| --- | --- |
| `requests` with browser-like headers | HTTP `403`; product content was not returned |
| Playwright Chromium, headed mode | HTTP `200`; the product page rendered and the raw price was extracted |
| Playwright Chromium, headless mode | HTTP `403`; the probe classified the response and exited without waiting for unavailable product data |

These observations describe a small number of controlled tests against one offer. They do not establish long-term stability, an allowed request rate, or production suitability.

## Project structure

```text
Market Pipeline/
├── http_diagnostics/
│   ├── __init__.py
│   ├── requests_probe.py
│   └── playwright_probe.py
├── .gitignore
└── README.md
```

### `requests_probe.py`

Sends a direct HTTP request and reports:

- response status;
- final URL;
- content type;
- response body length;
- a short body preview.

### `playwright_probe.py`

Starts Chromium and reports:

- final URL;
- page title;
- main response status or failure verdict;
- cookie-consent action when the real product page is available;
- raw text from the price block.

The probe separates expected HTTP outcomes from browser errors:

- `if / elif / else` classifies the main response;
- `try / except` handles an optional cookie banner;
- `try / finally` guarantees browser cleanup.

## Requirements

The probes were developed with:

- Python `3.13.5`;
- Requests `2.34.2`;
- Playwright `1.61.0`;
- Chromium installed through Playwright.

## Local setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the Python dependencies and Chromium:

```bash
python -m pip install requests playwright
playwright install chromium
```

## Running the diagnostics

Run the direct HTTP probe:

```bash
python http_diagnostics/requests_probe.py \
  --url "https://example.com/product"
```

Run the Playwright probe:

```bash
python http_diagnostics/playwright_probe.py \
  --url "https://example.com/product"
```

Both commands require `--url`. Run either script with `--help` to view its CLI usage without making a network request.

The browser mode is currently selected in `playwright_probe.py`:

```python
browser = pw.chromium.launch(headless=True)
```

Use `headless=False` only for an explicit headed diagnostic run. Changing the browser mode may change the response returned by a website.

## Interpretation

A successful navigation status does not by itself prove that the expected product page was returned. Diagnostic code should also verify page identity, expected content, and required fields.

Likewise, an HTTP `403` is useful data rather than an unexpected Python failure. The probe records the outcome and avoids waiting for locators that cannot exist on a blocked response.

## Responsible use

This repository is intended for learning and technical feasibility assessment.

Before automating data collection from any website:

- review the website's current terms of service and robots policies;
- prefer an official API, partner feed, or written permission;
- avoid excessive traffic;
- do not implement CAPTCHA bypass, fingerprint spoofing, stealth plugins, proxy rotation, or other protection-evasion techniques;
- do not commit credentials, cookies, browser storage state, tokens, or customer data.

The current Allegro results demonstrate technical behavior only. They do not grant permission for commercial automated collection.

## Possible next steps

Further work depends on confirmed business requirements and authorized data access. Potential next steps include:

1. move target URLs from source code into configuration;
2. return structured diagnostic results instead of console-only output;
3. capture timestamps and limited failure artifacts;
4. add tests for response classification and parsing;
5. evaluate additional sources with the least expensive method first;
6. design normalization, comparison, currency conversion, and export stages only after source access is validated.
