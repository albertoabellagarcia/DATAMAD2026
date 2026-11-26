"""Verify the saved snapshot and the generated data, offline.

Usage: python3 -I pipeline/check.py
"""

import array
import base64
import contextlib
import csv
import hashlib
import io
import json
import math
import runpy
import re
import shutil
import socket
import struct
import sys
import tempfile
import traceback
import unicodedata
from collections import Counter
from decimal import Decimal
from pathlib import Path


def offline(*args, **kwargs):
    raise RuntimeError("network access attempted")


socket.socket = socket.create_connection = socket.getaddrinfo = offline

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "datos/snapshots/2026-11-25-municipal"
OUTPUT = ROOT / "demo/data"
NAMES = ("municipalities.json", "boundaries.geojson", "expected.json", "places.json", "terrain.json")
PROVINCE = ROOT / "datos/snapshots/2026-11-26-provincia"
SCHOOL_CODES = {"012", "013", "014", "015", "016", "017", "042", "045", "070", "072", "073", "074"}
LAYERS = ("health_centres", "pharmacies", "schools", "sports", "cultural", "parks", "bus_stops",
          "metro_stations", "rail_stations", "light_rail_stops", "dog_areas", "vets")
DOGS = ROOT / "datos/snapshots/2026-11-26-perro"
CONTOURS = ROOT / "datos/snapshots/2026-11-25-contornos-25830"
GRID = 10**7
FILES = {"alquiler-mivau": "VDP001_01.csv", "relieve-ign-200": "relieve-ign-200.tif",
         "registro-sanitario": "centros_servicios_establecimientos_sanitarios.csv",
         "oficinas-farmacia": "oficinas_farmacia.csv",
         **{i: f"{i}.geojson" for i in ("crtm-bus-interurbano", "crtm-metro", "crtm-cercanias", "crtm-metro-ligero",
                                        "idem-deporte", "idem-parques", "idem-cultura")}}
DOG_FILES = {"ayto-areas-caninas": "areas-caninas.csv", "osm-perro": "osm-perro.tsv"}
LEGAL_ID = r"[A-HJNP-SUVW]\d{7}[0-9A-J]"
PINNED_FIRST_CASES = [118, 152, 163]
PINNED_TOTALS = {"health_centres": 429, "pharmacies": 2958, "schools": 1712, "sports": 718, "cultural": 649,
                 "parks": 2083, "bus_stops": 8247, "metro_stations": 243, "rail_stations": 92, "light_rail_stops": 56}
PINNED_WITHOUT_POINT = {"health_centres": 9, "pharmacies": 5, "schools": 5, "sports": 1, "cultural": 0, "parks": 1,
                        "bus_stops": 6, "metro_stations": 0, "rail_stations": 1, "light_rail_stops": 0,
                        "dog_areas": 0, "vets": 0}
RENT = "alquiler_medio_mensual_viviendas_arrendadas_valor_catastral_municipios_mas_20000"
BONO = "spacm_bono_alquiler_joven_2022"


def build_module():
    return runpy.run_path(str(ROOT / "pipeline/build.py"))


def load(name):
    return json.loads((OUTPUT / name).read_bytes())


def by_ine():
    return {m["ine"]: m for m in load("municipalities.json")["municipalities"]}


def raw_rows(ident, encoding="utf-8-sig", folder=SNAPSHOT):
    text = (folder / f"{ident}.csv").read_bytes().decode(encoding)
    return list(csv.DictReader(io.StringIO(text, newline=""), delimiter=";"))


def province_rows(name):
    text = (PROVINCE / name).read_bytes().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text, newline=""), delimiter=";"))


def features(ident):
    return [f["properties"] for f in json.loads((PROVINCE / f"{ident}.geojson").read_bytes())["features"]]


def ministry():
    """Read apart from build.py: {ine: {(element, dwelling type, measure): text}} for 2024."""
    out = {}
    for r in province_rows("VDP001_01.csv"):
        if r["COD_PROVINCIA"] == "28" and r["AÑO"] == "2024":
            out.setdefault(r["COD_POSTAL"], {})[r["ELEMENTO"], r["TIPO_VIVIENDA"], r["TIPO_MEDIDA"]] = r["VALOR"]
    return out


def raises(function, *args):
    try:
        function(*args)
    except ValueError:
        return True
    return False


def test_province_snapshot_matches_manifest():
    files = json.loads((PROVINCE / "MANIFIESTO.json").read_bytes())["files"]
    assert len(files) == 11 and {e["id"]: e["file"] for e in files} == FILES
    for entry in files:
        data = (PROVINCE / entry["file"]).read_bytes()
        assert (len(data), hashlib.sha256(data).hexdigest()) == (entry["bytes"], entry["sha256"]), entry["file"]
        assert entry["license"] and entry["url"] and entry["downloaded"], entry["file"]


def test_snapshot_matches_manifest():
    files = json.loads((SNAPSHOT / "MANIFIESTO.json").read_bytes())["files"]
    assert len(files) == 15, len(files)
    for entry in files:
        data = (SNAPSHOT / entry["file"]).read_bytes()
        assert len(data) == entry["bytes"], entry["file"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], entry["file"]
        assert entry["license"] and entry["url"] and entry["downloaded"], entry["file"]
    [contour] = json.loads((CONTOURS / "MANIFIESTO.json").read_bytes())["files"]
    data = (CONTOURS / contour["file"]).read_bytes()
    assert (len(data), hashlib.sha256(data).hexdigest()) == (contour["bytes"], contour["sha256"])
    assert contour["crs"] == "EPSG:25830"
    assert contour["declared_by_service"]["AccessConstraints"] == "CC BY 4.0 Comunidad de Madrid"
    assert contour["declared_by_service"]["Fees"] == "NONE"


