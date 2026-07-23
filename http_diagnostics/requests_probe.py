import argparse

import requests

parser = argparse.ArgumentParser(
    description="Diagnose access to a product URL"
)

parser.add_argument(
    "--url",
    required=True,
    help="Product page URL to diagnose"
)
args = parser.parse_args()
url = args.url

headers = {

    "User-Agent": (

        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "

        "AppleWebKit/537.36 (KHTML, like Gecko) "

        "Chrome/138.0.0.0 Safari/537.36"

    ),

    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",

}

response = requests.get(url, headers=headers, timeout=15)
print(f"Status: {response.status_code}")
print(f"Final URL: {response.url}")
print(f"Content type: {response.headers.get('Content-Type')}")
print(f"Body length: {len(response.text)}")
print("Body preview:")

print(response.text[:500])
