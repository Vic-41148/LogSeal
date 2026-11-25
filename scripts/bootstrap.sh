#!/usr/bin/env bash
# One command to prepare a laptop. Safe to run again.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"
"$PYTHON" - <<'EOF'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11 or newer is required (found %s)" % sys.version.split()[0])
print("Python", sys.version.split()[0], "OK")
EOF

if [ ! -d .venv ]; then
  "$PYTHON" -m venv .venv
fi

if [ -x .venv/bin/python ]; then
  VENV_PY=.venv/bin/python
  PIP=(.venv/bin/python -m pip)
elif [ -x .venv/Scripts/python.exe ]; then
  VENV_PY=.venv/Scripts/python.exe
  PIP=(.venv/Scripts/python.exe -m pip)
else
  echo "Cannot find the virtual environment python" >&2
  exit 1
fi

"$VENV_PY" -m pip install --quiet --upgrade pip
"$VENV_PY" -m pip install --quiet -r requirements.txt -r requirements-dev.txt

echo "Checking the contract..."
"$VENV_PY" scripts/check_contract.py

echo "Running the test suite..."
"$VENV_PY" -m unittest discover -s tests -t . -q

cat <<'EOF'

Ready. Start a private stack (replace p1 with your name):
  python scripts/local_stack.py up --name p1 --with-gen --with-console
Open the console URL that the command prints. Stop it with:
  python scripts/local_stack.py down --name p1

Read TASKS.md, then your file in docs/tasks/.
EOF
