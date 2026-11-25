# LogSeal: base project

Tamper-evident security log. Every event is sealed into a hash chain; a fingerprint of each record is copied to independent vault machines. Edit or delete the log and the console goes red. Full spec is in `docs/` (start with `00_README_START_HERE.md`, the contract is `03_CONTRACT.md`).

## Status
| File | State |
|---|---|
| `seal.py`, `verify.py`, `witness.py` | done. `python seal.py --selftest` runs 20 checks (every contract mutation, live-append false alarms, vault rewrite and wipe) |
| `gen.py`, `attack.py`, `bench.py`, `ml.py` | done, tested |
| `app.py` | done, smoke-tested (3 mock states, real verify, offline vault). Check it on the projector yourselves |
| `metrics.json`, `bench.json` | not shipped. Run the scripts on the day and quote only their output |

## Setup
```
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                        # vault laptops need Python only
python seal.py --selftest                              # sanity check
```
Put the vault IPs in `config.json`. Use `--config config.local.json` on every tool for the one-laptop fallback.

## Run
```
python witness.py --name "Vault 1" --port 8101 --allow-reset    # each vault (Vault 2 on 8102 in fallback)
export LOGSEAL_KEY=anything-same-everywhere                     # Windows: set LOGSEAL_KEY=...
python gen.py --rate 2                                          # victim server
streamlit run app.py --server.port 8501                         # control room (?stage=1 for projector)
python verify.py --watch                                        # terminal fallback console
```
Demo: stop `gen.py`, wait 3 s, edit a line of `app.log.jsonl` -> red. Then `python attack.py rewrite --seq 120` -> server tile green, vault tiles red. `python gen.py --attack burst` for the ML act.

Before the pitch: `python gen.py --dataset dataset && python ml.py train && python ml.py eval && python bench.py`
Reset: stop `gen.py`, then `python attack.py restore` (after an attack) or `python seal.py --reset`.

## Notes
- `?mock=ok|edit|rewrite` on the console URL previews the three states with no backend.
- Added beyond the contract, nothing breaking: `witness.py --dir`, `witness.reset()`, `seal.rebuild_ledger()`, `seal.py --selftest/--reset`; relative paths in config resolve next to the config file.
- `LOGSEAL_CONFIG=config.local.json` makes the console use the fallback config.
