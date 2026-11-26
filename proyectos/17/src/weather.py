"""Previsiones municipales de Open-Meteo. Lectura offline y actualización explícita."""
from __future__ import annotations

import csv
import json
import math
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
POINTS = ROOT / "data" / "processed" / "municipios.csv"
SEED = ROOT / "data" / "weather" / "open-meteo-2026-11-25.json"
CACHE = ROOT / ".cache" / "weather.json"
API = "https://api.open-meteo.com/v1/forecast"
FIELDS = {
    "tmax": ("temperature_2m_max", "°C"),
    "tmin": ("temperature_2m_min", "°C"),
    "rh": ("relative_humidity_2m_min", "%"),
    "rain": ("precipitation_sum", "mm"),
    "wind": ("wind_speed_10m_max", "km/h"),
    "gust": ("wind_gusts_10m_max", "km/h"),
    "vpd": ("vapour_pressure_deficit_max", "kPa"),
}
LOCK = threading.Lock()


def madrid_date(now):
    # Regla europea vigente desde 1996. También funciona en Windows sin tzdata.
    def transition(month):
        last = datetime(now.year, month, 31, 1, tzinfo=timezone.utc)
        return last - timedelta(days=(last.weekday() + 1) % 7)

    offset = 2 if transition(3) <= now < transition(10) else 1
    return (now.astimezone(timezone.utc) + timedelta(hours=offset)).date()


def dates_from(start, length=7):
    return [(start + timedelta(days=i)).isoformat() for i in range(length)]


def read_cache():
    for path in (CACHE, SEED):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("schema") == 1 and isinstance(value.get("locations"), dict):
                return value
        except (ValueError, OSError, AttributeError):
            continue
    return {"schema": 1, "locations": {}}


def snapshot(now=None, cache=None):
    now = now or datetime.now(timezone.utc)
    data = read_cache() if cache is None else cache
    today = madrid_date(now)
    valid_dates = dates_from(today)
    available = set()
    for days in data["locations"].values():
        available.update(days)
    archived = bool(available) and not available.intersection(valid_dates)
    if archived:
        last = date.fromisoformat(max(available))
        valid_dates = dates_from(last - timedelta(days=6))
    locations = {
        ine: {day: days[day] for day in valid_dates if day in days}
        for ine, days in data["locations"].items()
        if any(day in days for day in valid_dates)
    }
    return {
        "dates": valid_dates, "locations": locations, "archived": archived,
        "source": "Open-Meteo · Best Match", "checked_at": data.get("checked_at"),
        "issues": data.get("issues", []), "now": now.isoformat(),
    }


def point_batches():
    with POINTS.open(encoding="utf-8-sig", newline="") as f:
        points = []
        for row in csv.DictReader(f):
            ine = row.get("cod_ine") or row.get("ine")
            lat, lon = float(row["lat"]), float(row["lon"])
            if ine and 39 < lat < 42 and -5 < lon < -2:
                points.append((ine, lat, lon))
    return [points[i:i + 18] for i in range(0, len(points), 18)]


def request_batch(points):
    params = {
        "latitude": ",".join(f"{p[1]:.5f}" for p in points),
        "longitude": ",".join(f"{p[2]:.5f}" for p in points),
        "daily": ",".join(name for name, _ in FIELDS.values()),
        "past_days": 3, "forecast_days": 7, "timezone": "Europe/Madrid",
        "wind_speed_unit": "kmh", "temperature_unit": "celsius", "precipitation_unit": "mm",
    }
    req = Request(API + "?" + urlencode(params), headers={"User-Agent": "FireRisk-Madrid/1.0"})
    for attempt in range(2):
        try:
            with urlopen(req, timeout=12) as resp:
                return json.load(resp)
        except HTTPError as exc:
            if exc.code < 500 or attempt:
                raise
        except (URLError, TimeoutError, ConnectionError):
            if attempt:
                raise
        time.sleep(0.6)


