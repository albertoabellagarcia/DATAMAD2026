"""Build the web data from the saved snapshots, offline.

Usage: python3 -I pipeline/build.py
A missing figure is null. Zero means the dataset covers the municipality and counts none.
"""

import array
import base64
import csv
import datetime
import io
import json
import math
import re
import struct
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "datos/snapshots/2026-11-25-municipal"
OUTPUT = ROOT / "demo/data"
CONTOURS = ROOT / "datos/snapshots/2026-11-25-contornos-25830"
DECIMALS = 6
PROVINCE = ROOT / "datos/snapshots/2026-11-26-provincia"
DOGS = ROOT / "datos/snapshots/2026-11-26-perro"
MADRID_DOGS, OSM, MADRID = "ayto-areas-caninas", "osm-perro", "28079"

RENT = "alquiler_medio_mensual_viviendas_arrendadas_valor_catastral_municipios_mas_20000"
SALARY = "perceptores_salarios_por_edad_nacionalidad_y_sexo"
EARNERS = "perceptores_asalariados_por_edad_nacionalidad_y_sexo"
GRANT = "spacm_bono_alquiler_joven_2022"
SCHOOLS = "centros_educativos"
POPULATION = "poblacion_censada_por_edad_nacionalidad_y_sexo"
BOUNDARIES = "idem-unid-admin"
MINISTRY, TERRAIN = "alquiler-mivau", "relieve-ign-200"
HEALTH, PHARMACIES = "registro-sanitario", "oficinas-farmacia"
HEALTH_TYPES = ("Centro de salud", "Consultorio de atención primaria")
# Colegios e institutos de primaria o secundaria. The rest of the register is described in DEFINITIONS.
SCHOOL_CODES = ("012", "013", "014", "015", "016", "017", "042", "045", "070", "072", "073", "074")
STATIONS = {"metro_stations": "crtm-metro", "rail_stations": "crtm-cercanias", "light_rail_stops": "crtm-metro-ligero"}
IDEM = {"sports": "idem-deporte", "cultural": "idem-cultura", "parks": "idem-parques"}
LAYERS = ("health_centres", "pharmacies", "schools", "sports", "cultural", "parks", "bus_stops", *STATIONS,
          "dog_areas", "vets")
# OpenStreetMap veterinary names that are a person's name, read one by one on 26 November: only type and address.
# ponytail: hand-made list for this download.
PERSON_VETS = frozenset("""Almacén de Piensos Valentín Raposo e Hijos|Alonso Cano|Centro Veterinario Cardona
|Centro Veterinario Finat|Centro veterinario General Arrando|Concha Vizcay|Consultorio Veterinario Pablo Neruda
|Clínica Veterinaria Aaron|Clínica Veterinaria Del Val|Clínica Veterinaria Guzmán el Bueno|Clínica Veterinaria Saz
|Clínica Veterinaria Unzeta|Clínica veterinaria Rafael Alberti|Veterinaria Joan Miró|Dr. Eugenio Cabezas
|F. Gálvez Sánchez|Don Pedro|Godín|José del Hierro|Hospital Veterinario Alberto Alcocer|Hospital Veterinario Puchol
|Rosa de Luxemburgo|Veterinaria Araceli Fernández|Veterinario Salvatierra""".replace("\n", "").split("|"))
LEGAL_ID = r"[A-HJNP-SUVW]\d{7}[0-9A-J]"  # tax number of a company, order or association, never of a person
# Private places whose name is a person's name, read one by one on 26 November: the map shows their type instead.
# ponytail: hand-made list for this snapshot; a new download needs a new reading.
class _Hashed(frozenset):
    def __contains__(self, name):
        return super().__contains__(__import__("hashlib").sha256(name.encode()).hexdigest())


