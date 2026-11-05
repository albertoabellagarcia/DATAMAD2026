#!/usr/bin/env python3
"""
pysmartdatamodels demo (DATAMAD 2026 · slides 48 and 49).

Part 1 · Explore the models (slide 48)
    list_all_subjects, datamodels_subject, attributes_datamodel,
    description_attribute, units_attribute
    + extras: datatype_attribute, ngsi_datatype_attribute, model_attribute,
      subject_for_datamodel, look_for_datamodel, datamodel_repolink,
      list_datamodel_metadata

Part 2 · Generate, validate and identify (slide 49)
    validate_data_model_schema, ngsi_ld_example_generator,
    ngsi_ld_keyvalue_example_generator, geojson_features_example_generator,
    identify_or_draft_datamodel

Part 3 · Try it: Madrid real-time traffic -> TrafficFlowObserved
    Converts measuring points from the Ayuntamiento de Madrid (output of
    trafico_madrid_tiempo_real.py, or a sample point) to the
    TrafficFlowObserved model and checks them with validate_payload.

Every result is saved in the folder sdm_salida/.

Usage:
  python smart_data_models_demo.py            # all parts
  python smart_data_models_demo.py 1          # only part 1 (also: 2, 3, "1 3"...)

Requirements: pip install pysmartdatamodels
Optional:     pip install pyproj   (adds location to the Madrid points)
Internet access is needed: the package reads schemas from GitHub.
"""

import glob
import json
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from pysmartdatamodels import pysmartdatamodels as sdm

# ---------------------------------------------------------------- settings
SUBJECT = "dataModel.Transportation"
DATAMODEL = "TrafficFlowObserved"
ATTRIBUTES = ["intensity", "occupancy", "averageVehicleSpeed", "congested"]
SCHEMA_URL = ("https://raw.githubusercontent.com/smart-data-models/"
              "dataModel.Transportation/master/TrafficFlowObserved/schema.json")
OUT_DIR = "sdm_salida"
VALIDATE_SAMPLE = 5  # Madrid points validated one by one in part 3

SERVICE_LEVELS = {0: "fluido", 1: "lento", 2: "retenciones", 3: "congestión"}


# ---------------------------------------------------------------- helpers
def title(text):
    print("\n" + "=" * 78)
    print(text)
    print("=" * 78)


def step(name, func, show=True, save_as=None, max_chars=600):
    """Run one package function, print the result and optionally save it."""
    print(f"\n▶ {name}")
    try:
        result = func()
    except Exception as e:  # keep going if one function fails
        print(f"  ✘ {type(e).__name__}: {str(e)[:300]}")
        return None
    if show:
        text = json.dumps(result, ensure_ascii=False, indent=2, default=str)
        print("  " + (text[:max_chars] + " …" if len(text) > max_chars else text)
              .replace("\n", "\n  "))
    if save_as:
        path = os.path.join(OUT_DIR, save_as)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"  ✔ saved to {path}")
    return result


