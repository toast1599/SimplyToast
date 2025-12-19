#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
PYTHON_BIN="$HERE/../python3/bin/python3"

# Run silently (no debug output)
exec "$PYTHON_BIN" "$HERE/main.py" >/dev/null 2>&1
