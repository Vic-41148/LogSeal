# 14. Model report — handoff for review and improvement

Purpose: give another engineer (Claude) everything needed to check the burst detector and improve it without breaking the LogSeal core. Written 2026-11-25, from real script output on the development laptop.

## 1. What the model is

A **secondary feature**, not part of the integrity proof. The core promise (hash chain + independent vaults) does not depend on it. It flags a run of failed logins from one external IP in the console activity chart.

- Algorithm: `sklearn.ensemble.IsolationForest(random_state=42)` on 10 numeric features per 10 s window.
- Alarm rule: `score_samples < threshold`. Lower score means more abnormal.
- Threshold: 1st percentile of the **benign training** scores. About 1% of benign windows cross it.
- Training data: synthetic events from our own `gen.py`, not real customer logs.
- Evaluation data: a separate synthetic day with six injected bursts. Labels are per-event, then collapsed to window level with "any event in this window is an attack".
- Console use: `app.py` calls `ml.flag_windows(events)` and marks flagged windows in the 10 s chart.

## 2. Files

| Path | Committed? | Role |
|---|---|---|
| `ml.py` | Yes | Features, training, evaluation, `flag_windows()`. Safe to edit: this is your lane. |
| `gen.py` | Yes | Live event generator, `burst_events()`, and `write_dataset()` for train/test. Safe to edit. |
| `bench.py` | Yes | Mutation benchmark for the **core**, not the model. Safe to edit. |
| `app.py` | Yes | Reads `ml.flag_windows()` for the chart. Do not edit unless P3 agrees. |
| `dataset/train.jsonl` | No (generated) | 29,055 benign events from 08:00–12:00 on 2026-11-20, seed 42. |
| `dataset/test.jsonl` | No (generated) | 7,448 events from 2026-11-21 08:00–09:00 plus six ~41-event bursts. |
| `model.joblib` | No (generated) | Serialized `{"model": ..., "threshold": ...}`, 1.17 MB. |
| `metrics.json` | No (generated) | Last `ml.py eval` output. |
| `bench.json` | No (generated) | Last mutation benchmark output. |
| `docs/13_VERIFICATION.md` | Yes | Exact command output for all measured numbers. |
| `docs/11_CLAIMS_AND_HONESTY.md` | Yes | What may be said to judges. Read before changing wording. |
| `requirements.txt` | Yes | `streamlit`, `pandas`, `scikit-learn`, `numpy`, `joblib`. |

## 3. Features (in order)

For each 10 s window, from `ml.py::featurize()`:

1–7. Counts of each event type: `login_ok`, `login_fail`, `logout`, `file_read`, `file_write`, `sudo`, `config_change`.
8. Total event count in the window.
9. Number of distinct `src_ip`.
10. Number of distinct `user`.
11. Fraction of events that are `login_fail` (`login_fail / n`).

That is 11 features, not 10. Rows with an unparseable `ts` are skipped. `ts` format is `%Y-%m-%dT%H:%M:%S`; windows are keyed by `epoch_seconds // 10 * 10`.

## 4. Exact measured output (development laptop)

Commands and printed output:

```
python3 gen.py --dataset dataset
wrote 29055 train and 7448 test events to dataset/

.venv/bin/python ml.py train
trained on 1440 benign windows, threshold -0.5764

.venv/bin/python ml.py eval
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

.venv/bin/python bench.py
100 mutations, 100 detected, median 1.72 ms (p95 1.77 ms)
  INSERT     18/18
  TRUNCATE   21/21
  EDIT       40/40
  DELETE     21/21
```

Interpretation: on the synthetic holdout, all 12 attack windows were flagged; 4 benign windows were also flagged. Precision 0.75, recall 1.0, F1 0.857. These numbers are from one run, one laptop, synthetic data. They are not a production estimate.

## 5. What was tried and what to disclose

The first version used the 5th percentile. It produced precision 0.375, recall 1.0, F1 0.545 (20 benign windows flagged). A local scan of the threshold budget gave:

