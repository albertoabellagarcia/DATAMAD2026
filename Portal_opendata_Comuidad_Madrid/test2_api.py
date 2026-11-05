#!/usr/bin/env python3
"""
Download the full dataset "Afiliados a la Seguridad Social en alta laboral
(media mensual) por sexo y edad - Comunidad de Madrid" as a single JSON file.

Strategy (stops at the first one that works):
  1. CKAN: find the dataset that owns the resource and download its JSON
     resource directly, if one is published.
  2. CKAN datastore: page through all records with limit/offset.
  3. API gateway (apiscm.comunidad.madrid): page through with limit/offset.

Requirements: pip install requests
"""

import json
import sys
import requests

RESOURCE_ID = "f809ef2a-8385-43a5-87c6-c079d217a658"
OUTPUT_FILE = (
    "api_extraccionesafiliados-a-la-seguridad-social-en-alta-laboral-"
    "media-mensual-por-sexo-y-edad.-comu.json"
)

CKAN_BASES = [
    "https://datos.comunidad.madrid/api/3/action",
    "https://datos.comunidad.madrid/catalogo/api/3/action",
]
GATEWAY_URL = (
    "https://apiscm.comunidad.madrid/t/ciudadanos.comunidad.madrid/"
    "sector-publico/catalogo-unificado/v1/recursos/"
    f"{RESOURCE_ID}/datos"
)

PAGE_SIZE = 5000
TIMEOUT = 60
session = requests.Session()
session.headers.update({"User-Agent": "datos-abiertos-downloader/1.0"})


def save(records):
    """Write all records to one JSON file (UTF-8, readable accents)."""
    clean = [
        {k: v for k, v in r.items() if k != "_id"} if isinstance(r, dict) else r
        for r in records
    ]
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(clean)} records to {OUTPUT_FILE}")


def ckan_get(base, action, **params):
    try:
        r = session.get(f"{base}/{action}", params=params, timeout=TIMEOUT)
        data = r.json()
        return data["result"] if data.get("success") else None
    except (requests.RequestException, ValueError):
        return None


def extract_records(payload):
    """Pull the list of records out of a JSON response of unknown shape."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("records", "data", "datos", "items", "results", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                inner = extract_records(value)
                if inner:
                    return inner
    return None


# ---------------------------------------------------------------- strategy 1
def try_direct_json(base):
    resource = ckan_get(base, "resource_show", id=RESOURCE_ID)
    if not resource:
        return None
    package = ckan_get(base, "package_show", id=resource["package_id"])
    if not package:
        return None

    print(f"Dataset: {package.get('title')}")
    for res in package.get("resources", []):
        fmt = (res.get("format") or "").lower()
        url = res.get("url") or ""
        if fmt == "json" or url.lower().endswith(".json"):
            print(f"Found JSON resource: {url}")
            try:
                r = session.get(url, timeout=TIMEOUT)
                r.raise_for_status()
                records = extract_records(r.json())
                if records:
                    return records
            except (requests.RequestException, ValueError) as e:
                print(f"  Could not use it ({e}), trying next option")
    print("No downloadable JSON resource in the dataset.")
    return None


# ---------------------------------------------------------------- strategy 2
def try_datastore(base):
    records, offset, total = [], 0, None
    while True:
        result = ckan_get(base, "datastore_search",
                          resource_id=RESOURCE_ID,
                          limit=PAGE_SIZE, offset=offset)
        if result is None:
            return records or None
        batch = result.get("records", [])
        total = result.get("total", total)
        records.extend(batch)
        print(f"  datastore: {len(records)}/{total}")
        offset += PAGE_SIZE
        if not batch or (total is not None and len(records) >= total):
            return records


# ---------------------------------------------------------------- strategy 3
def try_gateway():
    records, offset = [], 0
    while True:
        try:
            r = session.get(GATEWAY_URL,
                            params={"limit": PAGE_SIZE, "offset": offset},
                            timeout=TIMEOUT)
            r.raise_for_status()
            batch = extract_records(r.json())
        except (requests.RequestException, ValueError) as e:
            print(f"  gateway error: {e}")
            return records or None
        if not batch:
            return records or None
        # Stop if the gateway ignores offset and keeps returning the same page
        if records and batch[0] == records[-len(batch)]:
            print("  gateway ignores paging parameters")
            return records
        records.extend(batch)
        print(f"  gateway: {len(records)} records")
        if len(batch) < PAGE_SIZE:
            return records
        offset += PAGE_SIZE


def main():
    for base in CKAN_BASES:
        print(f"\nTrying CKAN at {base}")
        records = try_direct_json(base)
        if records:
            return save(records)
        print("Trying datastore paging...")
        records = try_datastore(base)
        if records:
            return save(records)

    print("\nTrying API gateway...")
    records = try_gateway()
    if records:
        return save(records)

    sys.exit("Could not download the data from any source.")


if __name__ == "__main__":
    main()