PERSON_NAMED = _Hashed("0089d6ef3e56be6dda08727e2a11dfca90eda6694290601342a8242dea207f02 09e2f630368e452ce55ce79e86dded09a440f9709ef028988a0e90ba15e2e7d7 0c0d7df2f9e5a42508a6340fafbbdf2e0a6643752fca24402dd2199088496c61 0e7bcc9a2719da792d8bd1bd602bc4e4969ba85b0ee99b67d159d1e5973aa439 19c8c70f6e21444bc4384287dde1cb0fa9be5cfae44195e924e0d1f6383dda23 19d9d5e5aa74d024984392a85e9bbc57c5913dd7830fd455d330586661c360f6 1f2532bccadd14204e57fd446986335d97b96b29383a36b390f34dd3a64feea4 20114a5f15951d26fd629c97c3f6e77a85f8003e7ff00e0dfa8760cc711ee7ed 227f9f9ccd3ded5cbcbfa7d9a18d05516c538b3981bf0ced1a9394859ab927db 22ad2609ebff21b1b1b85639710e4efcd685568e875263fcb209d35ad01dc198 2b07a851a4125ade8da943c421cc925ce5eccc9dffc3ddeac9381295b558678d 343f911c4bb443aa38c94cd0dc8c027a960428e737155f20d36cc00aa9bb1669 4249f1f6f65ddea9e1dda154a3b94c214e546276c7e44acee7b1ca4efca8662c 471c028d9c92e16de3b1871f5062308d1cf040eb1bd7a23d66937b723d8f42ca 4dd6aa42932c3020c627da2582418c3fcd0934392d47f15894e7fde59cc6a03a 589bf87c940d2e291b48743f67d7478cd586585086dffe22daa16371bac46b22 6355d3ac4d6dc8e88b99f81d6a4d716f5d780f009c8cd60760bce187b6d959bf 6a94b30f4289da087789af961dae5b0c93d1703efaf0408d4232c78b2043bbf0 6d354c869089d8220d5d302fa4365838154e15d2830262ab5abf1532447c582f 77767c9d38b9a1d09f4d8da8a35368097eb02b669dd00e6147e464097bf84647 7c339a7fd275104faf36ae5deefe168a6dccaec048e3d0c01a1750924a9d0899 7fa662bd361eed37b51faf313fbdced2a5b15751f036e7220002173982b2f480 82570747a361d34e2b9ef23c97acae92dff6235917ebda826a19a6c2043d96ec 828f56ed46e4110a74c73748c433ca0846cb0ee9b0bfae583d3c484cd28cf767 898a095bacd6d9c964ffc16b4d34349e2cf5840c42b6532cbee51d04171bf2ab 8ec86873d214753986aa05f395c3bb69404ceb08ee564e916cdb3a700e7ac6fa 9554a39d6a8c782b3611f5a81bc9ec0481df9964d12ff758c0601b3960c934f8 97fb2cbd99092149fd42466bd26ffe048ef7c099c501f5c5679ee5a4ad4d342b 9a6743916bc870d76ab4b6ee57680502e3da6bfb60dccc1f90b2089bbb2f511b 9b325a57bd6e0f3031d50bddf0979a01291e108e3cdec642d43739e428ba2d11 9d6870a16df1bc1ec32a883da2148070cea75c8c905f29ccf87ff23754c54a28 9ed868bea9705c373e4671915c976bf015c3c5e8f92a0f04143fc55515b03c11 a27d90c5915d7f10758f2bfb7a76e37e92ab373e6553f42f72d850afc7e2f8cc a59afd79918dc69d597eb7bab2ee5cb1e518a4d8c34348b8bdb02633a28de654 adc56f13b27ccbcc1a5b02dbef232bd66ef0699fd9caf04fac7a4f68ab234172 b1b49692c23f5ec77a2404ec26130d5e34f9ef62428bafbfe1b34c494f5c1da4 b5089870807e2a667dccbb3a6c2e6c2318b8438ad5d8a584e80f54115c61405e b8295d950bc6b86b1d932248657ffee3113c8427adadf602c1386245929e853e be50f45ae93a3cb706625662e6112535ba58199d0e408d46fb236ce25a274c9c c1c134e16cff4af92431dbe84cb87868e3f2889abf115750db77c0c5aac5b742 cbc7bd829856d493dab9dce5758f1a51830e31320f6c5c1dbfebf77a48173a06 ccbafbe761f0d2a53279a7c9f032e2077b2a76934db232b43c8fd0c8d061afba d4e0cc9c70ebe73ad2907715359505bb803902b2f66f338f2b4287688bbd5a25 dddc2fbf5ae46b97aede3d1fc6f6269aec579a5d0ac9763ef00d7795ed6af93a e2ab7115d2c76950b5dc5acd197fb8f27a6883f552a5beabbe684160b55028ca e2dd4c860bcf76a02f56ec782b274389f37c21643af4337a790d167436797656 ee4d99a4fe00bca7f7f5064ec0c103f9b633f6d4a27242179b2d95961504f007".split())
NOT_PUBLIC = ("PRIVADA", "OTROS", "OTRAS")  # owners in the EIEL layers whose places go through PERSON_NAMED
IDEM_TYPE = {"sports": "TIPOINSTAL", "cultural": "TIPO", "parks": "TIPOPARQUE"}
NEAR = 500  # metres a point may fall outside the outline of its own municipality
GRID_STEP, NODATA = (0.0024, -0.0018), -32768  # about 200 m at 40.5 degrees north
DEFINITIONS = {
    "rent": "Mediana de 2024 del alquiler mensual en el CSV del Ministerio. Pisos (vivienda colectiva); donde no hay "
            "dato de pisos, casas unifamiliares.",
    "rent_regional": "Media de 2024 de las viviendas habituales, portal de la Comunidad de Madrid. Solo municipios de "
                     "más de 20.000 habitantes.",
    "health_centres": "Centros de salud y consultorios de atención primaria del registro sanitario.",
    "pharmacies": "Oficinas de farmacia.",
    "schools": "Colegios e institutos de primaria o secundaria en alta, públicos y privados. No cuenta escuelas "
               "infantiles, educación especial, centros extranjeros, adultos, formación profesional específica, "
               "idiomas ni enseñanzas artísticas o deportivas.",
    "sports": "Instalaciones deportivas de la encuesta EIEL 2023, sin las que estaban en ejecución.",
    "cultural": "Centros culturales de la encuesta EIEL 2023 (incluye centros cívicos, hogares del pensionista y plazas "
                "de toros), sin los que estaban en ejecución.",
    "parks": "Parques, jardines, parques infantiles y zonas recreativas de la encuesta EIEL 2023, sin refugios ni "
             "obras en ejecución.",
    "bus_stops": "Paradas de autobús interurbano. No incluye autobús urbano ni la EMT de Madrid.",
    "metro_stations": "Estaciones de Metro (una por nombre y municipio). El archivo del CRTM trae en Madrid un punto "
                      "sin nombre, que cuenta como una.",
    "rail_stations": "Estaciones de Cercanías (una por nombre y municipio).",
    "light_rail_stops": "Paradas de metro ligero y tranvía (una por nombre y municipio).",
    "dog_areas": "Zonas caninas. En Madrid capital, las municipales en servicio (Ayuntamiento de Madrid); en el resto, "
                 "las dibujadas en OpenStreetMap sin acceso privado. OpenStreetMap está incompleto: un municipio sin "
                 "dato no significa que no haya.",
    "vets": "Centros veterinarios anotados en OpenStreetMap. La lista está incompleta: un municipio sin dato no "
            "significa que no haya.",
    "parks_for_dogs": "Los parques son los de la encuesta EIEL 2023: no consta si admiten perros ni en qué horario.",
}

EARLY_YEARS = ("nurseries", "private_early_centres")
CODE_FORMATS = {"statistics": r"\d{4}", "education": r"\d{3}", "boundaries": r"28\d{3}"}
SCOPE_EVIDENCE = ("https://sede.agenciatributaria.gob.es/AEAT/Contenidos_Comunes/La_Agencia_Tributaria/Estadisticas/"
                  "Publicaciones/sites/mercado/2024/jrubik55619f73308d982b9a531ce2452976c1cbd79255.html")
