# 13. Verification record

This file records what the base proved on one Linux machine. It is evidence, not a target list.

Environment: Linux, Python 3.14.10, localhost vaults. Date: 2026-11-25.

## Commands and results

| Command | Result |
|---|---|
| `python scripts/check_contract.py` | 38 checks pass, `CONTRACT OK` |
| `python -m unittest discover -s tests -t .` | 50 tests pass in about 5 s |
| `python seal.py --selftest` | All 20 checks pass. `verify()` on 1,000 events: 9 ms |
| `python scripts/demo_check.py` | All five acts pass |
| `python gen.py --dataset dataset` | 29,055 train events, 7,448 test events |
| `python ml.py train` | 1,440 benign training windows, threshold -0.5764 |
| `python ml.py eval` | precision 0.75, recall 1.0, F1 0.857 on 360 test windows |
| `python bench.py` | 100 mutations, 100 detected, median 1.72 ms, p95 1.77 ms |
| Browser: `?mock=ok` | Green banner, three green tiles |
| Browser: `?mock=edit` | Red banner, server ✘, both vaults ✔, record 120 named |
| Browser: `?mock=rewrite` | Red banner, server ✔, both vaults ✘ |
| Browser: real edit in `.run/verify/app.log.jsonl` | Banner flipped to red 2.33 s after the edit |

These numbers were measured by the lead on the development laptop. Every person must repeat them on the demo laptop before the pitch. `dataset/`, `metrics.json`, `bench.json` and `model.joblib` are generated files and are not committed.

## Demo acts proved by `make demo-check`

| Act | Check | Result |
|---|---|---|
| 1 | 60 sealed events, three machines agree | PASS |
| 2 | Edit record 24, both vaults confirm the original | PASS |
| 3 | Rewrite with the key: server green, two vaults red at record 20 | PASS |
| 4 | Wipe to 30 records: server green, vaults ahead at record 31 | PASS |
| 5 | Reset clears log, ledger and both vaults | PASS |

The rewrite act also printed:

```
Vault 1 REJECTED the rewrite (conflict at record 20)
Vault 2 REJECTED the rewrite (conflict at record 20)
```

A real-browser pass used Streamlit 1.67.0 on Python 3.12 with `LOGSEAL_CONFIG=.run/verify/config.json` and two live vaults. The console refresh fragment runs every 2 s; a one-line edit flipped the banner in 2.33 s. The console title line was fixed: a conditional expression rendered a Streamlit `DeltaGenerator` object as a large internal-methods table on every page load. It is now a plain `if` statement.

## Benchmark detail

```
100 mutations, 100 detected, median 1.72 ms (p95 1.83 ms)
  INSERT     18/18
  TRUNCATE   21/21
  EDIT       40/40
  DELETE     21/21
```

These are local checks on a copy of the log. Vaults are not part of this number. `bench.json` holds the same values.

## Model detail

```
trained on 1440 benign windows, threshold -0.5764
{
  "data": "synthetic, own generator",
  "train_windows": 1440,
  "test_windows": 360,
  "precision": 0.75,
  "recall": 1.0,
  "f1": 0.857,
  "threshold": -0.5764,
  "generated_at": "2026-11-25T11:04:53"
}
```

The alarm budget is the 1st percentile of benign training windows. The data is synthetic: our generator, our features, measured today. Say that to the judges. `metrics.json` holds the same values.

## Still open

| Item | Owner | Status |
|---|---|---|
| Projector readability from 3 m | P3 | Pending |
| Real-browser check of all three mock states | P3 / lead | Pending |
| Two physical vault laptops over the hotspot | P2 / lead | Pending |
| Two full rehearsals | Lead | Pending |

Do not move an item to done until the exact command output is in this file.