def test_rebuild_gives_same_bytes():
    with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
        build_module()["main"](SNAPSHOT, Path(folder))
        for name in NAMES:
            assert (Path(folder) / name).read_bytes() == (OUTPUT / name).read_bytes(), name


def test_codes_from_each_source():
    code = build_module()["ine_code"]
    assert code("0650", "statistics") == code("065", "education") == code("28065", "boundaries") == "28065"
    for raw, source in (("065", "statistics"), ("0650", "education"), ("65", "education"),
                        ("0650", "boundaries"), ("-", "education"), ("", "statistics"), ("08065", "boundaries")):
        assert raises(code, raw, source), (raw, source)


def test_unknown_municipality_is_an_error():
    with tempfile.TemporaryDirectory() as folder:
        copy = Path(folder) / "snapshot"
        shutil.copytree(SNAPSHOT, copy)
        path = copy / f"{BONO}.csv"
        path.write_bytes(path.read_bytes().replace(b";065;", b";999;"))
        assert raises(build_module()["build"], copy)


def test_179_municipalities_everywhere():
    municipalities = load("municipalities.json")["municipalities"]
    codes = [m["ine"] for m in municipalities]
    assert len(codes) == len(set(codes)) == 179
    shapes = [f["properties"]["ine"] for f in load("boundaries.geojson")["features"]]
    assert sorted(c for c in shapes if c) == sorted(codes)
    assert shapes.count(None) == 2
    population = {"28" + r["Código territorio"][:3] for r in raw_rows("poblacion_censada_por_edad_nacionalidad_y_sexo")
                  if r["Año"] == "2025" and r["Tipo territorio"] == "Municipios"}
    assert population == set(codes)
    assert all(m["name"] for m in municipalities)
    for field in ("population", "population_0_4", "nurseries"):
        assert all(m[field] is not None for m in municipalities), field


def test_salary_and_caps():
    salary = load("municipalities.json")["reference"]["salary"]
    assert (salary["total_eur"], salary["earners"], salary["year"]) == (19495891206, 748781, 2024)
    yearly = salary["total_eur"] / salary["earners"]
    assert round(yearly, 2) == 26036.84 and round(yearly / 12, 2) == 2169.74
    caps = [c["cap_eur_month"] for c in load("expected.json")["cases"][:3]]
    assert [round(c, 2) for c in caps] == [650.92, 867.89, 1301.84], caps


def test_expected_cases_match_the_csv():
    rents, detached = {}, set()
    for code, values in ministry().items():
        for kind in ("COLECTIVA", "UNIFAMILIAR"):
            text = values.get(("PRECIO", kind, "MEDIANA"))
            if text:
                rents[code] = Decimal(text)
                if kind == "UNIFAMILIAR":
                    detached.add(code)
                break
    cases = load("expected.json")["cases"]
    assert [c["affordable_count"] for c in cases[:3]] == PINNED_FIRST_CASES, [c["affordable_count"] for c in cases[:3]]
    for case in cases:
        limit = Decimal(str(case["annual_gross"])) * case["share"] * case["earners"]
        wanted = sorted(code for code, rent in rents.items() if rent * 1200 <= limit)
        assert case["affordable"] == wanted and case["affordable_count"] == len(wanted), case["name"]
        assert case["affordable_detached_count"] == len(detached & set(wanted)), case["name"]
        assert case["with_rent"] == len(rents) == 163


def test_nothing_fits_leaves_nobody_in():
    """The empty result: a cap under the cheapest rent in the ministry CSV, by less than one euro."""
    cheapest = min(Decimal(v["PRECIO", kind, "MEDIANA"]) for v in ministry().values()
                   for kind in ("COLECTIVA", "UNIFAMILIAR") if v.get(("PRECIO", kind, "MEDIANA")))
    case = next(c for c in load("expected.json")["cases"] if c["name"] == "nothing_fits")
    assert case["affordable"] == [] and case["affordable_count"] == 0, case["affordable"]
    assert cheapest - 1 <= Decimal(str(case["cap_eur_month"])) < cheapest, (case["cap_eur_month"], cheapest)


def test_affordability_rule_and_limits():
    fits = build_module()["affordable"]
    assert fits(600, 24000, 30, 1) is True and fits(601, 24000, 30, 1) is False
    assert fits(752, 30080, 30, 1) is True and fits(752, 30079, 30, 1) is False
    assert fits(None, 10**9, 100, 2) is None
    assert fits(600.1, 24004, 30, 1) is True and fits(600.1, 24003, 30, 1) is False
    assert fits(1027.1, 41084, 30, 1) is True and fits(1027.1, 41083, 30, 1) is False
    for bad in (("", 30, 1), (0, 30, 1), (-1, 30, 1), ("24000", 30, 1), (None, 30, 1), (True, 30, 1),
                (math.nan, 30, 1), (math.inf, 30, 1), (24000, 0, 1), (24000, 101, 1), (24000, "30", 1),
                (24000, 30, 0), (24000, 30, 3),
                (24000, 30, True), (24000, True, 1), (True, 30, True), (24000, 30, 1.0), (24000, 30, "1")):
        assert fits(600, *bad) is None, bad
    for case in load("expected.json")["invalid"]:
        assert fits(600, case["annual_gross"], case["share"], case["earners"]) is None, case


def test_one_euro_below_is_one_monthly_euro():
    cases = {c["name"]: c for c in load("expected.json")["cases"]}
    equal, below = cases["rent_equal_to_cap_fits"], cases["one_euro_below_that_cap"]
    assert equal["cap_eur_month"] - below["cap_eur_month"] == 1, below["cap_eur_month"]
    assert "28065" in equal["affordable"] and "28065" not in below["affordable"]
    assert equal["cap_eur_month"] == 700