SCOPE_NOTE = ("Los metadatos del portal dicen «Ámbito = Toda España», pero la suma de asalariados de 2024 del conjunto "
              "(3.476.015) es la que la Agencia Tributaria publica para la Comunidad de Madrid según el domicilio del "
              "perceptor. El total de su tabla es 20.637.992.")


def ine_code(raw, source):
    if not re.fullmatch(CODE_FORMATS[source], raw):
        raise ValueError(f"unexpected {source} municipality code: {raw!r}")
    return raw if source == "boundaries" else "28" + raw[:3]


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def affordable(rent, annual_gross, share, earners):
    """None means no answer: unknown rent or invalid input."""
    valid = (is_number(annual_gross) and annual_gross > 0 and is_number(share) and 1 <= share <= 100
             and type(earners) is int and earners in (1, 2))
    if rent is None or not valid:
        return None
    return rent * 1200 <= annual_gross * share * earners


def count(text):
    if text in ("", "-"):
        return None
    if not text.isdigit():
        raise ValueError(f"not a whole number: {text!r}")
    return int(text)


def plain_name(name):
    text = "".join(c for c in unicodedata.normalize("NFD", name.lower()) if not unicodedata.combining(c))
    article = re.match(r"(.*?)[, ]+\(?(el|la|los|las)\)?$", text.strip())
    if article:
        text = f"{article[2]} {article[1]}"
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def rows(folder, ident, encoding="utf-8-sig"):
    text = (folder / f"{ident}.csv").read_bytes().decode(encoding)
    return list(csv.DictReader(io.StringIO(text, newline=""), delimiter=";"))


def join(names, raw, source, name):
    """Return the INE code only if the code is known and the name agrees with the boundaries."""
    code = ine_code(raw, source)
    if code not in names:
        raise ValueError(f"unknown municipality code: {code} ({name})")
    if plain_name(name) != plain_name(names[code]):
        raise ValueError(f"code {code} is {names[code]!r} in boundaries but {name!r} in {source}")
    return code


def put(target, key, value):
    if key in target:
        raise ValueError(f"duplicate row for {key}")
    target[key] = value


def lon_lat(east, north):
    """ETRS89 UTM zone 30N (EPSG:25830) to longitude and latitude, Kruger series on the GRS80 ellipsoid."""
    flattening = 1 / 298.257222101
    n = flattening / (2 - flattening)
    radius = 0.9996 * 6378137 / (1 + n) * (1 + n ** 2 / 4 + n ** 4 / 64)
    xi, eta = north / radius, (east - 500000) / radius
    terms = (n / 2 - 2 * n ** 2 / 3 + 37 * n ** 3 / 96, n ** 2 / 48 + n ** 3 / 15, 17 * n ** 3 / 480)
    xi_s = xi - sum(b * math.sin(2 * j * xi) * math.cosh(2 * j * eta) for j, b in enumerate(terms, 1))
    eta_s = eta - sum(b * math.cos(2 * j * xi) * math.sinh(2 * j * eta) for j, b in enumerate(terms, 1))
    chi = math.asin(math.sin(xi_s) / math.cosh(eta_s))
    back = (2 * n - 2 * n ** 2 / 3 - 2 * n ** 3, 7 * n ** 2 / 3 - 8 * n ** 3 / 5, 56 * n ** 3 / 15)
    latitude = chi + sum(d * math.sin(2 * j * chi) for j, d in enumerate(back, 1))
    longitude = -3 + math.degrees(math.atan2(math.sinh(eta_s), math.cos(xi_s)))
    return longitude, math.degrees(latitude)


def utm(longitude, latitude):
    """Longitude and latitude to EPSG:25830, the forward Kruger series."""
    flattening = 1 / 298.257222101
    n = flattening / (2 - flattening)
    radius = 0.9996 * 6378137 / (1 + n) * (1 + n ** 2 / 4 + n ** 4 / 64)
    sine, turn = math.sin(math.radians(latitude)), math.radians(longitude + 3)
    k = 2 * math.sqrt(n) / (1 + n)
    t = math.sinh(math.atanh(sine) - k * math.atanh(k * sine))
    xi, eta = math.atan2(t, math.cos(turn)), math.atanh(math.sin(turn) / math.sqrt(1 + t * t))
    terms = (n / 2 - 2 * n ** 2 / 3 + 5 * n ** 3 / 16, 13 * n ** 2 / 48 - 3 * n ** 3 / 5, 61 * n ** 3 / 240)
    north = xi + sum(a * math.sin(2 * j * xi) * math.cosh(2 * j * eta) for j, a in enumerate(terms, 1))
    east = eta + sum(a * math.cos(2 * j * xi) * math.sinh(2 * j * eta) for j, a in enumerate(terms, 1))
    return 500000 + radius * east, radius * north


def convert(ring):
    """Neighbours share vertices, so converting and rounding each one alone keeps shared boundaries shared."""
    return [[round(value, DECIMALS) for value in lon_lat(east, north)] for east, north in ring]


