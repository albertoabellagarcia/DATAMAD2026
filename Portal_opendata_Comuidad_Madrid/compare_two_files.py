#!/usr/bin/env python3
"""
Compare two JSON files with the dataset
"Afiliados a la Seguridad Social en alta laboral (media mensual) por sexo y edad".

Two comparisons are run, one after the other:

  1. NORMALISED comparison (content)
     Equivalent values count as equal: "1.234,5" == 1234.5, extra spaces,
     "" == null, upper/lower case in field names. Row order is ignored.
     Answers: "do both files contain the same information?"

  2. STRICT comparison (exact)
     Values are compared exactly as written, including their type:
     "1234" (text) != 1234 (integer) != 1234.0 (decimal), "Madrid" != "Madrid ",
     field names are case-sensitive. It also checks whether the records are
     in the same order and whether the two files are byte-for-byte identical.
     Answers: "are both files exactly the same?"

For each comparison it reports:
  - number of records
  - fields present in only one file
  - records present in only one file (order independent, duplicates counted)
  - for records sharing the same key, every field value that differs

A full report is saved to comparacion_resultado.json.
No external libraries needed.

Usage:
  python comparar_json.py                 # run both comparisons
  python comparar_json.py --solo-normal   # only the normalised comparison
  python comparar_json.py --solo-estricto # only the strict comparison
"""

import hashlib
import json
import re
import sys
from collections import Counter

# ---------------------------------------------------------------- settings
FILE_API = (
    "api_extraccionesafiliados-a-la-seguridad-social-en-alta-laboral-"
    "media-mensual-por-sexo-y-edad.-comu.json"
)
FILE_ORIGINAL = (
    "original_extraccionesafiliados-a-la-seguridad-social-en-alta-laboral-"
    "media-mensual-por-sexo-y-edad.-comu.json"
)
REPORT_FILE = "comparacion_resultado.json"

# Fields that identify a record (e.g. ["fecha", "sexo", "edad"]).
# Leave empty to detect them automatically.
KEY_FIELDS = []

# Fields ignored in the NORMALISED comparison (e.g. internal ids).
# The STRICT comparison never ignores any field.
IGNORE_FIELDS_NORMAL = {"_id"}

MAX_EXAMPLES = 20  # examples printed on screen per type of difference
# (the report file always contains ALL differences)


# ---------------------------------------------------------------- loading
def extract_records(payload):
    """Get the list of records from a JSON document of unknown shape."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("records", "data", "datos", "items", "results", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                inner = extract_records(value)
                if inner is not None:
                    return inner
    return None


def load(path):
    """Return (records, sha256 of the raw file bytes)."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        sys.exit(f"File not found: {path}")
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        sys.exit(f"Invalid JSON in {path}: {e}")
    records = extract_records(payload)
    if records is None:
        sys.exit(f"Could not find a list of records in {path}")
    non_dict = sum(1 for r in records if not isinstance(r, dict))
    if non_dict:
        print(f"Warning: {non_dict} entries in {path} are not objects; skipped.")
    records = [r for r in records if isinstance(r, dict)]
    return records, hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------- normalising
def normal_key(name):
    return str(name).strip().lower()


def normal_value(value):
    """Make equivalent values compare equal (normalised mode)."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 6)
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    text = str(value).strip()
    if text == "":
        return None
    # Read numbers written as 1234.5 or in Spanish format 1.234,5 / 1.234
    candidates = []
    if "," in text:
        candidates.append(text.replace(".", "").replace(",", "."))
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", text):
        candidates.append(text.replace(".", ""))  # 1.234 -> 1234
    candidates.append(text)
    for c in candidates:
        try:
            return round(float(c), 6)
        except ValueError:
            pass
    return " ".join(text.split())


def prepare_normal(records):
    return [
        {normal_key(k): normal_value(v)
         for k, v in r.items() if normal_key(k) not in IGNORE_FIELDS_NORMAL}
        for r in records
    ]


def prepare_strict(records):
    # Values stay exactly as loaded; nothing is renamed or ignored.
    return [dict(r) for r in records]


# ---------------------------------------------------------------- helpers
MISSING = "<<field missing>>"


def exact(value):
    """Type-aware text form: 1, 1.0, "1" and true are all different."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def signature(record, fields):
    return "[" + ",".join(
        exact(record[f]) if f in record else json.dumps(MISSING)
        for f in fields
    ) + "]"


def type_name(value):
    if value is None:
        return "null"
    return {bool: "boolean", int: "integer", float: "decimal",
            str: "text", list: "list", dict: "object"}.get(type(value), "other")


