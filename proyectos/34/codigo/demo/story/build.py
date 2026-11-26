import html, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
m = json.loads((DATA / "municipalities.json").read_text())
expected = json.loads((DATA / "expected.json").read_text())
towns, src, ref = m["municipalities"], m["sources"], m["reference"]["salary"]

salary = ref["total_eur"] / ref["earners"]
def fits(t, share, earners=1): return t["rent"] is not None and t["rent"]["value"] * 1200 <= salary * share * earners
with_rent = [t for t in towns if t["rent"]]
no_rent = [t for t in towns if not t["rent"]]
detached = [t for t in with_rent if t["rent"]["type"] == "detached"]
fit = {k: sum(fits(t, *a) for t in towns) for k, a in {"30": (30,), "40": (40,), "two": (30, 2)}.items()}
cases = {c["name"]: c["affordable_count"] for c in expected["cases"]}
assert (fit["30"], fit["40"], fit["two"]) == (cases["reference_30"], cases["reference_40"], cases["reference_two_salaries_30"]), (fit, cases)
assert len(with_rent) == expected["cases"][0]["with_rent"]

def eur(v): return f"{v:,.0f}".replace(",", ".")
def cap(share, earners=1): return eur(int(salary * share * earners / 1200))
def esc(s): return html.escape(str(s), quote=True)

FIELD = {"rent": "alquiler mediano por municipio", "rent_regional": "alquiler medio de los municipios de más de 20.000 habitantes (solo en la ficha)",
         "population": "habitantes por municipio", "population_0_4": "población de 0 a 4 años", "nurseries": "escuelas infantiles",
         "private_early_centres": "centros privados de primer ciclo, contados aparte", "youth_rent_grant": "solicitudes del bono, aceptadas y rechazadas",
         "health_centres": "centros de salud y consultorios", "pharmacies": "farmacias", "schools": "colegios e institutos",
         "sports": "instalaciones deportivas", "cultural": "centros culturales", "parks": "parques y zonas recreativas",
         "bus_stops": "paradas de autobús interurbano", "metro_stations": "estaciones de metro", "rail_stations": "estaciones de Cercanías",
         "light_rail_stops": "paradas de metro ligero y tranvía", "vets": "centros veterinarios", "dog_areas": "áreas caninas"}
use, years = {}, {}
for t in towns:
    for k, v in [*((k, t[k]) for k in t if isinstance(t[k], dict) and k != "around"), *t["around"].items()]:
        if isinstance(v, dict) and v.get("source"):
            use.setdefault(v["source"], set()).add(k)
            if v.get("year"): years.setdefault(v["source"], set()).add(v["year"])
for s in ref["sources"]:
    use.setdefault(s, set()).add("salary"); years.setdefault(s, set()).add(ref["year"])
FIELD["salary"] = f"salario medio de {ref['ages']} años: suma de salarios entre número de asalariados"
use.setdefault("idem-unid-admin", set()).add("outline"); FIELD["outline"] = "contorno de cada municipio para dibujar el mapa"
use.setdefault("relieve-ign-200", set()).add("terrain"); FIELD["terrain"] = "altura del terreno para el relieve del inicio"

def publisher(k, s):
    if k.startswith("crtm"): return "Consorcio Regional de Transportes de Madrid"
    if "datos.madrid.es" in s["url"]: return "Ayuntamiento de Madrid"
    if "openstreetmap.org" in s["url"]: return "Colaboradores de OpenStreetMap"
    if "mivau" in s["url"]: return "Ministerio de Vivienda y Agenda Urbana"
    if "idee.es" in s["url"]: return "Instituto Geográfico Nacional"
    if "comunidad.madrid" in s["url"]: return "Comunidad de Madrid"
    return "pendiente"
def year(k):
    y = sorted(years.get(k, []))
    return "–".join(map(str, (y[0], y[-1]) if len(y) > 1 else y)) if y else "pendiente"

boxes = []
for n, (k, s) in enumerate(src.items(), 1):
    what = "; ".join(FIELD.get(f, f) for f in sorted(use.get(k, []), key=lambda f: list(FIELD).index(f) if f in FIELD else len(FIELD))) or "pendiente"
    note = f'<p class="story-letter-note">{esc(s["note"])}</p>' if s.get("note") else ""
    boxes.append(f'''<li><details class="story-box">
<summary><span class="story-box-front" aria-hidden="true"><span class="story-box-plate">{n}</span><span class="story-box-slot"><span class="story-box-flap"></span></span></span>
<span class="story-box-title">{esc(s["title"])}</span>
<span class="story-box-who">{esc(publisher(k, s))} · {"dato de " + esc(year(k)) if year(k) != "pendiente" else "fecha del dato: pendiente"}</span></summary>
<div class="story-letter">
<p class="story-letter-what"><b>Qué sacamos:</b> {esc(what)}</p>
<dl><div><dt>Licencia</dt><dd>{esc(s["license"])}</dd></div>
<div><dt>Crédito</dt><dd>{esc(s["credit"])}</dd></div></dl>{note}
<a class="story-src" href="{esc(s["url"])}">Abrir la fuente<span class="story-sr"> de {esc(s["title"])}</span></a>
</div></details></li>''')
publishers = sorted({publisher(k, s) for k, s in src.items()})