def read_boundaries(folder):
    raw = json.loads((folder / f"{BOUNDARIES}.geojson").read_bytes())
    if not raw["crs"]["properties"]["name"].endswith("EPSG::25830"):
        raise ValueError("outlines are expected in EPSG:25830")
    names, shapes, unowned = {}, {}, []
    for feature in raw["features"]:
        props, geometry = feature["properties"], feature["geometry"]
        parts = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        parts = [[convert(ring) for ring in polygon] for polygon in parts]
        kind = props["DS_DESCRIPCION"]
        if kind.startswith("Comunidad Jurisdiccional"):
            unowned.append((props["DS_NOMBRE"], parts))
            continue
        if kind not in ("Término Municipal", "Enclave"):
            raise ValueError(f"unknown boundary kind: {kind}")
        code = ine_code(props["CD_INE"], "boundaries")
        if kind == "Término Municipal":
            put(names, code, props["DS_NOMBRE"])
        shapes.setdefault(code, []).extend(parts)
    if set(shapes) != set(names):
        raise ValueError("enclave without a municipality")
    features = [(code, names[code], shapes[code]) for code in sorted(names)]
    features += [(None, name, parts) for name, parts in sorted(unowned)]
    return names, {
        "type": "FeatureCollection",
        "source": BOUNDARIES,
        "changes_to_source": f"converted from EPSG:25830 to longitude and latitude, rounded to {DECIMALS} decimals",
        "features": [{"type": "Feature", "properties": {"ine": code, "name": name},
                      "geometry": {"type": "MultiPolygon", "coordinates": parts}}
                     for code, name, parts in features],
    }


def read_rent(folder, names):
    out = {}
    for r in rows(folder, RENT):
        if (r["Año"], r["Tipo territorio"], r["Tipo de vivienda"]) == ("2024", "Municipios", "Viviendas habituales"):
            code = join(names, r["Código territorio"], "statistics", r["Territorio"])
            value = count(r["Valor"])
            put(out, code, None if value is None else
                {"value": value, "year": 2024, "unit": "eur_month", "source": RENT})
    return out


def read_population(folder, names):
    out = {"Total": {}, "De 0-4 años": {}}
    for r in rows(folder, POPULATION):
        if (r["Año"] == "2025" and r["Tipo territorio"] == "Municipios" and r["Edad"] in out
                and r["Sexo"] == "Total" and r["Nacionalidad"] == "Total"):
            code = join(names, r["Código territorio"], "statistics", r["Territorio"])
            value = count(r["Valor"])
            put(out[r["Edad"]], code, None if value is None else
                {"value": value, "year": 2025, "unit": "people", "source": POPULATION})
    return out["Total"], out["De 0-4 años"]


def early_years_kind(label):
    if label.startswith("ESCUELA") and "INFANTIL" in label:
        return "nurseries"
    return "private_early_centres" if label == "CENTRO PRIVADO DE EDUCACIÓN INFANTIL" else None


def read_early_years(folder, names, year):
    """Assumes the register covers the whole region, so no matching row means zero."""
    out = {kind: dict.fromkeys(names, 0) for kind in EARLY_YEARS}
    for r in rows(folder, SCHOOLS):
        if r["SITUACIÓN"] == "ALTA":
            code = join(names, r["CDMUNI"], "education", r["MUNICIPIO"])
            kind = early_years_kind(r["TIPO_EXT"])
            if kind:
                out[kind][code] += 1
    return {kind: {code: {"value": n, "year": year, "unit": "centres", "source": SCHOOLS}
                   for code, n in counts.items()} for kind, counts in out.items()}


def read_grant(folder, names):
    out, unassigned = {}, {"requests": 0, "accepted": 0, "rejected": 0}
    for r in rows(folder, GRANT, "latin-1"):
        figures = {"requests": count(r["solicitudes"]), "accepted": count(r["aceptadas"]),
                   "rejected": count(r["rechazadas"])}
        if r["municipio"] == "-" and r["municipio_nombre"] == "Otro":
            for key, value in figures.items():
                unassigned[key] += value
            continue
        code = join(names, r["municipio"], "education", r["municipio_nombre"])
        put(out, code, {**figures, "year": 2022, "source": GRANT})
    return out, unassigned


def read_salary_figure(folder, ident, unit):
    matches = [r for r in rows(folder, ident)
               if (r["Año"], r["Sexo"], r["Nacionalidad"], r["Unidad"]) == ("2024", "Total", "Total", unit)
               and "de 26 a 35 años" in r["Concepto"]]
    if len(matches) != 1:
        raise ValueError(f"{ident}: expected one 26-35 row, found {len(matches)}")
    return count(matches[0]["Valor"])


def number(text):
    if not text:
        return None
    if not re.fullmatch(r"\d+(\.\d)?", text):
        raise ValueError(f"not a figure: {text!r}")
    return int(float(text)) if float(text).is_integer() else float(text)


def read_ministry_rent(folder, names):
    """Median of flats; detached houses only where there is no figure for flats."""
    found = {}
    text = (folder / "VDP001_01.csv").read_bytes().decode("utf-8-sig")
    for r in csv.DictReader(io.StringIO(text, newline=""), delimiter=";"):
        if r["COD_PROVINCIA"] == "28" and r["AÑO"] == "2024":
            code = join(names, r["COD_POSTAL"], "boundaries", r["NOMBRE_MUNICIPIO"])
            put(found.setdefault(code, {}), (r["ELEMENTO"], r["TIPO_VIVIENDA"], r["TIPO_MEDIDA"]), number(r["VALOR"]))
    out = {}
    for code, figures in found.items():
        for dwelling, kind in (("COLECTIVA", "collective"), ("UNIFAMILIAR", "detached")):
            value = figures.get(("PRECIO", dwelling, "MEDIANA"))
            if value is not None:
                out[code] = {"value": value, "year": 2024, "unit": "eur_month", "source": MINISTRY, "type": kind,
                             "dwellings": figures.get(("VIVIENDA", dwelling, "RECUENTO")),
                             "p25": figures.get(("PRECIO", dwelling, "PERCENT25")),
                             "p75": figures.get(("PRECIO", dwelling, "PERCENT75"))}
                break
    return out


def point(east, north):
    """Both columns must be numbers, whichever decimal mark they use. None means no usable point."""
    try:
        pair = float(str(east).replace(",", ".")), float(str(north).replace(",", "."))
    except ValueError:
        return None
    return pair if all(map(math.isfinite, pair)) else None


