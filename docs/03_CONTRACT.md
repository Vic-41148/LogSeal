# 03. Contract (the law: do not change without the human)

## config.json
```json
{
  "log_path": "app.log.jsonl",
  "ledger_path": "ledger.jsonl",
  "hmac_key_env": "LOGSEAL_KEY",
  "hmac_key_default": "demo-key-change-me",
  "witnesses": [
    {"name": "Vault 1", "url": "http://192.168.43.11:8101"},
    {"name": "Vault 2", "url": "http://192.168.43.12:8101"}
  ],
  "witness_timeout_s": 1.0,
  "pending_grace_s": 3
}
```
Fallback `config.local.json`: same, but witnesses are `http://127.0.0.1:8101` and `http://127.0.0.1:8102`. Every tool accepts `--config PATH` (default `config.json`).

## app.log.jsonl
One event per line, UTF-8, `\n` terminated, written with `json.dumps(evt, sort_keys=True, separators=(",", ":"))`. Event fields:
```json
{"seq":412,"ts":"2026-11-25T10:31:07","host":"srv-01","user":"alice","event":"login_fail","src_ip":"10.0.0.7","msg":"bad password"}
```
`event` is one of: `login_ok, login_fail, logout, file_read, file_write, sudo, config_change`.
`seq` is 1-based and equals the line number. The verifier must NOT depend on the `seq` field inside a line.

## ledger.jsonl
One entry per log line, same order:
```json
{"seq":412,"prev":"<64 hex>","hash":"<64 hex>","lhash":"<64 hex>","mac":"<64 hex>"}
```
- genesis `prev` = 64 zeros
- `lhash = sha256(line_bytes)` where `line_bytes` = the raw line without the trailing newline
- `hash = sha256((prev + line_str).encode())`
- `mac = HMAC-SHA256(KEY, f"{seq}:{prev}:{hash}:{lhash}")`
- KEY from env `LOGSEAL_KEY`, else `hmac_key_default`

## Witness HTTP API (port 8101 by default, `--port` overrides, binds 0.0.0.0)
| Request | Response |
|---|---|
| `POST /append` body `{"seq":int,"prev":hex,"hash":hex}` | `200 {"ok":true,"count":n}` if `seq==count+1` and `prev==head hash`<br>`200 {"ok":true,"duplicate":true}` if same seq already stored with same hash<br>`409 {"ok":false,"error":"CONFLICT","seq":n,"stored":hex,"offered":hex}` if seq exists with a different hash (also recorded in a visible conflict log)<br>`422 {"ok":false,"error":"GAP","count":n}` if seq > count+1 or prev mismatches head |
| `GET /head` | `{"name":..,"count":n,"seq":n,"hash":hex}` (empty vault: count 0, hash 64 zeros) |
| `GET /entry/{seq}` | `{"seq":n,"prev":hex,"hash":hex}` or `404` |
| `GET /` | auto-refreshing HTML status page (count, last fingerprint, conflicts) |
| `POST /reset` | clears the vault, only if started with `--allow-reset` |

Storage: `witness_<name>.jsonl` next to `witness.py`. Append-only. Reloaded on start.

## Python API

### witness.py (client helpers, importable)
```python
push(entry: dict, cfg: dict) -> list[dict]      # [{"name","ok","status","error"}], never raises, honours witness_timeout_s
head(url: str, timeout: float) -> dict | None   # None = unreachable
entry(url: str, seq: int, timeout: float) -> dict | None
```

### seal.py
```python
load_config(path="config.json") -> dict
get_key(cfg) -> bytes
append(evt: dict, cfg: dict) -> dict            # seals one event, returns the ledger entry; assigns seq itself
resync(cfg: dict) -> None                       # SHOULD: replay ledger entries a vault is missing
reset(cfg: dict) -> None                        # truncate log and ledger, tell vaults to reset
```

### verify.py
```python
verify(cfg=None, log_path=None, ledger_path=None, use_witnesses=True) -> dict
```
CLI: `python verify.py --watch` prints a coloured one-line status every second (terminal fallback console).

Return shape (**the console depends on this exactly**):
```json
{
  "status": "OK | PENDING | TAMPERED",
  "checked_at": "2026-11-25T10:31:08",
  "log_lines": 412,
  "ledger_entries": 412,
  "findings": [
    {
      "class": "EDIT | DELETE | INSERT | TRUNCATE | UNSEALED | LEDGER_FORGED | WITNESS_CONFLICT | WITNESS_AHEAD",
      "seq": 412,
      "expected": "<64 hex line fingerprint from ledger, or vault hash>",
      "actual": "<64 hex of what is in the file now, or null if missing>",
      "detail": "Record 412 was changed after it was sealed.",
      "confirmed_by": ["Vault 1", "Vault 2"]
    }
  ],
  "nodes": [
    {"name": "Server",  "role": "server", "reachable": true,  "head_seq": 412, "head_hash": "<hex>", "agrees": true},
    {"name": "Vault 1", "role": "vault",  "reachable": true,  "head_seq": 412, "head_hash": "<hex>", "agrees": true},
    {"name": "Vault 2", "role": "vault",  "reachable": false, "head_seq": null, "head_hash": null,  "agrees": null}
  ],
  "feed": [{"seq": 412, "ts": "...", "event": "login_fail", "user": "alice", "src_ip": "10.0.0.7", "ok": true}]
}
```
Rules for `nodes[].agrees`:
- **Server**: `true` if recomputing the log reproduces the server's own ledger exactly and all MACs are valid.
- **Vault**: `true` if the vault's head hash equals the server **ledger's** hash at the same seq and the vault count is not above the server's. `null` if unreachable (grey tile, never an error).
- A vault that is merely behind (count lower, matching prefix) is `agrees: true` with a smaller `head_seq`.

`feed` = last 50 lines, parsed leniently; a line that fails to parse gets `{"seq": n, "event": "UNPARSEABLE", "ok": false}`. `feed[].ok` is false for any seq mentioned in `findings`.

## metrics.json (from ml.py)
```json
{"data": "synthetic, own generator", "train_windows": 0, "test_windows": 0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "threshold": 0.0, "generated_at": "..."}
```

## bench.json (from bench.py)
```json
{"mutations": 100, "detected": 0, "by_class": {"EDIT": {"n": 0, "detected": 0}}, "latency_ms_median": 0.0, "latency_ms_p95": 0.0, "note": "local checks on a copy of the files, vaults not included"}
```
