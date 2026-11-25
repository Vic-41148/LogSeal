# 05. Task: witness.py (Person 2)

A tiny independent vault. Stdlib only (`http.server.ThreadingHTTPServer`, `json`, `threading`, `argparse`). Two jobs in one file: **server** (`python witness.py --name "Vault 1" --port 8101`) and **client helpers** that `seal.py` and `verify.py` import. API is in `03_CONTRACT.md`.

## Server
1. Load `witness_<name>.jsonl` at start (name slugged). Keep entries in a list, protect with a `threading.Lock`.
2. `POST /append` rules, exactly as the contract. Persist each accepted entry with fsync. A `409 CONFLICT` is also appended to an in-memory + file `conflicts` log with time, seq, stored hash and offered hash.
3. `GET /head`, `GET /entry/{seq}`, `POST /reset` (only with `--allow-reset`).
4. `GET /` serves a self-contained HTML page with `<meta http-equiv="refresh" content="2">`:
   - big vault name, "Records held: N", "Latest fingerprint: first 8 hex chars"
   - green strip "ALL RECORDS CONSISTENT" normally
   - if conflicts exist: red strip "REWRITE ATTEMPT REJECTED" with the seq and the two short hashes, newest first
   - readable from 3 metres: large font, light background, saturated red/green
   This page is part of the demo. The audience should be able to look at a vault laptop and see it update on its own.
5. Bind `0.0.0.0`. Print the URL on start. Suppress noisy request logging.

## Client helpers
- `push(entry, cfg)`: POST to every witness, timeout from `cfg["witness_timeout_s"]`, catch every exception, return the list of results. Never raise, never block longer than timeout per witness. Use threads so two vaults are contacted in parallel.
- `head(url, timeout)`, `entry(url, seq, timeout)`: return the JSON dict or `None` on any failure.

## Acceptance
- start two vaults on one machine (`--port 8101`, `--port 8102`), `curl` each endpoint
- append seq 1..5, then re-offer seq 3 with a different hash -> `409`, status page turns red, restart the vault -> conflict history and entries are still there
- kill a vault mid-run: `push` returns quickly with `ok:false`
- check firewall: from another laptop `curl http://<vault-ip>:8101/head` works (Windows needs an inbound rule for the port)