def words(*parts):
    """The given texts with single spaces, or None when there is nothing."""
    return " ".join(" ".join(p or "" for p in parts).split()) or None


def shown_name(name, kind, private, entity=True):
    """A private place named after a person, or held by someone without a company tax number, shows its type."""
    return words(kind) if private and (not entity or words(name) in PERSON_NAMED) else words(name)


def read_places(folder, schools_folder, names):
    """{layer: [(ine, point in EPSG:25830 or None, (name, address, extra))]}, one item per counted thing,
    and the IDEM coverage. Only the fields read here reach the output."""
    by_name = {plain_name(name): code for code, name in names.items()}

    def named(name):
        if plain_name(name) not in by_name:
            raise ValueError(f"unknown municipality name: {name!r}")
        return by_name[plain_name(name)]

    def table(name):
        text = (folder / name).read_bytes().decode("utf-8-sig")
        return csv.DictReader(io.StringIO(text, newline=""), delimiter=";")

    def layer(ident):
        raw = json.loads((folder / f"{ident}.geojson").read_bytes())
        if not raw["crs"]["properties"]["name"].endswith("25830"):
            raise ValueError(f"{ident}: points are expected in EPSG:25830")
        if raw.get("exceededTransferLimit") or raw.get("properties", {}).get("exceededTransferLimit"):
            raise ValueError(f"{ident}: the service cut the answer")
        return [(f["properties"], point(*f["geometry"]["coordinates"])) for f in raw["features"]]

    out, covered = {}, {}
    centres = {}
    for r in table("centros_servicios_establecimientos_sanitarios.csv"):
        if r["centro_tipo"] in HEALTH_TYPES:
            address = words(*(r[f"direccion_vial_{k}"] for k in ("tipo", "nombre", "nro")))
            item = (named(r["municipio_nombre"]), point(r["localizacion_coordenada_x"], r["localizacion_coordenada_y"]),
                    (None, address, r["centro_tipo"]))
            if centres.setdefault(r["centro_nro_registro"], item) != item:
                raise ValueError(f"health centre {r['centro_nro_registro']} appears in two places")
    out["health_centres"] = list(centres.values())
    pharmacies = {}
    for r in table("oficinas_farmacia.csv"):
        put(pharmacies, r["CODIGO_NACIONAL_CCN"], (named(r["MUNICIPIO_NOMBRE"]),
            point(r["LOCALIZACION_COORDENADA_X"], r["LOCALIZACION_COORDENADA_Y"]),
            (None, words(r["DIRECCION_VIAL_TIPO"], r["DIRECCION_VIAL_NOMBRE"], r["DIRECCION_VIAL_NRO"]), None)))
    out["pharmacies"] = list(pharmacies.values())
    out["schools"] = [
        (join(names, r["CDMUNI"], "education", r["MUNICIPIO"]), point(r["UTM_X"], r["UTM_Y"]),
         (shown_name(r["CENTRO"], r["TIPO_EXT"], r["TITULARIDAD"] != "PÚBLICO",
                     bool(re.fullmatch(LEGAL_ID, r["NIF_TITULAR"].strip()))),
          words(r["CDTPVIA"], r["DOMICILIO"], r["NMVIAL"]), f"{words(r['TIPO_EXT'])} · {r['TITULARIDAD']}"))
        for r in rows(schools_folder, SCHOOLS) if r["SITUACIÓN"] == "ALTA" and r["COD_TIPO"] in SCHOOL_CODES]

    def regional(ident):
        for props, where in layer(ident):
            if props["CODIGOPROVINCIA"] == "28":
                code = ine_code(props["CODIGOMUNICIPIO"], "education")
                if code not in names:
                    raise ValueError(f"unknown municipality code: {code} in {ident}")
                yield code, props["DENOMINACION"], where

    out["bus_stops"] = [(code, where, (words(name), None, None))
                        for code, name, where in regional("crtm-bus-interurbano")]
    for key, ident in STATIONS.items():
        stations = {}
        for code, name, where in regional(ident):
            stations.setdefault((code, name), []).append(where)
        out[key] = []
        for (code, name), found in stations.items():
            if None in found or max(math.dist(a, b) for a in found for b in found) > 1000:
                raise ValueError(f"{ident}: {name} has platforms without a point or more than 1 km apart")
            middle = tuple(sum(axis) / len(found) for axis in zip(*found))
            out[key].append((code, middle, (words(name), None, None)))
    for key, ident in IDEM.items():
        found = [(join(names, props["MUN"], "education", props["MUNICIPIO"]), props, where)
                 for props, where in layer(ident) if props["PROV"] == "28"]
        covered[key] = {code for code, _, _ in found}
        out[key] = [(code, where, (shown_name(props["NOMBRE"], props[IDEM_TYPE[key]], props["TITULAR"] in NOT_PUBLIC),
                                   None, words(props[IDEM_TYPE[key]])))
                    for code, props, where in found if props["ESTADO"] != "EN EJECUCION"
                    and props.get("TIPOPARQUE") != "REFUGIOS DE PESCA Y MONTAÑA"]
    return out, covered


