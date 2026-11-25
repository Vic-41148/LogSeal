# 04. Task: seal.py and verify.py (Person 1, the core)

Everything depends on you. Read `03_CONTRACT.md` twice. Stdlib only. Write the mutation tests FIRST, then make them pass.

## Part A: seal.py (about 20-30 min)
1. `load_config`, `get_key`.
2. `append(evt, cfg)`:
   - read last ledger entry (or genesis) to get `seq` and `prev`. Do not keep counters in memory; the process may restart.
   - build canonical `line`, `lhash`, `hash`, `mac` exactly as in the contract
   - **write the log line first, flush + fsync, then the ledger entry, flush + fsync**
   - then `witness.push(entry, cfg)`. Never block the demo on a slow or dead vault.
   - use an `fcntl`/`msvcrt`-free approach: a single writer process is assumed. Do not add locks.
3. `reset(cfg)`: truncate both files, POST `/reset` to vaults (ignore failures).
4. `resync(cfg)` (SHOULD): if `push` gets a `422 GAP`, replay ledger entries from the vault's `count+1` upward.
5. Until `witness.py` exists, stub the import: `try: import witness except ImportError: witness = None`.

## Part B: verify.py (about 20-30 min)
Never parse log lines to verify them. Read the file in binary mode, split on `b"\n"`, re-open the path on every call and hold no handles (editors save atomically, Windows locks files).

Algorithm:
1. `L` = sha256 of each raw log line. `G` = ledger `lhash` list. Also validate each ledger entry: `seq` sequence, `prev` linkage, `mac` via `hmac.compare_digest`. Failures -> `LEDGER_FORGED`.
2. Find first index `f` where `L[f] != G[f]` in the common prefix.
   - none, `len(L) < len(G)` -> `TRUNCATE` (log lost lines), seq = `len(L)+1`
   - none, `len(L) > len(G)` -> unsealed trailing lines. **Pending rule:** keep first-seen time in a small state file (`.verify_state.json`). `status = PENDING` for `pending_grace_s` seconds, then `UNSEALED` finding. This avoids the writer/verifier race.
   - `L[f+1:] == G[f:]` -> `INSERT` at seq f+1
   - `L[f:] == G[f+1:]` -> `DELETE` at seq f+1
   - `L[f+1:] == G[f+1:]` -> `EDIT` at seq f+1
   - otherwise -> `EDIT` at seq f+1, detail says "multiple records differ" (reorder lands here)
3. Plain-English `detail` for each, written for non-technical viewers ("Record 412 was changed after it was sealed.").
4. Vault checks (if `use_witnesses`): for each vault call `witness.head()`.
   - unreachable -> node `reachable:false`, `agrees:null`, no finding
   - `vault.count > len(G)` -> `WITNESS_AHEAD` (the server lost records the vault remembers)
   - else compare `vault.hash` with ledger `hash` at `vault.count`. Mismatch -> `WITNESS_CONFLICT`; locate the first bad seq by binary search with `witness.entry()`. `expected` = vault hash, `actual` = server ledger hash.
   - for every local finding, fill `confirmed_by` with vaults whose entry at that seq equals the ledger `hash`.
5. Build `nodes`, `feed` (last 50, lenient parse), `status` (`TAMPERED` if any finding, else `PENDING` if pending, else `OK`).
6. `python verify.py --watch`: loop once per second, print `OK` green / `TAMPERED` red with class + seq. This is the terminal fallback if Streamlit fails.

## Mutation tests (write first, `python seal.py --selftest` or a `test_core.py` only if the human agrees to one extra file)
Seal 50 events, copy files to a temp dir, then each case must produce the stated class:
| Mutation | Expected |
|---|---|
| change one character in a line | `EDIT` at that seq |
| add one space inside a line | `EDIT` (whitespace must alarm) |
| delete a middle line | `DELETE` |
| insert a new line in the middle | `INSERT` |
| drop the last 5 lines | `TRUNCATE` |
| swap two adjacent lines | `EDIT`, status TAMPERED |
| edit a ledger entry's hash | `LEDGER_FORGED` |
| edit log + ledger with the key, re-chain from seq 20, vault running | `WITNESS_CONFLICT` |
| truncate log + ledger consistently, vault running | `WITNESS_AHEAD` |
| append one line then verify immediately | `PENDING`, then clean after `seal` catches up |
| no tampering at all, 200 verify calls during live appends | **zero** false alarms |

## Acceptance
- all rows above pass; the last two lines of the table are the demo killers, test them hardest
- `verify()` on 1,000 events takes well under 1 second
- a judge-style manual edit in a text editor is flagged on the next call