def test_rent_coverage_and_missing_values():
    municipalities = by_ine()
    values = [m["rent"] for m in municipalities.values()]
    assert sum(v is not None for v in values) == 163 and values.count(None) == 16
    assert [sum(v["type"] == k for v in values if v) for k in ("collective", "detached")] == [137, 26]
    assert all(v["value"] > 0 and v["year"] == 2024 and v["unit"] == "eur_month" for v in values if v)
    assert max(m["population"]["value"] for m in municipalities.values() if not m["rent"]) < 700
    regional = [m["rent_regional"] for m in municipalities.values()]
    assert sum(v is not None for v in regional) == 37 and regional.count(None) == 142
    portal = {"28" + r["Código territorio"][:3]: int(r["Valor"]) for r in raw_rows(RENT)
              if r["Año"] == "2024" and r["Tipo territorio"] == "Municipios"
              and r["Tipo de vivienda"] == "Viviendas habituales" and r["Valor"] != "-"}
    assert {c: m["rent_regional"]["value"] for c, m in municipalities.items() if m["rent_regional"]} == portal


def test_rent_matches_the_ministry_csv():
    source = ministry()
    for code, m in by_ine().items():
        values = source.get(code, {})
        kind = next((k for k in ("COLECTIVA", "UNIFAMILIAR") if values.get(("PRECIO", k, "MEDIANA"))), None)
        if kind is None:
            assert m["rent"] is None, code
            continue
        rent = m["rent"]
        assert rent["type"] == {"COLECTIVA": "collective", "UNIFAMILIAR": "detached"}[kind], code
        for key, row in (("value", ("PRECIO", kind, "MEDIANA")), ("p25", ("PRECIO", kind, "PERCENT25")),
                         ("p75", ("PRECIO", kind, "PERCENT75")), ("dwellings", ("VIVIENDA", kind, "RECUENTO"))):
            assert rent[key] == (float(values[row]) if values.get(row) else None), (code, key)


def test_getafe():
    getafe = by_ine()["28065"]
    assert getafe["name"] == "Getafe"
    assert [getafe["rent"][k] for k in ("value", "p25", "p75", "dwellings", "type")] == [700, 600, 850, 12120, "collective"]
    assert getafe["rent_regional"]["value"] == 752
    assert (getafe["population"]["value"], getafe["population_0_4"]["value"]) == (195628, 7801)
    assert round(100 * 7801 / 195628, 2) == 3.99
    assert getafe["nurseries"]["value"] == 35
    assert getafe["around"]["parks"] is None and getafe["around"]["bus_stops"]["value"] > 0
    grant = getafe["youth_rent_grant"]
    assert (grant["requests"], grant["accepted"], grant["rejected"]) == (1209, 282, 927)


def test_around_matches_each_file():
    municipalities = by_ine()
    names = {code: m["name"] for code, m in municipalities.items()}
    plain = build_module()["plain_name"]
    code_of = {plain(name): code for code, name in names.items()}
    wanted = {}
    health = {(code_of[plain(r["municipio_nombre"])], r["centro_nro_registro"])
              for r in province_rows("centros_servicios_establecimientos_sanitarios.csv")
              if r["centro_tipo"] in ("Centro de salud", "Consultorio de atención primaria")}
    wanted["health_centres"] = Counter(code for code, _ in health)
    wanted["pharmacies"] = Counter(code_of[plain(r["MUNICIPIO_NOMBRE"])] for r in province_rows("oficinas_farmacia.csv"))
    wanted["schools"] = Counter("28" + r["CDMUNI"] for r in raw_rows("centros_educativos")
                                if r["SITUACIÓN"] == "ALTA" and r["COD_TIPO"] in SCHOOL_CODES)
    wanted["bus_stops"] = Counter("28" + f["CODIGOMUNICIPIO"] for f in features("crtm-bus-interurbano")
                                  if f["CODIGOPROVINCIA"] == "28")
    for layer, ident in (("metro_stations", "crtm-metro"), ("rail_stations", "crtm-cercanias"),
                         ("light_rail_stops", "crtm-metro-ligero")):
        stations = {("28" + f["CODIGOMUNICIPIO"], f["DENOMINACION"]) for f in features(ident)
                    if f["CODIGOPROVINCIA"] == "28"}
        wanted[layer] = Counter(code for code, _ in stations)
    present = {}
    for layer, ident in (("sports", "idem-deporte"), ("cultural", "idem-cultura"), ("parks", "idem-parques")):
        rows = features(ident)
        present[layer] = {"28" + f["MUN"] for f in rows}
        wanted[layer] = Counter("28" + f["MUN"] for f in rows if f["ESTADO"] != "EN EJECUCION"
                                and f.get("TIPOPARQUE") != "REFUGIOS DE PESCA Y MONTAÑA")
    for code, m in municipalities.items():
        assert tuple(m["around"]) == LAYERS, code
        for layer in LAYERS[:-2]:
            figure = m["around"][layer]
            if code not in present.get(layer, names):
                assert figure is None, (code, layer, figure)
            else:
                assert figure["value"] == wanted[layer][code] and figure["year"] and figure["source"], (code, layer, figure)
    assert {layer: len(codes) for layer, codes in present.items()} == {"sports": 155, "cultural": 153, "parks": 155}
    assert all(municipalities[c]["around"]["parks"] is None for c in ("28065", "28079", "28092"))
    assert sum(m["around"]["pharmacies"]["value"] == 0 for m in municipalities.values()) == 19
    assert sum(m["around"]["bus_stops"]["value"] > 0 for m in municipalities.values()) == 179
    assert sum(m["around"]["metro_stations"]["value"] > 0 for m in municipalities.values()) == 12
    totals = {layer: sum(m["around"][layer]["value"] for m in municipalities.values() if m["around"][layer])
              for layer in LAYERS[:-2]}
    assert totals == PINNED_TOTALS, totals


