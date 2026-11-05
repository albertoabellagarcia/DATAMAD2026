#!/usr/bin/env python3
"""
Download the "Calidad del aire. Datos diarios" dataset from the
Comunidad de Madrid open data portal (CKAN) using its API.

Dataset page: https://datos.comunidad.madrid/dataset/calidad_aire_datos_dia

Two modes:
  files      (default) Download every resource file (CSV, JSON, XLS...) listed
             in the dataset metadata (CKAN action `package_show`).
  datastore  Pull the rows through the CKAN DataStore API (`datastore_search`),
             paginating, and save them as CSV. Only works for resources that
             have `datastore_active = true`.

Examples:
  python descargar_calidad_aire.py                       # all files -> ./calidad_aire
  python descargar_calidad_aire.py --format csv          # only CSV files
  python descargar_calidad_aire.py --list                # just list resources
  python descargar_calidad_aire.py --mode datastore      # rows via API -> CSV

Requires: pip install requests
"""

import argparse
import csv
import os
import re
import sys
import time
from urllib.parse import urlparse

import requests

PORTAL = "https://datos.comunidad.madrid"
DATASET_ID = "calidad_aire_datos_dia"
# The portal has exposed the CKAN API under both paths over time; try both.
API_CANDIDATES = [f"{PORTAL}/catalogo/api/3/action", f"{PORTAL}/api/3/action"]

session = requests.Session()
session.headers["User-Agent"] = "calidad-aire-downloader/1.0 (python-requests)"


def ckan_call(base, action, retries=3, **params):
    """Call a CKAN action and return its `result`, with simple retries."""
    url = f"{base}/{action}"
    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, params=params, timeout=60)
            r.raise_for_status()
            data = r.json()
            if not data.get("success"):
                raise RuntimeError(f"CKAN error: {data.get('error')}")
            return data["result"]
        except (requests.RequestException, ValueError) as e:
            if attempt == retries:
                raise
            print(f"  retry {attempt}/{retries} for {action}: {e}", file=sys.stderr)
            time.sleep(2 * attempt)


def find_api_base():
    for base in API_CANDIDATES:
        try:
            ckan_call(base, "package_show", retries=1, id=DATASET_ID)
            return base
        except Exception:
            continue
    sys.exit("Could not reach the CKAN API at: " + ", ".join(API_CANDIDATES))


def safe_name(text):
    return re.sub(r"[^\w.\-]+", "_", text, flags=re.UNICODE).strip("_")[:150]


def filename_for(res):
    path_name = os.path.basename(urlparse(res.get("url", "")).path)
    if path_name and "." in path_name:
        return safe_name(path_name)
    ext = (res.get("format") or "dat").lower()
    return f"{safe_name(res.get('name') or res['id'])}.{ext}"


def download_file(url, dest, overwrite=False):
    if os.path.exists(dest) and not overwrite:
        print(f"  skip (exists): {dest}")
        return
    tmp = dest + ".part"
    with session.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        done = 0
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  {done/1e6:8.1f} / {total/1e6:.1f} MB", end="")
        print()
    os.replace(tmp, dest)
    print(f"  saved: {dest}")


def download_datastore(base, res, dest, page_size=32000):
    """Fetch all rows of a DataStore resource with pagination and write CSV."""
    offset, writer, total = 0, None, None
    with open(dest, "w", newline="", encoding="utf-8") as f:
        while True:
            result = ckan_call(base, "datastore_search",
                               resource_id=res["id"], limit=page_size, offset=offset)
            if writer is None:
                fields = [fd["id"] for fd in result["fields"] if fd["id"] != "_id"]
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                total = result.get("total")
            records = result["records"]
            writer.writerows(records)
            offset += len(records)
            print(f"\r  rows: {offset}" + (f" / {total}" if total else ""), end="")
            if not records or (total is not None and offset >= total):
                break
    print(f"\n  saved: {dest}")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default="calidad_aire", help="output folder")
    p.add_argument("--mode", choices=["files", "datastore"], default="files")
    p.add_argument("--format", help="only resources of this format, e.g. csv, json, xlsx")
    p.add_argument("--list", action="store_true", help="list resources and exit")
    p.add_argument("--overwrite", action="store_true", help="re-download existing files")
    args = p.parse_args()

    base = find_api_base()
    print(f"API: {base}")
    pkg = ckan_call(base, "package_show", id=DATASET_ID)
    print(f"Dataset: {pkg.get('title')}  (last modified: {pkg.get('metadata_modified')})")

    resources = pkg.get("resources", [])
    if args.format:
        resources = [r for r in resources
                     if (r.get("format") or "").lower() == args.format.lower()]
    if args.mode == "datastore":
        resources = [r for r in resources if r.get("datastore_active")]

    print(f"{len(resources)} resource(s):")
    for r in resources:
        ds = " [datastore]" if r.get("datastore_active") else ""
        print(f"  - {r.get('name')} | {r.get('format')}{ds}\n    {r.get('url')}")
    if args.list or not resources:
        return

    os.makedirs(args.out, exist_ok=True)
    for r in resources:
        print(f"\n> {r.get('name')}")
        try:
            if args.mode == "files":
                download_file(r["url"], os.path.join(args.out, filename_for(r)), args.overwrite)
            else:
                dest = os.path.join(args.out, safe_name(r.get("name") or r["id"]) + "_datastore.csv")
                download_datastore(base, r, dest)
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()