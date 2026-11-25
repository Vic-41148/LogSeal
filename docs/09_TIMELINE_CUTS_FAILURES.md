# 09. Timeline, Cut List, Failure Prevention

## Before 10:00 (09:00-10:00, setup, not coding)
- Ask the Technical Head: team size cap, pre-built code policy, **AI coding assistant policy**, pitch length, one or per-track winner, power/WiFi/HDMI.
- Install: `pip install streamlit scikit-learn joblib` on every laptop. Check `python --version` (recent scikit-learn needs Python 3.11+). Install whatever pip resolves; do not pin versions.
- Hotspot up, **laptop-to-laptop connectivity tested**, firewall ports opened on vault laptops.
- 10:00-10:10: read `03_CONTRACT.md` together, agree on the vault IPs, write `config.json`.

## Build window
| Time | Milestone | Working check |
|---|---|---|
| 10:00-10:10 | Contract and config agreed, `gen.py` started | everyone has the same repo |
| 10:10-10:50 | Parallel builds against the contract: P1 seal+verify, P2 witness, P3 console on mock, P4 gen then attack | each person passes their own acceptance list |
| 10:50-11:10 | Integrate with one vault on localhost, then real vaults over the network | green end to end |
| 11:10-11:40 | Tamper tests: edit, delete, truncate, rewrite-both, wipe. Judge-edit rehearsal. | all tests behave per `08_DEMO_AND_PITCH.md` |
| 11:40-12:15 | `ml.py` metrics, `bench.py` if time, console polish, 4-slide deck | `metrics.json`, `bench.json` exist |
| 12:15-12:30 | **Code freeze.** Two timed rehearsals. | demo runs cleanly twice |
| 12:30-13:00 | Break: phone video of a clean run, rehearse again, fallback switch drill. No code edits after 12:50. | |
Budget reality: the core pieces (seal, verify, console, generator, ML) add up to about 130 pessimistic minutes of single-person work. Parallel work is what makes the window; do not add scope.

## Cut list (in this order when behind)
1. `bench.py` -> show one live tamper instead of a mutation table
2. Activity chart in console
3. Before/after diff in the alarm box (keep banner + tiles)
4. Auto-refresh -> "Verify now" button
5. sklearn ML -> simple rarity/fail-streak score labelled "statistical, not ML"
6. `gen.py --attack burst` -> pre-labeled dataset only
7. `attack.py` (say so on the slide)
8. Vaults -> one vault, then localhost fallback
**Never cut:** seal + ledger, verifier alarm, judge-edit moment, the three machine tiles.

## How the live demo fails, and prevention
| Failure | Prevention |
|---|---|
| Generator appends while the judge edits (race) | Stop `gen.py` first, wait 3 seconds, then hand over the laptop |
| False alarm because the verifier saw an unsealed trailing line | Log written before ledger; verifier reports `PENDING` for `pending_grace_s` before alarming |
| Whitespace-only edit not detected | Verifier hashes raw bytes, never re-dumped JSON |
| Judge breaks JSON syntax | Verifier never parses lines; console wraps each row in try/except |
| Streamlit rerun wipes state | All state in files, none in `session_state` |
| Hotspot isolates clients / firewall blocks vault port | Test at 09:00; fallback `config.local.json` with all vaults on localhost, rehearsed once |
| A vault laptop dies mid-demo | Tile goes grey "OFFLINE", console keeps running; act 3 still works with the other vault |
| Editor atomic-save or Windows file lock | Verifier reopens the path every pass and holds no handles |
| Two generators running | Launch from terminal only |
| Streamlit fails entirely | `python verify.py --watch` terminal alarm on the projector |
| Projector dead | Circle the laptops, show the vault status pages; play the phone video |
| Version drift (pip resolves something new) | Test the console fragment API on the day; fall back to the button |
| Clocks differ across laptops | Never compare timestamps across machines; use seq and hashes only |