def test_places_are_points_in_their_municipality():
    places, municipalities = load("places.json"), by_ine()
    assert tuple(places["layers"]) == LAYERS
    shapes = shapes_in(OUTPUT / "boundaries.geojson")
    total = 0
    for layer, content in places["layers"].items():
        assert set(content) == {"source", "points"} | ({"other_sources"} if layer == "dog_areas" else set()), layer
        for code, points in content["points"].items():
            figure = municipalities[code]["around"][layer]
            assert figure and 0 < len(points) <= figure["value"], (layer, code)
            for point in points:
                assert len(point) == 5 and all(type(v) is float and round(v, 5) == v for v in point[:2]), (layer, point)
                assert all(v is None or (type(v) is str and v == v.strip() and v) for v in point[2:]), (layer, point)
                assert -4.7 <= point[0] <= -3.0 and 39.8 <= point[1] <= 41.2, (layer, point)
            total += len(points)
            for lon, lat, *_ in points:
                if not any(sum(contains(r, (lon, lat)) for r in polygon) % 2 for polygon in shapes[code]):
                    metres = min(math.hypot((a - lon) * 84700, (b - lat) * 111000)
                                 for polygon in shapes[code] for r in polygon for a, b in r)
                    assert metres < 700, (layer, code, lon, lat, round(metres))
        listed = sum(map(len, content["points"].values()))
        counted = sum(m["around"][layer]["value"] for m in municipalities.values() if m["around"][layer])
        assert counted - listed == places["without_point"][layer], (layer, counted, listed)
    assert total > 15000, total
    assert places["without_point"] == PINNED_WITHOUT_POINT, places["without_point"]


def items(layer):
    return [p for points in load("places.json")["layers"][layer]["points"].values() for p in points]


def test_places_carry_the_information_of_each_file():
    assert load("places.json")["fields"] == ["longitude", "latitude", "name", "address", "extra"]
    assert all(p[2] is None and p[3] and p[4] is None for p in items("pharmacies"))
    assert all(p[2] is None and p[3] and p[4] in ("Centro de salud", "Consultorio de atención primaria")
               for p in items("health_centres"))
    for layer in ("bus_stops", "metro_stations", "rail_stations", "light_rail_stops"):
        assert all(p[3] is None and p[4] is None for p in items(layer)), layer
        ident = {"bus_stops": "crtm-bus-interurbano", "metro_stations": "crtm-metro",
                 "rail_stations": "crtm-cercanias", "light_rail_stops": "crtm-metro-ligero"}[layer]
        unnamed = {f["CODIGOMUNICIPIO"] for f in features(ident)
                   if f["CODIGOPROVINCIA"] == "28" and not (f["DENOMINACION"] or "").strip()}
        # the metro file has one point in Madrid without a name (two identical rows): null, never a guessed name
        assert sum(p[2] is None for p in items(layer)) == len(unnamed) == (layer == "metro_stations"), layer
    for layer in ("sports", "cultural", "parks"):
        assert all(p[3] is None and p[4] for p in items(layer)), layer
        assert sum(p[2] is None for p in items(layer)) <= 5, layer
    schools = items("schools")
    assert all(p[2] and p[3] and p[4].rsplit(" · ", 1)[1] in ("PÚBLICO", "PRIVADO", "PRIVADO CONCERTADO") for p in schools)
    names = {p[2] for p in schools}
    assert not names & {"NOMBRE RETIRADO", "NOMBRE RETIRADO", "NOMBRE RETIRADO"}, names
    assert "SAN JOSE" in names
    other = {p[2] for layer in ("sports", "cultural", "parks") for p in items(layer)}
    assert not other & {"NOMBRE RETIRADO", "NOMBRE RETIRADO", "NOMBRE RETIRADO"}
    stations = {p[2] for p in load("places.json")["layers"]["rail_stations"]["points"]["28065"]}
    assert stations == {f["DENOMINACION"] for f in features("crtm-cercanias")
                        if f["CODIGOPROVINCIA"] == "28" and f["CODIGOMUNICIPIO"] == "065"}
    wanted = {" ".join(r[k].strip() for k in ("DIRECCION_VIAL_TIPO", "DIRECCION_VIAL_NOMBRE", "DIRECCION_VIAL_NRO")
                       if r[k].strip()) for r in province_rows("oficinas_farmacia.csv") if r["MUNICIPIO_NOMBRE"] == "Getafe"}
    getafe = {p[3] for p in load("places.json")["layers"]["pharmacies"]["points"]["28065"]}
    assert getafe and getafe <= {" ".join(w.split()) for w in wanted}


def fold(text):
    text = "".join(c for c in unicodedata.normalize("NFD", text.upper()) if not unicodedata.combining(c))
    return " " + " ".join(re.sub(r"[^A-Z0-9]+", " ", text).split()) + " "


def private_people():
    """Holder names and telephone numbers that must never reach the output."""
    holders = {fold(name) for r in province_rows("oficinas_farmacia.csv") for name in r["TITULARES_NOMBRE"].split(",")}
    schools = raw_rows("centros_educativos")
    holders |= {fold(r["TITULAR"]) for r in schools
                if r["TITULARIDAD"] != "PÚBLICO" and not re.fullmatch(LEGAL_ID, r["NIF_TITULAR"].strip())}
    phones = {re.sub(r"\D", "", r[k]) for r in schools for k in ("TELEFONO", "TELEFONO2", "TELEFONO3", "TELEFONO4", "FAX")}
    return {h for h in holders if len(h.split()) >= 3}, {p for p in phones if len(p) == 9}


def personal(strings, holders, phones):
    """Strings that look like an e-mail, a telephone or a tax number, or that name a holder."""
    found = []
    text = "\n".join(fold(s) for s in strings)
    found += [h for h in holders if h in text]
    for value in strings:
        digits = re.sub(r"\D", "", value)
        if (re.search(r"\S@\S", value) or re.search(r"(?<!\d)[6789](?:[ .\-]?\d){8}(?!\d)", value)
                or re.search(r"(?<![A-Za-z0-9])(\d{8}[ \-]?[A-Za-z]|[XYZ]\d{7}[A-Za-z]|[A-HJNP-SUVW]\d{8})(?![A-Za-z0-9])", value)
                or any(digits[i:i + 9] in phones for i in range(len(digits) - 8))):
            found.append(value)
    return found