def read_dogs(folder, shapes):
    """{layer: [(ine, point, info)]} for dog areas and vets, and the municipalities each one says something about."""
    out = {"dog_areas": [], "vets": []}
    text = (folder / "areas-caninas.csv").read_bytes().decode("utf-8-sig")
    for r in csv.DictReader(io.StringIO(text, newline=""), delimiter=";"):
        if r["SISTEMA_COORD"] != "ETRS89":
            raise ValueError(f"dog areas: unexpected reference system {r['SISTEMA_COORD']!r}")
        if r["ESTADO"] == "OPERATIVO":
            address = words(r["TIPO_VIA"], r["NOM_VIA"], r["NUM_VIA"])
            out["dog_areas"].append((MADRID, point(r["COORD_GIS_X"], r["COORD_GIS_Y"]), (None, address, "Zona canina")))
    boxes = {code: [f(axis) for axis in zip(*(p for ring in rings for p in ring)) for f in (min, max)]
             for code, rings in shapes.items()}
    text = (folder / "osm-perro.tsv").read_text(encoding="utf-8")
    for r in csv.DictReader(io.StringIO(text, newline=""), delimiter="\t", quoting=csv.QUOTE_NONE):
        vet = r["amenity"] == "veterinary"
        if not vet and (r["leisure"] != "dog_park" or r["access"] in ("private", "no")):
            continue
        where = utm(float(r["@lon"]), float(r["@lat"]))
        code = next((c for c, (west, east, south, north) in boxes.items() if west <= where[0] <= east
                     and south <= where[1] <= north and inside(shapes[c], where)), None)
        if code is None or (code == MADRID and not vet):
            continue  # outside the region, or inside Madrid city where the council's own list is used
        name = words(r["name"].strip('"').replace('""', '"'))
        if vet and name in PERSON_VETS:
            name = None
        out["vets" if vet else "dog_areas"].append(
            (code, where, (name, words(r["addr:street"], r["addr:housenumber"]), "Veterinario" if vet else "Zona canina")))
    return out, {layer: {code for code, _, _ in found} for layer, found in out.items()}


def inside(rings, where):
    x, y = where
    odd = False
    for ring in rings:
        for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                odd = not odd
    return odd


def distance(rings, where):
    best = math.inf
    for ring in rings:
        for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
            dx, dy = x2 - x1, y2 - y1
            along = max(0, min(1, ((where[0] - x1) * dx + (where[1] - y1) * dy) / (dx * dx + dy * dy or 1)))
            best = min(best, math.dist(where, (x1 + along * dx, y1 + along * dy)))
    return best


def outlines(contours):
    """{ine: [rings]} in EPSG:25830, to test points in their native system."""
    out = {}
    for f in json.loads((contours / f"{BOUNDARIES}.geojson").read_bytes())["features"]:
        props, geometry = f["properties"], f["geometry"]
        if not props["DS_DESCRIPCION"].startswith("Comunidad"):
            parts = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
            out.setdefault(props["CD_INE"], []).extend(ring for polygon in parts for ring in polygon)
    return out


def build_around(province, schools_folder, dogs, contours, names, years):
    found, covered = read_places(province, schools_folder, names)
    shapes = outlines(contours)
    extra, extra_covered = read_dogs(dogs, shapes)
    found.update(extra)
    covered.update(extra_covered)
    sources = {"health_centres": HEALTH, "pharmacies": PHARMACIES, "schools": SCHOOLS,
               "bus_stops": "crtm-bus-interurbano", **STATIONS, **IDEM, "dog_areas": OSM, "vets": OSM}
    own = {("dog_areas", MADRID): MADRID_DOGS}
    around = {code: {} for code in names}
    places, without, outside = {}, {}, {}
    for key in LAYERS:
        counts, points = dict.fromkeys(names, 0), {}
        without[key] = outside[key] = 0
        for code, where, info in found[key]:
            counts[code] += 1
            if where is not None and not inside(shapes[code], where):
                outside[key] += 1
                if distance(shapes[code], where) > NEAR:
                    where = None
            if where is None:
                without[key] += 1
            else:
                points.setdefault(code, []).append([*(round(v, 5) for v in lon_lat(*where)), *info])
        for code in names:
            source = own.get((key, code), sources[key])
            around[code][key] = None if code not in covered.get(key, names) else {
                "value": counts[code], "year": years[source], "source": source}
        places[key] = {"source": sources[key], "points": {c: sorted(points[c], key=str) for c in sorted(points)}}
    places["dog_areas"]["other_sources"] = {code: source for (key, code), source in own.items()}
    return around, {"crs": "ETRS89 longitude, latitude",
                    "fields": ["longitude", "latitude", "name", "address", "extra"], "layers": places, "without_point": without,
                    "rule": f"a point is dropped when it is more than {NEAR} m outside its own municipality",
                    "outside_own_outline": outside}


def read_geotiff(data):
    """The one GeoTIFF the IGN service returns: little endian, uncompressed int16 strips, EPSG:25830."""
    if data[:4] != b"II*\0":
        raise ValueError("not a little endian TIFF")
    start = struct.unpack_from("<I", data, 4)[0]
    tags = {}
    for i in range(struct.unpack_from("<H", data, start)[0]):
        tag, kind, count, raw = struct.unpack_from("<HHI4s", data, start + 2 + 12 * i)
        letter = {3: "H", 4: "I", 12: "d"}.get(kind)
        if letter:
            size = struct.calcsize(letter) * count
            offset = struct.unpack("<I", raw)[0]
            tags[tag] = struct.unpack(f"<{count}{letter}", raw[:size] if size <= 4 else data[offset:offset + size])
    keys = tags[34735]
    geo = {keys[i]: keys[i + 3] for i in range(4, len(keys), 4)}
    if (tags[258], tags[259], tags[339], geo[1025], geo[3072]) != ((16,), (1,), (2,), 1, 25830):
        raise ValueError("unexpected TIFF layout")
    values = array.array("h", b"".join(data[o:o + n] for o, n in zip(tags[273], tags[279])))
    if sys.byteorder == "big":
        values.byteswap()
    width, height = tags[256][0], tags[257][0]
    if len(values) != width * height:
        raise ValueError("TIFF size does not match its header")
    scale, tie = tags[33550][0], tags[33922]
    return values, width, height, scale, (tie[3] + scale / 2, tie[4] - scale / 2)