# ================================================================ PART 1
def part1_explore():
    title("PART 1 · EXPLORE THE MODELS (slide 48)")

    subjects = step("sdm.list_all_subjects()  -> all subjects (themes)",
                    sdm.list_all_subjects, show=False, save_as="subjects.json")
    if subjects:
        print(f"  {len(subjects)} subjects, e.g. {subjects[:6]}")

    models = step(f'sdm.datamodels_subject("{SUBJECT}")  -> models in the subject',
                  lambda: sdm.datamodels_subject(SUBJECT), show=False)
    if models:
        print(f"  {len(models)} models: {', '.join(models[:12])} …")

    attrs = step(f'sdm.attributes_datamodel("{SUBJECT}", "{DATAMODEL}")',
                 lambda: sdm.attributes_datamodel(SUBJECT, DATAMODEL), show=False,
                 save_as=f"{DATAMODEL}_attributes.json")
    if attrs:
        print(f"  {len(attrs)} attributes: {', '.join(attrs)}")

    # Describe each attribute: description, units, types and reference model
    print("\n▶ Attribute details: description_attribute, units_attribute,"
          " datatype_attribute, ngsi_datatype_attribute, model_attribute")
    table = {}
    for a in ATTRIBUTES:
        row = {}
        for label, fn in (("description", sdm.description_attribute),
                          ("units", sdm.units_attribute),
                          ("type", sdm.datatype_attribute),
                          ("ngsi_type", sdm.ngsi_datatype_attribute),
                          ("model", sdm.model_attribute)):
            try:
                value = fn(SUBJECT, DATAMODEL, a)
                row[label] = None if value is False else value  # False = not set
            except Exception as e:
                row[label] = f"error: {e}"
        table[a] = row
        print(f"\n  {a}")
        for k, v in row.items():
            print(f"    {k:<12} {str(v).strip()[:110]}")
    with open(os.path.join(OUT_DIR, f"{DATAMODEL}_attribute_details.json"),
              "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, indent=2)

    # Extras
    step(f'sdm.subject_for_datamodel("{DATAMODEL}")  -> which subject owns it',
         lambda: sdm.subject_for_datamodel(DATAMODEL))
    step('sdm.look_for_datamodel("TrafficFlow", 50)  -> search by approximate name',
         lambda: sdm.look_for_datamodel("TrafficFlow", 50))
    step(f'sdm.datamodel_repolink("{DATAMODEL}")  -> GitHub repository',
         lambda: sdm.datamodel_repolink(DATAMODEL))
    step(f'sdm.list_datamodel_metadata("{DATAMODEL}", "{SUBJECT}")  -> metadata',
         lambda: sdm.list_datamodel_metadata(DATAMODEL, SUBJECT),
         save_as=f"{DATAMODEL}_metadata.json")


# ================================================================ PART 2
def part2_generate_validate():
    title("PART 2 · GENERATE, VALIDATE AND IDENTIFY (slide 49)")
    print(f"Schema: {SCHEMA_URL}")

    report = step("sdm.validate_data_model_schema(url)  -> is the schema valid?",
                  lambda: sdm.validate_data_model_schema(SCHEMA_URL), show=False,
                  save_as=f"{DATAMODEL}_schema_validation.json")
    if isinstance(report, dict):
        print("  Diagnosis:", json.dumps(report.get("schemaDiagnose"),
                                         ensure_ascii=False)[:400])

    step("sdm.ngsi_ld_example_generator(url)  -> NGSI-LD normalized example",
         lambda: sdm.ngsi_ld_example_generator(SCHEMA_URL),
         save_as=f"{DATAMODEL}_example-normalized.jsonld")
    step("sdm.ngsi_ld_keyvalue_example_generator(url)  -> key-values example",
         lambda: sdm.ngsi_ld_keyvalue_example_generator(SCHEMA_URL),
         save_as=f"{DATAMODEL}_example.jsonld")
    step("sdm.geojson_features_example_generator(url)  -> GeoJSON example",
         lambda: sdm.geojson_features_example_generator(SCHEMA_URL),
         save_as=f"{DATAMODEL}_example.geojson")

    # identify_or_draft_datamodel: which model fits a payload?
    payload = {"id": "x", "type": "TrafficFlowObserved", "intensity": 450}
    r = step(f"sdm.identify_or_draft_datamodel({payload})  -> exact match by type",
             lambda: sdm.identify_or_draft_datamodel(payload), show=False,
             save_as="identify_exact.json")
    show_identify(r)

    payload = {"id": "x", "intensity": 450, "occupancy": 0.3, "averageVehicleSpeed": 40}
    r = step(f"sdm.identify_or_draft_datamodel({payload}, fuzzy=True)"
             "  -> no type: guess by attributes",
             lambda: sdm.identify_or_draft_datamodel(payload, fuzzy=True),
             show=False, save_as="identify_fuzzy.json")
    show_identify(r)


def show_identify(result):
    """Print the useful part of identify_or_draft_datamodel's answer."""
    if not isinstance(result, dict):
        return
    schema = result.get("schema") or {}
    print(f"  Proposed: {schema.get('subject')} / {schema.get('datamodel')}"
          f"  (source: {schema.get('source')}, confidence: {schema.get('confidence')})")
    for c in (result.get("candidates") or [])[:5]:
        print(f"    candidate {c.get('subject')} / {c.get('dataModel')}"
              f"  score {c.get('score')}")


# ================================================================ PART 3
def load_madrid_points():
    """Latest snapshot from trafico_madrid_tiempo_real.py, or a sample."""
    files = sorted(glob.glob("trafico_madrid_*.json"))
    if files:
        with open(files[-1], encoding="utf-8") as f:
            data = json.load(f)
        print(f"Using real data from {files[-1]}")
        return data.get("puntos", data if isinstance(data, list) else [])
    print("No trafico_madrid_*.json found: using a sample point "
          "(run trafico_madrid_tiempo_real.py first for real data).")
    return [{"idelem": "3409", "descripcion": "SEPÚLVEDA ENTRADA CRUCE N-S",
             "intensidad": 80, "ocupacion": 1, "carga": 5, "nivelServicio": 0,
             "error": "N", "st_x": 436008.175534995, "st_y": 4472593.78531503,
             "fecha_hora": "05/11/2026 12:15:00"}]


def to_iso_utc(fecha_hora):
    """'05/11/2026 12:15:00' (Madrid time) -> '2026-11-05T11:15:00Z'."""
    try:
        local = datetime.strptime(fecha_hora, "%d/%m/%Y %H:%M:%S")
        local = local.replace(tzinfo=ZoneInfo("Europe/Madrid"))
        return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_transformer():
    try:
        from pyproj import Transformer
        return Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True)
    except ImportError:
        return None