def detect_key_fields(a, b, fields):
    """Pick fields that look like identifiers and are unique in both files."""
    if KEY_FIELDS:
        wanted = {normal_key(k) for k in KEY_FIELDS}
        keys = [f for f in fields if normal_key(f) in wanted]
        return keys if len(keys) == len(wanted) else []

    hints = ("fecha", "año", "ano", "anio", "mes", "periodo", "edad",
             "sexo", "tramo", "grupo", "municipio", "codigo", "código")
    sample = a[:300] + b[:300]
    keys = []
    for f in fields:
        name = normal_key(f)
        looks_textual = any(isinstance(r.get(f), str) and
                            not _is_number_text(r.get(f)) for r in sample)
        if looks_textual or any(h in name for h in hints):
            keys.append(f)
    if not keys:
        return []
    for records in (a, b):
        sigs = [signature(r, keys) for r in records]
        if len(sigs) != len(set(sigs)):
            return []  # not unique: cannot match records one to one
    return keys


def _is_number_text(value):
    try:
        float(str(value).replace(".", "").replace(",", "."))
        return True
    except ValueError:
        return False


def show(title, items, limit=MAX_EXAMPLES):
    if not items:
        return
    print(f"\n  {title} (showing {min(limit, len(items))} of {len(items)})")
    for item in items[:limit]:
        print("    ", json.dumps(item, ensure_ascii=False))


# ---------------------------------------------------------------- comparison
def compare(api, orig, mode):
    """Run one comparison. mode is 'normalised' or 'strict'."""
    strict = mode == "strict"
    print("\n" + "=" * 78)
    print(f"{mode.upper()} COMPARISON")
    print("=" * 78)

    result = {"mode": mode}

    # --- record count
    print("\nRECORD COUNT")
    print(f"  API:      {len(api)}")
    print(f"  Original: {len(orig)}")
    result["records_api"] = len(api)
    result["records_original"] = len(orig)

    # --- fields
    fields_api = set().union(*api) if api else set()
    fields_orig = set().union(*orig) if orig else set()
    common = sorted(fields_api & fields_orig)
    only_api = sorted(fields_api - fields_orig)
    only_orig = sorted(fields_orig - fields_api)

    print("\nFIELDS")
    print(f"  Common:            {len(common)}")
    print(f"  Only in API:       {only_api or '-'}")
    print(f"  Only in original:  {only_orig or '-'}")
    result["fields_common"] = common
    result["fields_only_in_api"] = only_api
    result["fields_only_in_original"] = only_orig

    # Field order inside each record (strict only, informative)
    if strict and api and orig:
        order_api = list(api[0].keys())
        order_orig = list(orig[0].keys())
        same_field_order = order_api == order_orig
        result["same_field_order_first_record"] = same_field_order
        if not same_field_order:
            print("  Field order differs (first record):")
            print(f"    API:      {order_api}")
            print(f"    Original: {order_orig}")

    # In strict mode a record is compared on ALL its fields (a missing
    # field is a difference); in normalised mode only common fields count.
    fields = sorted(fields_api | fields_orig) if strict else common

    # --- whole-record matching (order independent, duplicates counted)
    count_api = Counter(signature(r, fields) for r in api)
    count_orig = Counter(signature(r, fields) for r in orig)
    missing_in_api = count_orig - count_api
    extra_in_api = count_api - count_orig
    identical = sum((count_api & count_orig).values())
    dup_api = sum(n - 1 for n in count_api.values() if n > 1)
    dup_orig = sum(n - 1 for n in count_orig.values() if n > 1)

    print("\nRECORDS" + (" (all fields)" if strict else " (common fields)"))
    print(f"  Identical in both:          {identical}")
    print(f"  In original, not in API:    {sum(missing_in_api.values())}")
    print(f"  In API, not in original:    {sum(extra_in_api.values())}")
    print(f"  Duplicate records in API:      {dup_api}")
    print(f"  Duplicate records in original: {dup_orig}")
    result.update(identical_records=identical,
                  duplicates_api=dup_api, duplicates_original=dup_orig)

    # --- row order (strict only)
    if strict:
        n = min(len(api), len(orig))
        first_diff = next((i for i in range(n)
                           if signature(api[i], fields) != signature(orig[i], fields)),
                          None)
        same_order = first_diff is None and len(api) == len(orig)
        result["same_row_order"] = same_order
        if same_order:
            print("  Row order:                  identical")
        elif first_diff is not None:
            print(f"  Row order:                  differs from record #{first_diff + 1}")
            result["first_row_position_that_differs"] = first_diff + 1
        else:
            print("  Row order:                  same up to the end of the shorter file")

    # --- key-based matching: explains WHICH values differ
    keys = detect_key_fields(api, orig, common)
    value_diffs = []
    if keys:
        print(f"\nKEY FIELDS used to match records: {keys}")
        idx_api = {signature(r, keys): r for r in api}
        idx_orig = {signature(r, keys): r for r in orig}
        only_keys_orig = sorted(set(idx_orig) - set(idx_api))
        only_keys_api = sorted(set(idx_api) - set(idx_orig))

        for k in sorted(set(idx_api) & set(idx_orig)):
            a, o = idx_api[k], idx_orig[k]
            for f in fields:
                if f in keys:
                    continue
                va, vo = a.get(f, MISSING), o.get(f, MISSING)
                if exact(va) != exact(vo):
                    diff = {"key": {kf: a[kf] for kf in keys},
                            "field": f, "api": va, "original": vo}
                    if strict:
                        diff["type_api"] = "missing" if va is MISSING else type_name(va)
                        diff["type_original"] = "missing" if vo is MISSING else type_name(vo)
                    value_diffs.append(diff)

        print(f"  Keys only in original:  {len(only_keys_orig)}")
        print(f"  Keys only in API:       {len(only_keys_api)}")
        print(f"  Value differences:      {len(value_diffs)}")

        result["key_fields"] = keys
        result["records_only_in_original"] = [idx_orig[k] for k in only_keys_orig]
        result["records_only_in_api"] = [idx_api[k] for k in only_keys_api]
        result["value_differences"] = value_diffs

        show("Records only in ORIGINAL", result["records_only_in_original"])
        show("Records only in API", result["records_only_in_api"])

        if value_diffs:
            print(f"\n  Value differences (showing {min(MAX_EXAMPLES, len(value_diffs))}"
                  f" of {len(value_diffs)})")
            for d in value_diffs[:MAX_EXAMPLES]:
                line = (f"    {json.dumps(d['key'], ensure_ascii=False)} | {d['field']}: "
                        f"API={d['api']!r}  original={d['original']!r}")
                if strict and d["type_api"] != d["type_original"]:
                    line += f"  [type: {d['type_api']} vs {d['type_original']}]"
                print(line)

            print("\n  Differences per field:")
            for f, n in Counter(d["field"] for d in value_diffs).most_common():
                print(f"    {f}: {n}")

            if strict:
                type_changes = Counter(
                    (d["field"], d["type_api"], d["type_original"])
                    for d in value_diffs if d["type_api"] != d["type_original"])
                if type_changes:
                    print("\n  Type differences (field: API type -> original type):")
                    for (f, ta, to), n in type_changes.most_common():
                        print(f"    {f}: {ta} -> {to}  ({n} records)")
    else:
        print("\n  No unique key fields found; listing unmatched records instead.")
        print("  (Set KEY_FIELDS at the top of the script for a field-by-field report.)")
        result["records_only_in_original"] = [
            json.loads(s) for s in missing_in_api.elements()]
        result["records_only_in_api"] = [
            json.loads(s) for s in extra_in_api.elements()]
        result["records_only_in_original"] = [
            dict(zip(fields, v)) for v in result["records_only_in_original"]]
        result["records_only_in_api"] = [
            dict(zip(fields, v)) for v in result["records_only_in_api"]]
        show("Records only in ORIGINAL", result["records_only_in_original"])
        show("Records only in API", result["records_only_in_api"])

    # --- verdict
    same = (not only_api and not only_orig
            and not missing_in_api and not extra_in_api)
    if strict:
        same = same and result.get("same_row_order", False)
    result["equal"] = same
    print(f"\n{mode.upper()} RESULT:",
          "EQUAL ✔" if same else "DIFFERENT ✘")
    return result