def build_terrain(province, boundaries):
    values, wide, high, scale, (east0, north0) = read_geotiff((province / "relieve-ign-200.tif").read_bytes())
    polygons = [polygon for f in boundaries["features"] for polygon in f["geometry"]["coordinates"]]
    lons = [x for polygon in polygons for x, _ in polygon[0]]
    lats = [y for polygon in polygons for _, y in polygon[0]]
    dx, dy = GRID_STEP
    west, north = math.floor(min(lons) * 100) / 100, math.ceil(max(lats) * 100) / 100
    width = int((max(lons) - west) / dx) + 2
    height = int((min(lats) - north) / dy) + 2
    grid = array.array("h", [NODATA]) * (width * height)
    for polygon in polygons:
        crossings = {}
        for ring in polygon:
            for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
                low, top = sorted((y1, y2))
                for j in range(math.ceil((top - north) / dy), math.floor((low - north) / dy) + 1):
                    lat = north + j * dy
                    if (y1 > lat) != (y2 > lat):
                        crossings.setdefault(j, []).append((x2 - x1) * (lat - y1) / (y2 - y1) + x1)
        for j, found in crossings.items():
            found.sort()
            for left, right in zip(found[::2], found[1::2]):
                for i in range(math.ceil((left - west) / dx), math.ceil((right - west) / dx)):
                    east, northing = utm(west + i * dx, north + j * dy)
                    # clamped to the source rectangle, bilinear between the four nearest samples
                    x = min(max((east - east0) / scale, 0), wide - 1.000001)
                    y = min(max((north0 - northing) / scale, 0), high - 1.000001)
                    c, r = int(x), int(y)
                    fx, fy, at = x - c, y - r, r * wide + c
                    grid[j * width + i] = round(
                        (values[at] * (1 - fx) + values[at + 1] * fx) * (1 - fy)
                        + (values[at + wide] * (1 - fx) + values[at + wide + 1] * fx) * fy)
    if sys.byteorder == "big":
        grid.byteswap()
    return {"crs": "ETRS89 longitude, latitude", "origin": [west, north], "step": [dx, dy], "width": width,
            "height": height, "nodata": NODATA, "unit": "metres",
            "encoding": "base64, int16 little-endian, row by row from north to south, west to east",
            "source": TERRAIN, "heights": base64.b64encode(grid.tobytes()).decode("ascii")}


def day(iso):
    return "/".join(reversed(iso.split("-")))


def province_sources(province):
    out = {}
    for entry in json.loads((province / "MANIFIESTO.json").read_bytes())["files"]:
        ident, downloaded = entry["id"], entry["downloaded"][:10]
        source = {"title": entry["title"], "url": entry["url"], "downloaded": downloaded,
                  "sha256": entry["sha256"], "license": entry["license"]}
        if ident == MINISTRY:
            source["credit"] = ("Origen de los datos: Ministerio de Vivienda y Agenda Urbana. Datos hasta 2024, "
                                f"descargados el {day(downloaded)}. El Ministerio no participa en este proyecto ni lo apoya.")
            source["conditions"] = ("RD 1495/2011: no desnaturalizar la información, citar la fuente, mencionar la fecha "
                                    "de actualización si el original la trae, no sugerir apoyo del organismo y conservar "
                                    "sus metadatos.")
            source["link"] = "https://www.boe.es/buscar/act.php?id=BOE-A-2011-17560"
            source["note"] = ("La unidad (euros al mes) y la definición de las columnas del CSV están sin confirmar: no "
                              "se ha abierto ninguna definición oficial del archivo.")
        elif ident == TERRAIN:
            source["credit"] = "Obra derivada de modelos digitales del terreno del IGN, CC BY 4.0 scne.es"
            source["note"] = "Remuestreado a longitud y latitud y recortado a la región. Fecha del dato pendiente."
        elif ident.startswith("crtm-"):
            stamp = entry["declared_by_service"]["editingInfo"]["dataLastEditDate"] / 1000
            edition = datetime.datetime.fromtimestamp(stamp, datetime.timezone.utc).date().isoformat()
            source.update(edition=edition, link="http://www.crtm.es/",
                          conditions="https://www.crtm.es/licencia-de-uso",
                          credit=("Fuente: Consorcio Regional de Transportes de Madrid (CRTM), datos explotados. "
                                  f"Powered by CRTM. Datos editados el {day(edition)}."))
        elif ident.startswith("idem-"):
            source["credit"] = "Fuente: IDEM, EIEL 2023, CC BY 4.0 Comunidad de Madrid"
        else:
            source["url"] = entry["url"].split("/resource/")[0]
            source["credit"] = "Origen de los datos: Comunidad de Madrid, portal de datos abiertos, CC BY"
        out[ident] = source
    return out


def dog_sources(folder):
    out = {}
    for entry in json.loads((folder / "MANIFIESTO.json").read_bytes())["files"]:
        downloaded = entry["downloaded"][:10]
        source = {"title": entry["title"], "url": entry["page"], "downloaded": downloaded, "sha256": entry["sha256"],
                  "license": entry["license"]}
        if entry["id"] == OSM:
            until = entry["declared_by_service"]["data_until"][:10]
            source.update(link=entry["page"], edition=until, credit=f"© OpenStreetMap (ODbL). Datos hasta el {day(until)}.",
                          note="Lista incompleta, hecha por voluntarios. Las capas derivadas se comparten con la misma licencia.")
        else:
            source["credit"] = f"Origen de los datos: Ayuntamiento de Madrid, CC BY 4.0. Descargados el {day(downloaded)}."
        out[entry["id"]] = source
    return out


def read_sources(folder, contours):
    manifest = [entry for place in (folder, contours)
                for entry in json.loads((place / "MANIFIESTO.json").read_bytes())["files"]
                if (entry["id"] == BOUNDARIES) == (place == contours)]
    used = (RENT, SALARY, EARNERS, GRANT, SCHOOLS, POPULATION, BOUNDARIES)
    sources = {}
    for entry in manifest:
        if entry["id"] in used and not entry["file"].endswith(".meta.json"):
            sources[entry["id"]] = {"title": entry["title"], "url": entry.get("page", entry["url"]),
                                    "downloaded": entry["downloaded"][:10], "sha256": entry["sha256"],
                                    "license": entry["license"],
                                    "credit": "Contornos IDEM, CC BY 4.0 Comunidad de Madrid, convertidos a longitud y latitud"
                                    if entry["id"] == BOUNDARIES else
                                    "Origen de los datos: Comunidad de Madrid, portal de datos abiertos"}
    return {ident: sources[ident] for ident in used}


