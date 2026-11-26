import base64
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
WIDTH = 1000


def ring_area(ring):
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]))


def centroid(ring):
    a = ring_area(ring)
    if a == 0:
        return ring[0]
    cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        f = x0 * y1 - x1 * y0
        cx += (x0 + x1) * f
        cy += (y0 + y1) * f
    return cx / (6 * a), cy / (6 * a)


def build_shapes(features):
    pts = [p for f in features for poly in f["geometry"]["coordinates"] for ring in poly for p in ring]
    lon0 = min(p[0] for p in pts)
    lat1 = max(p[1] for p in pts)
    k = math.cos(math.radians(sum(p[1] for p in pts) / len(pts)))
    span = (max(p[0] for p in pts) - lon0) * k
    scale = WIDTH / span
    height = (lat1 - min(p[1] for p in pts)) * scale

    def project(p):
        return round((p[0] - lon0) * k * scale, 1), round((lat1 - p[1]) * scale, 1)

    shapes = []
    for f in features:
        parts, best = [], None
        for poly in f["geometry"]["coordinates"]:
            for i, ring in enumerate(poly):
                xy = []
                for p in map(project, ring):
                    if not xy or xy[-1] != p:
                        xy.append(p)
                if len(xy) < 4:
                    continue
                parts.append("M" + "L".join(f"{x:g} {y:g}" for x, y in xy) + "Z")
                if i == 0 and (best is None or abs(ring_area(xy)) > abs(ring_area(best))):
                    best = xy
        cx, cy = centroid(best)
        shapes.append({"ine": f["properties"]["ine"], "name": f["properties"]["name"],
                       "d": "".join(parts), "label": [round(cx, 1), round(cy, 1)]})
    return {"width": WIDTH, "height": round(height, 1), "shapes": shapes,
            "proj": [lon0, lat1, k, scale], "metres_per_unit": span * 111320 / WIDTH}, project


def build_places(places, project, codes):
    layers = {}
    for name, layer in places["layers"].items():
        unknown = set(layer["points"]) - codes
        if unknown:
            sys.exit(f"places {name}: unknown municipalities {sorted(unknown)}")
        layers[name] = {ine: [[*project(p[:2]), *p[2:5]] for p in pts] for ine, pts in layer["points"].items()}
    return layers


def build_ridges(terrain, features, codes):
    order = {c: i for i, c in enumerate(codes)}
    rings = []
    for f in features:
        i = order.get(f["properties"]["ine"], -1)
        for poly in f["geometry"]["coordinates"]:
            ring = poly[0]
            xs, ys = [p[0] for p in ring], [p[1] for p in ring]
            rings.append((i, ring, min(xs), max(xs), min(ys), max(ys)))

    def owner(lon, lat):
        for i, ring, a, b, c, d in rings:
            if a <= lon <= b and c <= lat <= d:
                inside = False
                for (px, py), (qx, qy) in zip(ring, ring[1:]):
                    if (py > lat) != (qy > lat) and lon < px + (lat - py) * (qx - px) / (qy - py):
                        inside = not inside
                if inside:
                    return i
        return -1

    w, h = terrain["width"], terrain["height"]
    heights = struct.unpack(f"<{w * h}h", base64.b64decode(terrain["heights"]))
    rows = []
    for r in range(0, h, 6):
        line = []
        for c in range(0, w, 3):
            z = heights[r * w + c]
            line.append(0 if z == terrain["nodata"] else [z, owner(terrain["origin"][0] + c * terrain["step"][0], terrain["origin"][1] + r * terrain["step"][1])])
        rows.append(line)
    return rows


def main():
    municipalities = json.loads((DATA / "municipalities.json").read_text(encoding="utf-8"))
    boundaries = json.loads((DATA / "boundaries.geojson").read_text(encoding="utf-8"))
    codes = {m["ine"] for m in municipalities["municipalities"]}
    mapped = {f["properties"]["ine"] for f in boundaries["features"]} - {None}
    if codes != mapped:
        sys.exit(f"boundaries and municipalities differ: {sorted(codes ^ mapped)}")
    shapes, project = build_shapes(boundaries["features"])
    places = json.loads((DATA / "places.json").read_text(encoding="utf-8"))
    terrain = json.loads((DATA / "terrain.json").read_text(encoding="utf-8"))
    missing = set(municipalities["municipalities"][0]["around"]) - set(places["layers"])
    if missing:
        sys.exit(f"places.json lacks layers {sorted(missing)}")
    payload = {"data": municipalities, "map": shapes, "places": build_places(places, project, codes),
               "without_point": places.get("without_point", {}),
               "ridges": build_ridges(terrain, boundaries["features"], [m["ine"] for m in municipalities["municipalities"]]),
               "ridge_grid": [terrain["origin"][0], terrain["origin"][1], terrain["step"][0] * 3, terrain["step"][1] * 6]}
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    template = (HERE / "index.template.html").read_text(encoding="utf-8")
    story = HERE / "story"
    subprocess.run([sys.executable, "-I", str(story / "build.py")], check=True)
    subprocess.run([sys.executable, "-I", str(HERE / "match/build.py")], check=True)
    scripts = [f.read_text(encoding="utf-8") for f in
               (HERE / "vendor/gsap.min.js", HERE / "vendor/ScrollTrigger.min.js", story / "story.js")]
    vendor = [(HERE / f"vendor/{n}").read_text(encoding="utf-8") for n in ("maplibre-gl.js", "motion.js")]
    if any("</script" in s.lower() for s in scripts + vendor):
        sys.exit("a script contains </script")
    parts = {"<!--__STORY__-->": (story / "story.built.html").read_text(encoding="utf-8"),
             "/*__STORY_CSS__*/": (story / "story.css").read_text(encoding="utf-8"),
             "<!--__STORY_JS__-->": "".join(f"<script>{s}</script>\n" for s in scripts),
             "/*__MAPLIBRE_CSS__*/": (HERE / "vendor/maplibre-gl.css").read_text(encoding="utf-8"),
             "<!--__MATCH__-->": "".join(f"<script>{s}</script>\n" for s in vendor) + (HERE / "match/match.built.html").read_text(encoding="utf-8"),
             "__DATA__": blob}
    for key in parts:
        if template.count(key) != 1:
            sys.exit(f"template needs exactly one {key}")
    for key, value in parts.items():
        template = template.replace(key, value)
    out = HERE / "index.html"
    out.write_text(template, encoding="utf-8")
    print(f"{out.name}: {out.stat().st_size} bytes, {len(payload['map']['shapes'])} shapes, "
          f"{sum(1 for m in municipalities['municipalities'] if m['rent'])} with rent, "
          f"{sum(len(v) for layer in payload['places'].values() for v in layer.values())} places")


if __name__ == "__main__":
    main()
