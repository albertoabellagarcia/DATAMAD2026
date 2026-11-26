"""Builds the match module from demo/data/ (read only).

Outputs, next to this file:
  match.built.html  fragment for WEB: markup, CSS, JS and data inlined (MapLibre and Motion not included: the page loads demo/vendor/)
  prueba.html       standalone test page: fragment plus MapLibre inlined, opens with file://

Run: python3 -I demo/match/build.py
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
import os
DATA = Path(os.environ.get("MATCH_DATA") or HERE.parent / "data")
VENDOR = HERE.parent / "vendor"
TOLERANCE = 0.0004  # degrees, about 35 m: outlines stay recognisable at zoom 12
NAMES_KEPT = 3
OPTIONAL_LAYERS = ("vets", "dog_areas")


def simplify_ring(ring, tol):
    """Closed ring: split at the point farthest from the start, simplify both halves."""
    x0, y0 = ring[0]
    k = max(range(len(ring)), key=lambda i: (ring[i][0] - x0) ** 2 + (ring[i][1] - y0) ** 2)
    if k == 0:
        return ring
    return simplify(ring[:k + 1], tol)[:-1] + simplify(ring[k:], tol)


def simplify(points, tol):
    """Douglas-Peucker on an open line."""
    if len(points) < 4:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        (x0, y0), (x1, y1) = points[a], points[b]
        dx, dy = x1 - x0, y1 - y0
        norm = math.hypot(dx, dy) or 1e-12
        best, idx = 0.0, None
        for i in range(a + 1, b):
            x, y = points[i]
            d = abs(dy * (x - x0) - dx * (y - y0)) / norm
            if d > best:
                best, idx = d, i
        if idx is not None and best > tol:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(points, keep) if k]


def ring_area_centroid(ring):
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        f = x0 * y1 - x1 * y0
        a += f
        cx += (x0 + x1) * f
        cy += (y0 + y1) * f
    if a == 0:
        return 0.0, ring[0]
    return abs(a / 2), [round(cx / (3 * a), 5), round(cy / (3 * a), 5)]


def build():
    geo = json.loads((DATA / "boundaries.geojson").read_text())
    data = json.loads((DATA / "municipalities.json").read_text())
    places = json.loads((DATA / "places.json").read_text())
    expected = json.loads((DATA / "expected.json").read_text())
    known = {m["ine"] for m in data["municipalities"]}

    feats, centre, bbox = [], {}, {}
    for i, f in enumerate(geo["features"]):
        ine = f["properties"].get("ine")
        polys, best = [], (0, None)
        for poly in f["geometry"]["coordinates"]:
            rings = []
            for ring in poly:
                r = simplify_ring([[round(x, 5), round(y, 5)] for x, y, *_ in ring], TOLERANCE)
                if len(r) >= 4:
                    rings.append(r)
            if rings:
                polys.append(rings)
                area, c = ring_area_centroid(rings[0])
                if area > best[0]:
                    best = (area, c)
        if not polys:
            continue
        pts = [p for poly in polys for ring in poly for p in ring]
        if ine in known:
            centre[ine] = best[1]
            bbox[ine] = [min(p[0] for p in pts), min(p[1] for p in pts),
                         max(p[0] for p in pts), max(p[1] for p in pts)]
        feats.append({"type": "Feature", "id": i,
                      "properties": {"ine": ine if ine in known else None},
                      "geometry": {"type": "MultiPolygon", "coordinates": polys}})

    names = {}
    for layer, body in places["layers"].items():
        for ine, rows in body["points"].items():
            got = []
            for row in rows:
                n = row[2]
                if n and n not in got:
                    got.append(n)
                if len(got) == NAMES_KEPT:
                    break
            if got:
                names.setdefault(ine, {})[layer] = got

    munis = []
    for m in data["municipalities"]:
        r = m["rent"]
        munis.append({
            "ine": m["ine"], "name": m["name"],
            "rent": r and {k: r.get(k) for k in ("value", "year", "type", "p25", "p75", "source")},
            "around": {k: (v and v["value"]) for k, v in m["around"].items()},
            "nurseries": m["nurseries"] and m["nurseries"]["value"],
            "private_early": m["private_early_centres"] and m["private_early_centres"]["value"],
            "centre": centre.get(m["ine"]), "bbox": bbox.get(m["ine"]),
            "names": names.get(m["ine"], {}),
            # located places for the click-to-zoom list: [lon, lat, name, address] per layer
            "pts": {layer: [r[:4] for r in body["points"].get(m["ine"], [])]
                    for layer, body in places["layers"].items() if body["points"].get(m["ine"])},
        })
    for layer in OPTIONAL_LAYERS:
        if layer in places["layers"]:
            print("optional layer present:", layer)

    extra_path = DATA / "extra.json"  # optional (DATOS cambio 5): postcodes of Madrid, unemployment, income
    extra = json.loads(extra_path.read_text()) if extra_path.exists() else {}
    print("extra.json:", "present" if extra else "absent")
    for m in munis:
        m["extra"] = (extra.get("municipalities") or {}).get(m["ine"]) or {}
    payload = {
        "rule": expected["rule"],
        "layers": sorted(places["layers"].keys()),
        "definitions": data["definitions"],
        "sources": {k: {"title": v.get("title"), "credit": v.get("credit"), "license": v.get("license"), "link": v.get("link"),
                        "url": v.get("url"), "note": v.get("note")} for k, v in data["sources"].items()},
        "municipalities": munis,
        "postcodes": extra.get("madrid_postcodes") or [],
        "extra_definitions": extra.get("definitions") or {},
        "extra_sources": {k: {"title": v.get("title"), "credit": v.get("credit"), "link": v.get("link")} for k, v in (extra.get("sources") or {}).items()},
        "outlines": {"type": "FeatureCollection", "features": feats},
    }
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    css = (HERE / "match.css").read_text()
    js = (HERE / "match.js").read_text()
    html = (HERE / "match.html").read_text()
    fragment = (f"<style>{css}</style>\n{html}\n"
                f'<script type="application/json" id="match-data">{blob}</script>\n<script>{js}</script>\n')
    (HERE / "match.built.html").write_text(fragment)

    page = ("<!doctype html>\n<html lang=\"es\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>Dónde cabes: mapa que se cierra (prueba)</title>"
            f"<style>{(VENDOR / 'maplibre-gl.css').read_text()}</style>"
            f"<script>{(VENDOR / 'maplibre-gl.js').read_text()}</script>"
            f"<script>{(VENDOR / 'motion.js').read_text()}</script></head><body>\n"
            f"{fragment}"
            # Test values: the reference_30 case of expected.json (one salary, 30 %).
            "<script>window.dondeCabes.openMatch({annual:26036.840152194032,share:30,earners:1,ine:null})</script>"
            "</body></html>\n")
    (HERE / "prueba.html").write_text(page)
    n_pts = sum(len(r) for f in feats for p in f["geometry"]["coordinates"] for r in p)
    print(f"outlines: {len(feats)} features, {n_pts} points; data {len(blob)} bytes; "
          f"fragment {len(fragment)} bytes; page {len(page)} bytes")


if __name__ == "__main__":
    build()