def expected_cases(municipalities, yearly):
    rents = {m["ine"]: m["rent"]["value"] for m in municipalities if m["rent"]}
    inputs = (
        ("reference_30", yearly, 30, 1),
        ("reference_40", yearly, 40, 1),
        ("reference_two_salaries_30", yearly, 30, 2),
        ("typed_24000_30", 24000, 30, 1),
        ("nothing_fits", 11640, 30, 1),  # cap 291, under the cheapest rent (291.7)
        ("rent_equal_to_cap_fits", 28000, 30, 1),
        ("one_euro_below_that_cap", 27960, 30, 1),
    )
    detached = {m["ine"] for m in municipalities if m["rent"] and m["rent"]["type"] == "detached"}
    cases = []
    for name, annual, share, earners in inputs:
        fitting = sorted(code for code, rent in rents.items() if affordable(rent, annual, share, earners))
        cases.append({"name": name, "annual_gross": annual, "share": share, "earners": earners,
                      "cap_eur_month": annual * share * earners / 1200, "affordable": fitting,
                      "affordable_count": len(fitting),
                      "affordable_detached_count": len(detached.intersection(fitting)), "with_rent": len(rents)})
    invalid = [{"annual_gross": a, "share": s, "earners": e} for a, s, e in
               ((None, 30, 1), ("", 30, 1), ("abc", 30, 1), (0, 30, 1), (-1, 30, 1),
                (24000, 0, 1), (24000, 101, 1), (24000, None, 1), (24000, 30, 0), (24000, 30, 3),
                (24000, 30, True), (24000, True, 1), (True, 30, 1))]
    return {"rule": "affordable if rent * 1200 <= annual_gross * share * earners", "cases": cases, "invalid": invalid}


def build(folder, contours=CONTOURS, province=PROVINCE, dogs=DOGS):
    sources = {**read_sources(folder, contours), **province_sources(province), **dog_sources(dogs)}
    names, boundaries = read_boundaries(contours)
    rent = read_ministry_rent(province, names)
    regional = read_rent(folder, names)
    years = {ident: int(s.get("edition", s["downloaded"])[:4]) for ident, s in sources.items()}
    years.update(dict.fromkeys(IDEM.values(), 2023))
    around, places = build_around(province, folder, dogs, contours, names, years)
    population, children = read_population(folder, names)
    early = read_early_years(folder, names, int(sources[SCHOOLS]["downloaded"][:4]))
    grant, unassigned = read_grant(folder, names)
    municipalities = [{"ine": code, "name": names[code], "rent": rent.get(code),
                       "rent_regional": regional.get(code), "around": around[code],
                       "population": population.get(code), "population_0_4": children.get(code),
                       **{kind: early[kind][code] for kind in EARLY_YEARS}, "youth_rent_grant": grant.get(code)}
                      for code in sorted(names)]
    total = read_salary_figure(folder, SALARY, "Euros")
    earners = read_salary_figure(folder, EARNERS, "Número")
    data = {
        "generated": max(s["downloaded"] for s in sources.values()),
        "sources": sources,
        "definitions": DEFINITIONS,
        "reference": {"salary": {"ages": "26-35", "year": 2024, "total_eur": total, "earners": earners,
                                 "sources": [SALARY, EARNERS], "scope": "Comunidad de Madrid",
                                 "scope_basis": "earner_residence", "scope_note": SCOPE_NOTE,
                                 "scope_evidence": SCOPE_EVIDENCE, "scope_checked": "2026-11-25"}},
        "municipalities": municipalities,
        "unassigned": {"youth_rent_grant": unassigned},
    }
    return {"municipalities.json": data, "boundaries.geojson": boundaries,
            "expected.json": expected_cases(municipalities, total / earners),
            "places.json": places, "terrain.json": build_terrain(province, boundaries)}


def main(folder=SNAPSHOT, output=OUTPUT):
    result = build(folder)
    output.mkdir(parents=True, exist_ok=True)
    for name, content in result.items():
        compact = name.endswith(".geojson") or name in ("places.json", "terrain.json")
        style = {"separators": (",", ":")} if compact else {"indent": 1}
        text = json.dumps(content, ensure_ascii=False, allow_nan=False, **style) + "\n"
        (output / name).write_text(text, encoding="utf-8")
        print(f"{name}: {len(text.encode())} bytes")
    municipalities = result["municipalities.json"]["municipalities"]
    for field in ("rent", "rent_regional", "population", "population_0_4", *EARLY_YEARS, "youth_rent_grant"):
        print(f"{field}: {sum(m[field] is not None for m in municipalities)} of {len(municipalities)} with data")
    places = result["places.json"]
    for key in LAYERS:
        figures = [m["around"][key] for m in municipalities if m["around"][key]]
        print(f"{key}: total {sum(f['value'] for f in figures)}, municipalities with data {len(figures)}, with zero "
              f"{sum(f['value'] == 0 for f in figures)}, outside own outline {places['outside_own_outline'][key]}, "
              f"without point {places['without_point'][key]}")
    terrain = result["terrain.json"]
    print(f"terrain: {terrain['width']} x {terrain['height']}, origin {terrain['origin']}, step {terrain['step']}")
    for case in result["expected.json"]["cases"]:
        print(f"{case['name']}: cap {case['cap_eur_month']:.2f}, {case['affordable_count']} of {case['with_rent']}")


if __name__ == "__main__":
    if sys.argv[1:]:
        raise SystemExit("build.py takes no arguments")
    main()