def test_personal_data_detector():
    holders, phones = {fold("Nombre Inventado Prueba")}, {"918887766"}
    for bad in ("escribe a alguien@ejemplo.es", "Tel. 91 580 12 34", "600123456", "NIF 12345678Z", "X1234567L",
                "B12345678", "Farmacia Nombre Inventado Prueba", "fax 918-887-766"):
        assert personal([bad], holders, phones), bad
    clean = ["CTRA M506 KM 12,300", "CALLE de Alcalá 98", "AV. 8 DE MARZO-C/ 1 DE MAYO", "Centro de salud"]
    assert not personal(clean, holders, phones), personal(clean, holders, phones)


def test_dog_snapshot_matches_manifest():
    files = json.loads((DOGS / "MANIFIESTO.json").read_bytes())["files"]
    assert {e["id"]: e["file"] for e in files} == DOG_FILES
    for entry in files:
        data = (DOGS / entry["file"]).read_bytes()
        assert (len(data), hashlib.sha256(data).hexdigest()) == (entry["bytes"], entry["sha256"]), entry["file"]
        assert entry["license"] and entry["url"] and entry["downloaded"], entry["file"]


def test_dog_areas_and_vets():
    """Counted again here in longitude and latitude; build.py places the points in EPSG:25830."""
    municipalities, places = by_ine(), load("places.json")
    osm = list(csv.DictReader(io.StringIO((DOGS / "osm-perro.tsv").read_text(encoding="utf-8"), newline=""),
                              delimiter="\t", quoting=csv.QUOTE_NONE))
    assert not {k for k in osm[0] if re.search("phone|mail|web|contact|operator|owner", k)}
    madrid = list(csv.DictReader(io.StringIO((DOGS / "areas-caninas.csv").read_bytes().decode("utf-8-sig"), newline=""),
                                 delimiter=";"))
    shapes = shapes_in(OUTPUT / "boundaries.geojson")
    shapes = {c: s for c, s in shapes.items() if c in municipalities}
    wanted = {"dog_areas": Counter(), "vets": Counter()}
    for r in osm:
        point = float(r["@lon"]), float(r["@lat"])
        layer = "vets" if r["amenity"] == "veterinary" else "dog_areas"
        if layer == "dog_areas" and r["access"] in ("private", "no"):
            continue
        for code, polygons in shapes.items():
            if any(sum(contains(ring, point) for ring in polygon) % 2 for polygon in polygons):
                wanted[layer][code] += 1
    wanted["dog_areas"]["28079"] = sum(r["ESTADO"] == "OPERATIVO" for r in madrid)
    assert wanted["dog_areas"]["28079"] == 113
    for code, m in municipalities.items():
        for layer in wanted:
            figure, count = m["around"][layer], wanted[layer][code]
            if not count:
                assert figure is None, (code, layer, figure, "absence in OpenStreetMap is not zero")
                continue
            source = "ayto-areas-caninas" if (code, layer) == ("28079", "dog_areas") else "osm-perro"
            assert figure == {"value": count, "year": 2026, "source": source}, (code, layer, figure, count)
    assert places["layers"]["dog_areas"]["other_sources"] == {"28079": "ayto-areas-caninas"}
    assert len(places["layers"]["dog_areas"]["points"]["28079"]) == 113
    city = places["layers"]["dog_areas"]["points"]["28079"]
    assert all(p[2] is None and p[4] == "Zona canina" for p in city)
    no_address = sum(not "".join(r[k].strip() for k in ("TIPO_VIA", "NOM_VIA", "NUM_VIA")) for r in madrid)
    assert sum(p[3] is None for p in city) == no_address == 2, no_address
    assert {layer: sum(m["around"][layer]["value"] for m in municipalities.values() if m["around"][layer])
            for layer in wanted} == {"dog_areas": 378, "vets": 355}
    vets = items("vets")
    assert all(p[4] == "Veterinario" for p in vets)
    shown = {p[2] for p in vets}
    assert not shown & {"Dr. Eugenio Cabezas", "F. Gálvez Sánchez", "Veterinaria Araceli Fernández", "Concha Vizcay"}
    assert "Centro Veterinario Mirasierra" in shown and None in shown
    data = load("municipalities.json")
    for layer in wanted:
        assert "OpenStreetMap" in data["definitions"][layer] and "no significa que no haya" in data["definitions"][layer]
    assert "no consta si admiten perros" in data["definitions"]["parks_for_dogs"]
    source = data["sources"]["osm-perro"]
    assert "© OpenStreetMap" in source["credit"] and "ODbL" in source["license"]
    assert source["link"] == "https://www.openstreetmap.org/copyright"
    assert "CC BY 4.0" in data["sources"]["ayto-areas-caninas"]["credit"]


def test_utm_forward_matches_the_inverse():
    module = build_module()
    for east, north in ((365000, 4415000), (440000, 4470000), (496000, 4558000)):
        back = module["utm"](*module["lon_lat"](east, north))
        assert math.dist(back, (east, north)) < 0.01, (east, north, back)