order = sorted(towns, key=lambda t: (t["rent"] is None, t["rent"]["value"] if t["rent"] else 0, t["name"]))
COLS, W, H, GX, GY = 15, 30, 40, 12, 22
wins = []
for i, t in enumerate(order):
    x, y = (i % COLS) * (W + GX), (i // COLS) * (H + GY)
    state = "none" if not t["rent"] else "fit" if fits(t, 30) else "off"
    label = f'{t["name"]}: ' + ("sin dato de alquiler" if state == "none" else f'{eur(t["rent"]["value"])} € al mes, {"entra" if state == "fit" else "no entra"} en {cap(30)} €')
    glass = f'<rect class="story-w-glass" width="{W}" height="{H}"/>'
    inner = {"fit": f'<path class="story-w-mull" d="M{W/2} 0V{H}M0 {H*.45}H{W}"/><rect class="story-w-roll" width="{W}" height="7"/>',
             "off": f'<rect class="story-w-blind" width="{W}" height="{H}"/>', "none": ""}[state]
    rail = f'<rect class="story-w-rail" x="-2" y="{H-13}" width="{W+4}" height="13"/>' if state != "none" else ""
    pot = f'<rect class="story-w-pot" x="{W-9}" y="{H-20}" width="7" height="7"/><circle class="story-w-leaf" cx="{W-5.5}" cy="{H-22}" r="5"/>' if state != "none" and i % 11 == 4 else ""
    wins.append(f'<g class="story-w story-w-{state}" transform="translate({x} {y})"><title>{esc(label)}</title>{glass}{inner}<rect class="story-w-frame" width="{W}" height="{H}"/>{rail}{pot}<rect class="story-w-sill" x="-3" y="{H}" width="{W + 6}" height="4"/></g>')
rows = -(-len(order) // COLS)
walls = f'<rect class="story-wall" x="-8" y="-8" width="{COLS * (W + GX) + 4}" height="{rows * (H + GY) + 6}"/>' + "".join(f'<rect class="story-impost" x="-8" y="{r * (H + GY) + H + 8}" width="{COLS * (W + GX) + 4}" height="3"/>' for r in range(rows))
grid = f'<svg class="story-grid" viewBox="-8 -8 {COLS * (W + GX) + 4} {rows * (H + GY) + 6}" role="img" aria-labelledby="story-grid-t"><title id="story-grid-t">Fachada de {len(towns)} ventanas, una por municipio, ordenadas de alquiler más bajo a más alto. {fit["30"]} encendidas, {len(with_rent) - fit["30"]} apagadas y {len(no_rent)} tapiadas sin dato.</title><defs><pattern id="story-rail" width="5" height="13" patternUnits="userSpaceOnUse"><path d="M0 1H5M2.5 1V13" stroke="#9fb0bd" stroke-width="1.2"/></pattern><pattern id="story-brick" width="10" height="6" patternUnits="userSpaceOnUse"><rect width="10" height="6" fill="#2a3644"/><path d="M0 .5H10M0 3.5H10M3 .5V3.5M8 3.5V6.5" stroke="#4a5a6b" stroke-width="1"/></pattern></defs>{walls}{"".join(wins)}</svg>'

def flaps(n): return "".join(f'<span class="story-flap">{c}</span>' for c in str(n))
dogs = sum(1 for t in towns if any((t["around"].get(k) or {}).get("value") for k in ("dog_areas", "vets")))
pets = " y, si vas con perro, áreas caninas y veterinarios" if dogs else ""
values = {
    "flaps30": flaps(fit["30"]), "pets": pets,
    "salary": eur(salary), "salary_year": ref["year"], "ages": ref["ages"].replace("-", " a "),
    "cap30": cap(30), "cap40": cap(40), "cap_two": cap(30, 2), "fit30": fit["30"], "fit40": fit["40"], "fit_two": fit["two"],
    "with_rent": len(with_rent), "total": len(towns), "no_rent": len(no_rent), "off30": len(with_rent) - fit["30"],
    "no_rent_names": esc(", ".join(t["name"] for t in sorted(no_rent, key=lambda t: t["name"])) ),
    "detached": len(detached), "n_sources": len(src), "n_publishers": len(publishers), "publishers": esc(", ".join(publishers)),
    "mivau_license": esc(src["alquiler-mivau"]["license"]), "boxes": "\n".join(boxes), "grid": grid, "map_href": "#map",
}
fragment = re.sub(r"\{\{(\w+)\}\}", lambda g: str(values[g[1]]), (HERE / "story.html").read_text())
assert "{{" not in fragment
(HERE / "story.built.html").write_text(fragment)
page = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Prueba: historia bajo el inicio</title>
<style>body{{margin:0;background:#08121c}}.hero-stub{{height:100vh;display:grid;place-items:center;color:#eef4f2;font:900 9vw "Avenir Next Condensed","Arial Narrow",sans-serif;text-transform:uppercase}}#map{{height:60vh;color:#eef4f2;display:grid;place-items:center;font:24px "Avenir Next",system-ui}}</style>
<link rel="stylesheet" href="story.css"></head><body><div class="hero-stub" aria-hidden="true">Aquí va el inicio</div>
{fragment}
<div id="map" tabindex="-1">Aquí empieza el mapa</div>
<script src="../vendor/gsap.min.js"></script><script src="../vendor/ScrollTrigger.min.js"></script><script src="story.js"></script></body></html>'''
(HERE / "prueba.html").write_text(page)
print("dog data towns", dogs)
print("story.built.html", len(fragment), "bytes; fits", fit, "no rent", len(no_rent), "sources", len(src), "publishers", len(publishers))
