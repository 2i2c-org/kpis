# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.17.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# Download HubSpot deals data and cache it locally.
#
# This mirrors the data pulled by the `deals-gantt` dashboards so our notebooks
# can run purely from cached JSON instead of hitting the HubSpot API directly.
# To refresh the cache, run:
#     python book/scripts/download_hubspot_data.py [--force]
# Requires HUBSPOT_ACCESS_TOKEN (or HUBSPOT_TOKEN) in the environment.

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import requests
from dotenv import load_dotenv

try:
    from hubspot import HubSpot
    from hubspot.crm.deals import ApiException
except ImportError:
    HubSpot = None  # Optional dependency for nicer pagination


PROPERTIES: List[str] = [
    "dealname",
    "amount",
    "closedate",
    "dealstage",
    "contract_start_date",
    "contract_end_date",
    "hs_mrr",
    "hs_arr",
    "target_start_date",
    "target_end_date",
    "hs_forecast_probability",
    "hs_projected_amount",
]
DEFAULT_MAX_AGE_HOURS = 12


def cache_is_fresh(path: Path, max_age_hours: int) -> bool:
    """Return True if the file exists and is newer than max_age_hours."""
    if not path.exists():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < timedelta(hours=max_age_hours)


def load_token() -> str:
    """Return the HubSpot token from the environment."""
    token = os.environ.get("HUBSPOT_ACCESS_TOKEN") or os.environ.get("HUBSPOT_TOKEN")
    if not token:
        raise RuntimeError(
            "Missing HUBSPOT_ACCESS_TOKEN (or HUBSPOT_TOKEN). "
            "Add it to your environment or ~/.zshrc.local."
        )
    return token


def fetch_deals(token: str) -> Dict:
    """Fetch deals using the official HubSpot client if available, otherwise REST."""
    if HubSpot is not None:
        return fetch_deals_client(token)
    return fetch_deals_rest(token)


def fetch_deals_client(token: str) -> Dict:
    """Fetch all deals via hubspot-api-client (handles pagination)."""
    client = HubSpot(access_token=token)
    try:
        deals = client.crm.deals.get_all(properties=PROPERTIES)
    except ApiException as err:
        raise RuntimeError(f"HubSpot client error: {err}") from err

    # Convert datetimes to ISO strings so JSON serialization succeeds
    raw_results = [deal.to_dict() for deal in deals]
    results = json.loads(json.dumps(raw_results, default=str))
    return {
        "results": results,
        "meta": {
            "total": len(results),
            "fetched_at": datetime.utcnow().isoformat(),
            "properties": PROPERTIES,
            "pages": 1,
            "source": "hubspot-api-client",
        },
    }


def fetch_deals_rest(token: str) -> Dict:
    """Fetch all deals from HubSpot with pagination."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    params = {
        "limit": 100,
        "properties": ",".join(PROPERTIES),
    }
    url = "https://api.hubapi.com/crm/v3/objects/deals"

    results = []
    after = None
    page = 1

    while True:
        if after:
            params["after"] = after
        elif "after" in params:
            params.pop("after")

        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(
                f"HubSpot API error {response.status_code}: {response.text}"
            )

        data = response.json()
        results.extend(data.get("results", []))

        paging = data.get("paging", {}).get("next", {})
        after = paging.get("after")
        if not after:
            break
        page += 1

    return {
        "results": results,
        "meta": {
            "total": len(results),
            "fetched_at": datetime.utcnow().isoformat(),
            "properties": PROPERTIES,
            "pages": page,
        },
    }


def main(force: bool, max_age_hours: int) -> None:
    load_dotenv(override=False)
    out_path = Path(__file__).resolve().parent / "../data/hubspot-deals.json"
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not force and cache_is_fresh(out_path, max_age_hours):
        print(f"Cache is fresh (<{max_age_hours}h); using existing file at {out_path}")
        return

    token = load_token()
    print("Fetching deals from HubSpot...")
    payload = fetch_deals(token)
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {payload['meta']['total']} deals to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download HubSpot deals data to book/data/hubspot-deals.json"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore cache age and force a fresh download.",
    )
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=DEFAULT_MAX_AGE_HOURS,
        help="Refresh cache if older than this many hours (default: %(default)s).",
    )
    args = parser.parse_args()
    main(force=args.force, max_age_hours=args.max_age_hours)