def test_terrain_grid_against_the_source():
    terrain = load("terrain.json")
    assert (OUTPUT / "terrain.json").stat().st_size < 1_500_000
    heights = array.array("h", base64.b64decode(terrain["heights"]))
    if sys.byteorder == "big":
        heights.byteswap()
    width, height, nodata = terrain["width"], terrain["height"], terrain["nodata"]
    assert len(heights) == width * height and nodata == -32768
    inside = [h for h in heights if h != nodata]
    assert 383 <= min(inside) < 450 and 2300 < max(inside) <= 2389, (min(inside), max(inside))
    (west, north), (dx, dy) = terrain["origin"], terrain["step"]
    assert dx > 0 > dy
    area = len(inside) * (dx * 111.32 * math.cos(math.radians(40.5))) * (-dy * 111.03)
    assert 7900 < area < 8150, area
    assert all(heights[i] == nodata for i in (0, width - 1, width * (height - 1), width * height - 1))
    tif = (PROVINCE / "relieve-ign-200.tif").read_bytes()
    lon_lat = build_module()["lon_lat"]
    differences = []
    for row in range(0, 715, 6):
        # 120 strips of 6 rows each, first at byte 1416, 7860 bytes apart (TIFF tags 273 and 279)
        values = struct.unpack_from("<655h", tif, 1416 + row // 6 * 7860)
        for column in range(0, 655, 5):
            lon, lat = lon_lat(365100 + 200 * column, 4557900 - 200 * row)
            i, j = round((lon - west) / dx), round((lat - north) / dy)
            if 0 <= i < width and 0 <= j < height and heights[j * width + i] != nodata:
                differences.append(abs(heights[j * width + i] - values[column]))
    differences.sort()
    # about 120 rows x 131 columns x 8,028 / 18,733 km2 of the source rectangle
    assert 6400 < len(differences) < 7100, len(differences)
    assert differences[len(differences) // 2] <= 8 and differences[int(len(differences) * 0.99)] <= 60, (
        differences[len(differences) // 2], differences[int(len(differences) * 0.99)])


def test_youth_rent_grant_totals():
    data = load("municipalities.json")
    grants = [m["youth_rent_grant"] for m in data["municipalities"] if m["youth_rent_grant"]]
    other = data["unassigned"]["youth_rent_grant"]
    assert len(grants) == 159 and len(data["municipalities"]) - len(grants) == 20
    assigned = {k: sum(g[k] for g in grants) for k in ("requests", "accepted", "rejected")}
    assert (assigned["rejected"], assigned["requests"]) == (36906, 48383), assigned
    assert (other["requests"], other["rejected"]) == (3352, 3352)
    assert [assigned[k] + other[k] for k in ("requests", "accepted", "rejected")] == [51735, 11477, 40258]


def test_nurseries_total_and_real_zeros():
    municipalities = by_ine()
    counted = [r for r in raw_rows("centros_educativos") if r["SITUACIÓN"] == "ALTA"
               and r["COD_TIPO"] in ("003", "006", "008")]
    assert sum(m["nurseries"]["value"] for m in municipalities.values()) == len(counted) == 1171
    assert any(m["nurseries"]["value"] == 0 for m in municipalities.values())
    acebeda = next(m for m in municipalities.values() if m["name"] == "La Acebeda")
    assert acebeda["population_0_4"]["value"] == 0


def test_private_early_centres_are_counted_apart():
    municipalities = by_ine().values()
    wanted = {}
    for r in raw_rows("centros_educativos"):
        if r["SITUACIÓN"] == "ALTA" and r["COD_TIPO"] == "004":
            assert r["TIPO_EXT"] == "CENTRO PRIVADO DE EDUCACIÓN INFANTIL", r["TIPO_EXT"]
            wanted["28" + r["CDMUNI"]] = wanted.get("28" + r["CDMUNI"], 0) + 1
    assert sum(wanted.values()) == 64
    for m in municipalities:
        key = "private_early_centres"
        assert set(m[key]) == set(m["nurseries"]) and m[key]["source"] == "centros_educativos"
        assert m[key]["value"] == wanted.get(m["ine"], 0), m["ine"]
        assert "child_houses" not in m


def test_salary_scope_is_the_region():
    """AEAT 2024, earners by residence, read on 25 November 2026 at reference.salary.scope_evidence."""
    region_earners, region_euros, spain_earners = 3476015, 110923709204, 20637992
    totals = []
    for ident in ("perceptores_asalariados_por_edad_nacionalidad_y_sexo",
                  "perceptores_salarios_por_edad_nacionalidad_y_sexo"):
        by_age = [int(r["Valor"]) for r in raw_rows(ident)
                  if (r["Año"], r["Sexo"], r["Nacionalidad"]) == ("2024", "Total", "Total")]
        assert len(by_age) == 7
        totals.append(sum(by_age))
        meta = json.loads((SNAPSHOT / f"{ident}.meta.json").read_bytes())["result"]
        assert "Toda España" in json.dumps(meta, ensure_ascii=False), "metadata changed: review the scope note"
    assert totals[0] == region_earners and totals[0] != spain_earners, totals
    assert abs(totals[1] - region_euros) <= 1, totals
    census = {r["Edad"]: int(r["Valor"]) for r in raw_rows("poblacion_censada_por_edad_nacionalidad_y_sexo")
              if (r["Año"], r["Tipo territorio"], r["Sexo"], r["Nacionalidad"])
              == ("2024", "Comunidad de Madrid", "Total", "Total")}
    salary = load("municipalities.json")["reference"]["salary"]
    assert salary["earners"] < census["De 25-29 años"] + census["De 30-34 años"] < census["Total"]
    assert salary["scope"] == "Comunidad de Madrid" and salary["scope_basis"] == "earner_residence"
    assert "Toda España" in salary["scope_note"]
    assert salary["scope_evidence"].startswith("https://sede.agenciatributaria.gob.es/")


def test_removed_rows_become_null_not_zero():
    with tempfile.TemporaryDirectory() as folder:
        copy, province = Path(folder) / "snapshot", Path(folder) / "province"
        shutil.copytree(SNAPSHOT, copy)
        shutil.copytree(PROVINCE, province)
        for ident in (RENT, BONO, "poblacion_censada_por_edad_nacionalidad_y_sexo"):
            path = copy / f"{ident}.csv"
            lines = path.read_bytes().split(b"\n")
            path.write_bytes(b"\n".join(line for line in lines if b";Getafe;" not in line and not line.startswith(b"Getafe;")))
        path = province / "VDP001_01.csv"
        path.write_bytes(b"\n".join(line for line in path.read_bytes().split(b"\n") if b";Getafe;" not in line))
        path = province / "idem-deporte.geojson"
        layer = json.loads(path.read_bytes())
        layer["features"] = [f for f in layer["features"] if f["properties"]["MUN"] != "088"]
        path.write_text(json.dumps(layer), encoding="utf-8")
        built = build_module()["build"](copy, province=province)
        result = built["municipalities.json"]["municipalities"]
        by_code = {m["ine"]: m for m in result}
        assert len(result) == 179
        for field in ("rent", "rent_regional", "youth_rent_grant", "population", "population_0_4"):
            assert by_code["28065"][field] is None, (field, by_code["28065"][field])
        assert by_code["28088"]["around"]["sports"] is None
        assert "28088" not in built["places.json"]["layers"]["sports"]["points"]


def test_sources_are_declared():
    data = load("municipalities.json")
    manifest = {e["file"]: e["sha256"] for folder in (SNAPSHOT, CONTOURS, PROVINCE, DOGS)
                for e in json.loads((folder / "MANIFIESTO.json").read_bytes())["files"] if e["id"] != "idem-unid-admin"
                or folder == CONTOURS}
    figures = [m[f] for m in data["municipalities"] for f in
               ("rent", "rent_regional", "population", "population_0_4", "nurseries", "private_early_centres",
                "youth_rent_grant")] + [f for m in data["municipalities"] for f in m["around"].values()]
    used = {f["source"] for f in figures if f}
    used |= set(data["reference"]["salary"]["sources"]) | {load("boundaries.geojson")["source"]}
    used |= {load("terrain.json")["source"]} | {c["source"] for c in load("places.json")["layers"].values()}
    assert used == set(data["sources"]), used ^ set(data["sources"])
    for ident, source in data["sources"].items():
        file = {**FILES, **DOG_FILES}.get(ident, f"{ident}.{'geojson' if ident == 'idem-unid-admin' else 'csv'}")
        assert source["sha256"] == manifest[file], ident
        assert all(source[k] for k in ("title", "url", "downloaded", "license", "credit")), ident
    sources = data["sources"]
    for ident in ("crtm-bus-interurbano", "crtm-metro", "crtm-cercanias", "crtm-metro-ligero"):
        assert "Powered by CRTM" in sources[ident]["credit"] and sources[ident]["link"] == "http://www.crtm.es/"
        year, month, day = sources[ident]["edition"].split("-")
        assert year == "2026" and month == "06" and f"{day}/{month}/{year}" in sources[ident]["credit"], sources[ident]
    assert "CC BY 4.0 scne.es" in sources["relieve-ign-200"]["credit"]
    rent = sources["alquiler-mivau"]
    assert "Origen de los datos: Ministerio de Vivienda y Agenda Urbana" in rent["credit"]
    assert "1495/2011" in rent["license"] and "sin confirmar" in rent["note"] and "euros al mes" in rent["note"]
    assert set(data["definitions"]) == set(LAYERS) | {"rent", "rent_regional", "parks_for_dogs"}


def polygons_of(geometry):
    return [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]


def snap(ring):
    points = []
    for lon, lat in ring:
        point = (round(lon * GRID), round(lat * GRID))
        if not points or point != points[-1]:
            points.append(point)
    return points


def owner(feature):
    props = feature["properties"]
    if "ine" in props:
        return props["ine"] or props["name"]
    return props["DS_NOMBRE"] if props["DS_DESCRIPCION"].startswith("Comunidad") else props["CD_INE"]


def shapes_in(path):
    shapes = {}
    for feature in json.loads(path.read_bytes())["features"]:
        shapes.setdefault(owner(feature), []).extend(polygons_of(feature["geometry"]))
    return shapes


def turn(a, b, c):
    value = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (value > 0) - (value < 0)


def inside_box(a, b, c):
    return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])


def intersections(rings):
    """Any contact between non-adjacent segments of one ring, folded-back neighbours,
    and proper crossings between any two rings of the layer."""
    segments = []
    for r, ring in enumerate(rings):
        size = len(ring) - 1
        segments += [(min(ring[i][0], ring[i + 1][0]), max(ring[i][0], ring[i + 1][0]), r, i, size,
                      ring[i], ring[i + 1]) for i in range(size)]
    segments.sort()
    found = []
    for k, (_, right, r, i, size, a, b) in enumerate(segments):
        for left, _, s, j, _, c, d in segments[k + 1:]:
            if left > right:
                break
            if min(c[1], d[1]) > max(a[1], b[1]) or max(c[1], d[1]) < min(a[1], b[1]):
                continue
            turns = turn(a, b, c), turn(a, b, d), turn(c, d, a), turn(c, d, b)
            crosses = turns[0] * turns[1] < 0 and turns[2] * turns[3] < 0
            touches = [(a, b, c), (a, b, d), (c, d, a), (c, d, b)]
            if r != s:
                bad = crosses
            elif abs(i - j) in (1, size - 1):
                bad = any(t == 0 and point not in (u, v) and inside_box(u, v, point)
                          for t, (u, v, point) in zip(turns, touches))
            else:
                bad = crosses or any(t == 0 and inside_box(u, v, point) for t, (u, v, point) in zip(turns, touches))
            if bad:
                found.append((r, i, s, j))
    return found


def signed_area(ring):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))


