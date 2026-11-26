"""Servidor local de FireRisk Madrid. La demostración usa la biblioteca estándar."""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from shutil import copyfileobj
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
PUBLIC = ("web", "data/processed", "data/metadata", "results", "models", "docs", "sources/egif")
EXTENSIONS = {".html", ".css", ".js", ".csv", ".geojson", ".json", ".md", ".pdf",
              ".png", ".svg", ".woff2", ".txt", ".xlsx"}
MIME = {".js": "text/javascript", ".geojson": "application/geo+json",
        ".csv": "text/csv", ".md": "text/plain"}


def public_file(url_path):
    path = unquote(urlsplit(url_path).path)
    path = "web/index.html" if path == "/" else path.lstrip("/")
    candidate = (ROOT / path).resolve()
    if candidate.suffix.lower() not in EXTENSIONS:
        return None
    if not any(candidate.is_relative_to(ROOT / folder) for folder in PUBLIC):
        return None
    return candidate if candidate.is_file() else None


class Handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        super().end_headers()

    def send_json(self, value, status=HTTPStatus.OK, head=False):
        body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def do_GET(self, head=False):
        path = urlsplit(self.path).path
        if path == "/api/weather":
            from src import weather
            return self.send_json(weather.snapshot(), head=head)
        file = public_file(self.path)
        if file is None:
            self.send_error(404)
            return
        mime = MIME.get(file.suffix, mimetypes.guess_type(file.name)[0] or "application/octet-stream")
        with file.open("rb") as stream:
            self.send_response(200)
            self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith("text/") else ""))
            self.send_header("Content-Length", str(file.stat().st_size))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            if not head:
                copyfileobj(stream, self.wfile)

    def do_HEAD(self):
        self.do_GET(head=True)

    def do_POST(self):
        if urlsplit(self.path).path != "/api/weather/refresh":
            self.send_error(404)
            return
        origin = self.headers.get("Origin")
        host = self.headers.get("Host", "")
        if origin and urlsplit(origin).netloc != host:
            self.send_error(403)
            return
        from src import weather
        try:
            self.send_json(weather.refresh())
        except (OSError, ValueError, RuntimeError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.SERVICE_UNAVAILABLE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as error:
        sys.exit(f"No se puede abrir el puerto {args.port}. Prueba --port 8502. {error}")
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"FireRisk Madrid · {url} · Ctrl+C para salir", flush=True)
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
