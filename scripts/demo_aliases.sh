# Short commands for the live demo.
# Source this file once: source scripts/demo_aliases.sh
# Use LOGSEAL_STACK=<name> before source to target another stack.

LOGSEAL_STACK=${LOGSEAL_STACK:-dev}
LOGSEAL_DIR=".run/$LOGSEAL_STACK"
LOGSEAL_CFG="$LOGSEAL_DIR/config.json"
LOGSEAL_LOG="$LOGSEAL_DIR/app.log.jsonl"
LOGSEAL_LED="$LOGSEAL_DIR/ledger.jsonl"
LOGSEAL_PIDS="$LOGSEAL_DIR/pids.json"
LOGSEAL_BAK="/tmp/logseal-$LOGSEAL_STACK-live.bak"
LOGSEAL_BAK_LED="/tmp/logseal-$LOGSEAL_STACK-live-ledger.bak"

_dgen_pid() {
  python3 -c "import json; print(json.load(open('$LOGSEAL_PIDS')).get('gen', ''))"
}

dshow() {
  echo "Screen:  http://100.100.12.125:8501/"
  echo "Vault 1: http://100.100.12.125:18524/"
  echo "Vault 2: http://100.100.12.125:18525/"
}

dstop() {
  local pid
  pid=$(_dgen_pid)
  if [ -n "$pid" ]; then
    kill "$pid" 2>/dev/null && echo "stopped gen $pid"
  else
    echo "gen not running"
  fi
}

dstart() {
  nohup python3 gen.py --config "$LOGSEAL_CFG" --rate 2 > "$LOGSEAL_DIR/gen.log" 2>&1 &
  local pid=$!
  python3 - "$pid" "$LOGSEAL_PIDS" <<'PY'
import json
import sys

path = sys.argv[2]
data = json.load(open(path))
data["gen"] = int(sys.argv[1])
json.dump(data, open(path, "w"), indent=2)
PY
  echo "started gen $pid"
}

dprep() {
  dstop
  sleep 3
  cp "$LOGSEAL_LOG" "$LOGSEAL_BAK"
  cp "$LOGSEAL_LED" "$LOGSEAL_BAK_LED"
  echo "backup ready"
}

dedit() {
  python3 - "$LOGSEAL_LOG" <<'PY'
import sys

path = sys.argv[1]
lines = open(path, "rb").read().split(b"\n")[:-1]
lines[119] = lines[119].replace(b'"srv-01"', b'"srv-02"', 1)
open(path, "wb").write(b"\n".join(lines) + b"\n")
print(lines[119].decode())
PY
}

dundo() {
  cp "$LOGSEAL_BAK" "$LOGSEAL_LOG"
  cp "$LOGSEAL_BAK_LED" "$LOGSEAL_LED"
  echo "restored"
}

dattack() {
  python3 attack.py rewrite --config "$LOGSEAL_CFG" --seq 120 --find grace --replace mallory
}

drestore() {
  python3 attack.py restore --config "$LOGSEAL_CFG"
}

dburst() {
  dstart
  python3 gen.py --attack burst --config "$LOGSEAL_CFG"
}

dstatus() {
  python3 - "$LOGSEAL_CFG" <<'PY'
import json
import sys

import seal
import verify

cfg = seal.load_config(sys.argv[1])
result = verify.verify(cfg)
print("status:", result["status"])
print("nodes:", [(n["name"], n["agrees"], n["head_seq"]) for n in result["nodes"]])
for finding in result["findings"][:1]:
    print("finding:", finding["class"], finding["seq"], finding.get("confirmed_by"))
PY
}

dreset() {
  python3 seal.py --reset --config "$LOGSEAL_CFG"
}

dvaults() {
  python3 - "$LOGSEAL_CFG" <<'PY'
import sys

import seal

cfg = seal.load_config(sys.argv[1])
for witness in cfg["witnesses"]:
    print(witness["url"] + "/")
PY
}