def contains(ring, point):
    x, y = point
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def loops_of(edges):
    near = {}
    for a, b in edges:
        near.setdefault(a, []).append(b)
        near.setdefault(b, []).append(a)
    assert all(len(v) == 2 for v in near.values()), "outline of the layer branches"
    seen, loops = set(), []
    for start in near:
        if start in seen:
            continue
        loop, point = [], start
        while point is not None:
            loop.append(point)
            seen.add(point)
            point = next((n for n in near[point] if n not in seen), None)
        loops.append(loop + loop[:1])
    return loops


def test_layer_has_no_crossings_gaps_or_overlaps():
    shapes = shapes_in(OUTPUT / "boundaries.geojson")
    rings, owners, directed, area = [], [], [], 0
    for code, polygons in shapes.items():
        for polygon in polygons:
            for index, ring in enumerate(polygon):
                points = snap(ring)
                if (signed_area(points) > 0) != (index == 0):
                    points = points[::-1]
                rings.append(points)
                owners.append(code)
                directed += zip(points, points[1:])
                area += signed_area(points)
    found = intersections(rings)
    assert not found, f"{len(found)} intersections: {sorted({(owners[r], owners[s]) for r, _, s, _ in found})}"
    for lon, lat in ((-3.6894333333, 40.5703333333), (-3.3318333333, 40.4234), (-4.3044666667, 40.3674666667)):
        point = (lon * GRID, lat * GRID)
        holding = [code for code, polygons in shapes.items()
                   if any(sum(contains(snap(ring), point) for ring in polygon) % 2 for polygon in polygons)]
        assert len(holding) == 1, f"point {lon}, {lat} belongs to {holding}"
    assert len(directed) == len(set(directed)), "two outlines run along the same side of a segment"
    present = set(directed)
    loops = loops_of([(a, b) for a, b in directed if (b, a) not in present])
    outer, *others = sorted(loops, key=len, reverse=True)
    assert len(others) == 2, f"{len(loops)} outer loops, expected region, one exclave and one hole"
    signed = abs(signed_area(outer))
    for loop in others:
        signed += abs(signed_area(loop)) * (-1 if contains(outer, loop[0]) else 1)
    assert area == signed, (area, signed)


