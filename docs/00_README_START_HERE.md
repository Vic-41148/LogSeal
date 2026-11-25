# LogSeal Agent Pack: START HERE

You are an AI coding agent helping a human team build **LogSeal** for the CodeStorm hackathon (Tech Fusion 4.0, K.R. Mangalam University, 25 Nov, build window 10:00-12:30, pitches 13:00-15:00).

LogSeal = a tamper-evident security log. Every log line is sealed into a hash chain, and a fingerprint of each record is copied to independent "vault" machines. If anyone edits, deletes or rewrites the log, a console shows a red alarm within seconds.

## Read order
1. `01_PROJECT_BRIEF.md`: what and why, constraints, honesty rules
2. `02_ARCHITECTURE.md`: components, data flow, threat model
3. `03_CONTRACT.md`: **file formats, endpoints, function signatures. This is the law.**
4. Your own task file (ask the human which one you are):
   - `04_TASK_seal_verify.md`: Person 1 (core)
   - `05_TASK_witness.md`: Person 2
   - `06_TASK_console_frontend.md`: Person 3
   - `07_TASK_gen_attack_ml_bench.md`: Person 4
5. `08_DEMO_AND_PITCH.md`: demo script, laptop roles, how to explain it
6. `09_TIMELINE_CUTS_FAILURES.md`: timeboxes, cut order, how the demo fails
7. `10_SETUP_NETWORK_RESET.md`: install, hotspot, fallback, git, reset
8. `11_CLAIMS_AND_HONESTY.md`: what may be said to judges

## Ground rules for every agent
- **Python stdlib only** for `gen.py seal.py verify.py witness.py attack.py bench.py`. Only `app.py` and `ml.py` may import third-party packages (`streamlit`, `scikit-learn`, `numpy`, `joblib`).
- **Do not change `03_CONTRACT.md`** on your own. If you think it is wrong, stop and tell the human.
- **Only edit files you own** (table below). Mock the other pieces if they are not ready.
- **Do not build** Merkle trees, quorum protocols, Drain3, embeddings, calibration, conformal prediction, OCSF, graphviz, Docker, databases. They were audited and cut. Mention them as "future work" at most.
- Keep each file small and readable (aim under 250 lines). Working beats clever.
- **Never invent numbers.** Any metric shown to judges must be printed by our own script that day.
- **Never call this a blockchain.** Say: "authenticated append-only ledger with independent witnesses, a prototype of the permissioned model".
- State lives in **files**, not in memory. Every tool must be restartable at any time.
- After each task, run the acceptance checks in your task file and report pass/fail honestly.

## File ownership
| File | Owner | Notes |
|---|---|---|
| `config.json`, `03_CONTRACT.md` | Human (shared) | Changed only by agreement |
| `seal.py`, `verify.py` | Person 1 | Core. Tests first. |
| `witness.py` | Person 2 | Server and client API in one file |
| `app.py` | Person 3 | Streamlit console |
| `gen.py`, `attack.py`, `ml.py`, `bench.py` | Person 4 | `gen.py` first, others wait on it |

## Definition of done (project level)
1. Events flow, all machines agree, console is green.
2. A manual edit of `app.log.jsonl` makes the console red within about 3 seconds, naming the record number.
3. `attack.py rewrite` (log + ledger rewritten with the key) leaves the server tile green but the vaults reject it, the vault tiles turn red, and the banner is red.
4. `reset` returns everything to a clean green state in under 30 seconds.
5. The full demo has been rehearsed twice.
