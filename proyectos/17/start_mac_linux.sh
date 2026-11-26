#!/bin/sh
set -eu
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
    echo "Instala Python 3.10 o superior y vuelve a ejecutar este archivo." >&2
    exit 1
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else "Se requiere Python 3.10 o superior")'
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
exec .venv/bin/python app.py "$@"