def parse_location(payload, fetched_at, start):
    daily, units = payload.get("daily", {}), payload.get("daily_units", {})
    if not isinstance(daily, dict) or not isinstance(units, dict):
        return {}
    source_days = daily.get("time")
    if not isinstance(source_days, list) or len(set(source_days)) != len(source_days):
        return {}
    horizon = dates_from(start)
    output, rains = {}, {}
    for index, day in enumerate(source_days):
        values = {}
        for key, (field, unit) in FIELDS.items():
            series = daily.get(field)
            v = series[index] if isinstance(series, list) and index < len(series) else None
            ok = type(v) in (int, float) and math.isfinite(v) and units.get(field) == unit
            if ok and key in {"vpd", "wind", "gust", "rain"}:
                ok = v >= 0
            if ok and key == "rh":
                ok = 0 <= v <= 100
            values[key] = v if ok else None
        rains[day] = values["rain"]
        if day in horizon and any(v is not None for v in values.values()):
            output[day] = dict(values, fetched_at=fetched_at)
    for day, values in output.items():
        prev = dates_from(date.fromisoformat(day) - timedelta(days=3), 3)
        values["rain3"] = round(sum(rains[d] for d in prev), 2) if all(rains.get(d) is not None for d in prev) else None
    return output


def collect(points, now, fetcher):
    records, errors = {}, []
    try:
        batch = fetcher(points)
        if isinstance(batch, dict):
            batch = [batch]
        if not isinstance(batch, list):
            raise ValueError("formato")
        for i, item in enumerate(batch):
            if not isinstance(item, dict):
                continue
            index = item.get("location_id", i if len(batch) == len(points) or i == 0 else None)
            if type(index) is not int or not 0 <= index < len(points):
                continue
            ine, lat, lon = points[index]
            try:
                if abs(item["latitude"] - lat) > 0.25 or abs(item["longitude"] - lon) > 0.25:
                    continue
                days = parse_location(item, now.isoformat(timespec="seconds"), madrid_date(now))
            except (TypeError, ValueError, KeyError):
                continue
            if days:
                records[ine] = days
        missing = len(points) - len(records)
        if missing:
            errors.append(f"{missing} punto(s) sin respuesta utilizable")
    except HTTPError as exc:
        errors.append(f"{len(points)} puntos · HTTP {exc.code}")
    except (OSError, ValueError, TypeError):
        errors.append(f"{len(points)} puntos · servicio inaccesible o respuesta inválida")
    return records, errors


def refresh(now=None, fetcher=request_batch):
    now = now or datetime.now(timezone.utc)
    if not LOCK.acquire(blocking=False):
        result = snapshot(now)
        result["notice"] = "Hay una actualización en curso."
        return result
    try:
        cache = read_cache()
        last = cache.get("checked_at")
        if last:
            elapsed = (now - datetime.fromisoformat(last)).total_seconds()
            ttl = 600 if cache.get("issues") else 10800
            if 0 <= elapsed < ttl and madrid_date(now) == madrid_date(datetime.fromisoformat(last)):
                result = snapshot(now, cache)
                result["notice"] = "Copia local reciente. Puedes consultar su hora de descarga."
                return result
        batches = point_batches()
        if not batches:
            raise ValueError("No hay coordenadas municipales válidas.")
        today = madrid_date(now).isoformat()
        locations = cache["locations"]
        issues, received = [], {}
        with ThreadPoolExecutor(max_workers=2) as pool:
            for records, errors in pool.map(lambda pts: collect(pts, now, fetcher), batches):
                received.update(records)
                issues.extend(errors)
        if received:
            for ine, days in list(locations.items()):
                locations[ine] = {d: row for d, row in days.items() if d >= today}
            for ine, days in received.items():
                locations.setdefault(ine, {}).update(days)
        cache.update(checked_at=now.isoformat(timespec="seconds"), issues=issues)
        try:
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            temp = CACHE.with_suffix(f".{os.getpid()}.tmp")
            temp.write_text(json.dumps(cache, ensure_ascii=False, allow_nan=False, separators=(",", ":")), encoding="utf-8")
            temp.replace(CACHE)
        except OSError:
            issues.append("Copia de esta consulta disponible solo en memoria de la página")
        return snapshot(now, cache)
    finally:
        LOCK.release()