| Budget (percentile of benign train scores) | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| 0.1% | 7 | 2 | 5 | 0.778 | 0.583 | 0.667 |
| 0.5% | 10 | 2 | 2 | 0.833 | 0.833 | 0.833 |
| 1% | 12 | 4 | 0 | 0.750 | 1.000 | 0.857 |
| 2% | 12 | 10 | 0 | 0.545 | 1.000 | 0.706 |
| 3% | 12 | 12 | 0 | 0.500 | 1.000 | 0.667 |
| 5% (original) | 12 | 20 | 0 | 0.375 | 1.000 | 0.545 |

**Honesty note:** the 1% choice was made after looking at holdout scores. That is a mild form of tuning on the test set. Do not call the holdout score an unbiased estimate. If you improve this, choose the threshold on a separate validation split cut from training data, then report the test numbers once.

## 6. Known limitations

1. Synthetic data from the same generator: scores are optimistic by construction.
2. Six bursts become 12 positive windows because a 10 s burst often crosses a window boundary. Window-level labels inflate the sample count.
3. No calibration, no ECE, no PR-AUC measure. No confidence interval; 12 positive windows is a small sample.
4. Only one seed (42) and one laptop. No cross-validation.
5. No concept drift or time-of-day handling: train and test are different days, which is realistic but uncontrolled.
6. `flag_windows()` loads `model.joblib` on every call. If the model file is missing, the console chart raises while the main integrity banner still works.
7. `metrics.json` and `model.joblib` are gitignored. A fresh clone has no model until someone runs `make dataset && make train`.
8. The model is not part of the integrity claim. Do not present it as detecting a root attacker who rewrites log + ledger; vaults do that.

## 7. How Claude can check it

```
cd /home/vic/Projects/logseal
python -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
python gen.py --dataset dataset
.venv/bin/python ml.py train
.venv/bin/python ml.py eval        # prints JSON; writes metrics.json
```

Quick sanity check of flagged windows:

```
.venv/bin/python - <<'PY'
import gen, ml, random, json
evs=[dict(e) for _,e in gen.burst_events(random.Random(7), __import__('datetime').datetime.now())]
print([w for w in ml.flag_windows(evs) if w['flagged']])
PY
```

Checks that matter:

- Reproduce the numbers above on a fresh dataset with seed 42.
- Confirm `len(featurize(...))` returns 11 columns per window.
- Confirm `metrics.json` matches the printed output byte for byte in values.
- Confirm the console still renders when `model.joblib` exists and when it does not.

## 8. Improvement list, in order of value

1. **Remove test-set tuning.** Split train into fit/validation by time, pick the percentile on validation, then evaluate test once. Add a `--tune` flag or a `validate()` function in `ml.py`.
2. **Better labels.** Produce one label per burst, not per event; evaluate burst-level detection (did the run of failures get flagged at least once?) as well as window-level.
3. **Consecutive-window logic.** Merge two adjacent flagged windows into one alarm; this should cut false positives without losing recall.
4. **More features.** Failed-login rate per (user, IP), inter-arrival gaps, entropy of users/IPs, hour-of-day bucket. Keep the feature list in one place so tests can assert its length.
5. **Multiple seeds.** Run the dataset generator with 3–5 seeds and report mean and range for precision/recall/F1. Never quote only the best run.
6. **Fail-safe console.** `app.py` should show "model not trained" instead of raising when `model.joblib` is missing. Requires P3 agreement on `app.py`.
7. **Persist metadata.** Save the dataset seed, feature names, sklearn version and git hash alongside the model so a number can always be traced to a run.
8. **Tests.** Add `tests/test_ml.py` with a tiny synthetic dataset: feature count, deterministic threshold, flagged burst. Keep sklearn import inside the functions so core tests stay stdlib-only.

## 9. Boundaries

- Safe to edit: `ml.py`, `gen.py`, `bench.py`, new `tests/test_ml.py`, new docs.
- Do not edit: `seal.py`, `verify.py`, `witness.py`, `app.py` (P3 owns it), `docs/03_CONTRACT.md`, `config*.json` (all four must agree).
- Never commit `dataset/`, `model.joblib`, `metrics.json`, `bench.json`, `.run/` — `.gitignore` covers them.
- Quote only script output to judges. See `docs/11_CLAIMS_AND_HONESTY.md`.