def test_outlines_keep_every_vertex_and_match_the_service():
    """The control points are the service's own longitude and latitude, published with four decimals."""
    output = shapes_in(OUTPUT / "boundaries.geojson")
    native = shapes_in(CONTOURS / "idem-unid-admin.geojson")
    control = shapes_in(SNAPSHOT / "idem-unid-admin.geojson")
    assert set(output) == set(native) == set(control)
    differences = []
    for code, polygons in output.items():
        shape = [[len(r) for r in p] for p in polygons]
        assert shape == [[len(r) for r in p] for p in native[code]] == [[len(r) for r in p] for p in control[code]], code
        for ours, theirs in zip((v for p in polygons for r in p for v in r),
                                (v for p in control[code] for r in p for v in r)):
            differences.append((ours[0] - theirs[0], ours[1] - theirs[1]))
    assert len(differences) == 155640
    for axis in (0, 1):
        values = [d[axis] for d in differences]
        assert max(map(abs, values)) <= 0.0000506, (axis, max(map(abs, values)))
        assert abs(sum(values) / len(values)) < 0.000001, (axis, sum(values) / len(values))
    for feature in json.loads((OUTPUT / "boundaries.geojson").read_bytes())["features"]:
        assert feature["geometry"]["type"] == "MultiPolygon"
        for polygon in feature["geometry"]["coordinates"]:
            for ring in polygon:
                assert len(ring) >= 4 and ring[0] == ring[-1], feature["properties"]
                for lon, lat in ring:
                    assert -4.7 <= lon <= -3.0 and 39.8 <= lat <= 41.2, (lon, lat)


def test_no_personal_data_in_outputs():
    private = {r[k].strip() for r in raw_rows("centros_educativos")
               for k in ("NIF_TITULAR", "NIF_CENTRO", "E_MAIL", "TITULAR") if len(r[k].strip()) > 8}
    private |= {r["NIF"].strip() for r in province_rows("centros_servicios_establecimientos_sanitarios.csv")
                if len(r["NIF"].strip()) > 8}
    private |= {r["TITULARES_NOMBRE"].strip() for r in province_rows("oficinas_farmacia.csv")
                if len(r["TITULARES_NOMBRE"].strip()) > 8}
    private -= {"COMUNIDAD DE MADRID"}
    assert len(private) > 5000, len(private)
    for name in NAMES:
        text = (OUTPUT / name).read_text(encoding="utf-8")
        assert "@" not in text, name
        strings = set(re.findall(r'"((?:[^"\\]|\\.)*)"', text))
        assert not strings & private, name
    holders, phones = private_people()
    assert len(holders) > 2500 and len(phones) > 3000, (len(holders), len(phones))
    shown = [v for layer in LAYERS for p in items(layer) for v in p[2:] if v]
    assert len(shown) > 20000, len(shown)
    assert not personal(shown, holders, phones), personal(shown, holders, phones)[:10]
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").split("\n")
    for path in ("2026-11-25-municipal/centros_educativos.csv",
                 "2026-11-25-municipal/spacm_listado_bibliotecas_servicios_lectura.csv",
                 "2026-11-26-provincia/centros_servicios_establecimientos_sanitarios.csv",
                 "2026-11-26-provincia/oficinas_farmacia.csv", "2026-11-26-provincia/VDP001_01.csv",
                 "2026-11-26-perro/osm-perro.tsv"):
        assert f"datos/snapshots/{path}" in ignored, path


def main():
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_")]
    failed = 0
    for name, test in tests:
        try:
            test()
            print(f"PASS {name}")
        except Exception as error:
            failed += 1
            frame = traceback.extract_tb(error.__traceback__)[-1]
            print(f"FAIL {name}: {type(error).__name__}: {str(error)[:200]} (line {frame.lineno})")
    print(f"{len(tests) - failed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