# ---------------------------------------------------------------- main
def main():
    args = set(sys.argv[1:])
    run_normal = "--solo-estricto" not in args
    run_strict = "--solo-normal" not in args

    raw_api, hash_api = load(FILE_API)
    raw_orig, hash_orig = load(FILE_ORIGINAL)

    report = {"api_file": FILE_API, "original_file": FILE_ORIGINAL,
              "sha256_api": hash_api, "sha256_original": hash_orig,
              "byte_identical": hash_api == hash_orig}

    print("=" * 78)
    print("FILES")
    print(f"  API:      {FILE_API}")
    print(f"  Original: {FILE_ORIGINAL}")
    print(f"  Byte-for-byte identical: {'YES' if hash_api == hash_orig else 'NO'}")

    if run_normal:
        report["normalised"] = compare(prepare_normal(raw_api),
                                       prepare_normal(raw_orig), "normalised")
    if run_strict:
        report["strict"] = compare(prepare_strict(raw_api),
                                   prepare_strict(raw_orig), "strict")

    # --- overall summary
    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print(f"  Byte-for-byte identical:     {'YES' if report['byte_identical'] else 'NO'}")
    if run_normal:
        print(f"  Same content (normalised):   "
              f"{'YES' if report['normalised']['equal'] else 'NO'}")
    if run_strict:
        print(f"  Exactly equal (strict):      "
              f"{'YES' if report['strict']['equal'] else 'NO'}")
    if run_normal and run_strict and report["normalised"]["equal"] \
            and not report["strict"]["equal"]:
        print("\n  -> The data is the same, but the format differs "
              "(types, spacing, field names or row order).")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nFull report saved to {REPORT_FILE}")


if __name__ == "__main__":
    main()