def to_traffic_flow_observed(p, transformer=None):
    """Map one Madrid measuring point to a TrafficFlowObserved entity."""
    entity = {
        "id": f"urn:ngsi-ld:TrafficFlowObserved:madrid-{p.get('idelem')}",
        "type": "TrafficFlowObserved",
        "name": p.get("descripcion"),
        "dateObserved": to_iso_utc(p.get("fecha_hora")),
        "dataProvider": "Ayuntamiento de Madrid",
        "source": "https://informo.madrid.es/informo/tmadrid/pm.xml",
    }
    if isinstance(p.get("intensidad"), (int, float)):
        entity["intensity"] = p["intensidad"]                 # vehicles/hour
    if isinstance(p.get("ocupacion"), (int, float)):
        entity["occupancy"] = round(p["ocupacion"] / 100, 4)  # % -> fraction 0-1
    if isinstance(p.get("velocidad"), (int, float)):
        entity["averageVehicleSpeed"] = p["velocidad"]        # km/h
    if isinstance(p.get("nivelServicio"), int):
        entity["congested"] = p["nivelServicio"] >= 2         # retenciones/congestión
        entity["description"] = ("Nivel de servicio: "
                                 + SERVICE_LEVELS.get(p["nivelServicio"], "desconocido"))

    lat, lon = p.get("latitud"), p.get("longitud")
    if lat is None and transformer and isinstance(p.get("st_x"), (int, float)):
        lon, lat = transformer.transform(p["st_x"], p["st_y"])
    if lat is not None and lon is not None:
        entity["location"] = {"type": "Point",
                              "coordinates": [round(lon, 6), round(lat, 6)]}
    return {k: v for k, v in entity.items() if v is not None}


def part3_madrid():
    title("PART 3 · TRY IT: MADRID TRAFFIC -> TrafficFlowObserved")
    points = load_madrid_points()
    transformer = make_transformer()
    if not transformer:
        print("(pyproj not installed: entities will have no location)")

    # What does the package think a raw Madrid point is?
    raw = {k: v for k, v in points[0].items()}
    raw.setdefault("id", f"madrid-{raw.get('idelem')}")
    r = step("sdm.identify_or_draft_datamodel(raw Madrid point, fuzzy=True)"
             "  -> Spanish field names, no type",
             lambda: sdm.identify_or_draft_datamodel(raw, fuzzy=True),
             show=False, save_as="identify_madrid_raw.json")
    show_identify(r)

    entities = [to_traffic_flow_observed(p, transformer) for p in points]
    path = os.path.join(OUT_DIR, "madrid_TrafficFlowObserved.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)
    print(f"\n✔ {len(entities)} points converted -> {path}")
    print("  First entity:")
    print("  " + json.dumps(entities[0], ensure_ascii=False, indent=2).replace("\n", "\n  "))

    print(f"\n▶ sdm.validate_payload(\"{DATAMODEL}\", \"{SUBJECT}\", entity)"
          f"  -> first {min(VALIDATE_SAMPLE, len(entities))} entities")
    ok = 0
    for e in entities[:VALIDATE_SAMPLE]:
        try:
            res = sdm.validate_payload(DATAMODEL, SUBJECT, e)
            valid = bool(res.get("result")) if isinstance(res, dict) else bool(res)
            details = res.get("details") if isinstance(res, dict) else res
        except Exception as ex:
            valid, details = False, [f"{type(ex).__name__}: {ex}"]
        ok += valid
        print(f"  {'✔' if valid else '✘'} {e['id']}: {details}")
    print(f"  {ok}/{min(VALIDATE_SAMPLE, len(entities))} valid")

    # A deliberately wrong payload, to see what an error looks like
    bad = dict(entities[0], intensity="mucho")
    step('sdm.validate_payload(...) with intensity="mucho"  -> expected error',
         lambda: sdm.validate_payload(DATAMODEL, SUBJECT, bad))


# ---------------------------------------------------------------- main
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    parts = set(" ".join(sys.argv[1:]).split()) or {"1", "2", "3"}
    if "1" in parts:
        part1_explore()
    if "2" in parts:
        part2_generate_validate()
    if "3" in parts:
        part3_madrid()
    print(f"\nDone. Results in the folder {OUT_DIR}/")


if __name__ == "__main__":
    main()