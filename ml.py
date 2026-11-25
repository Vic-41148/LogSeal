"""Tiny burst detector (secondary feature). Needs: pip install scikit-learn numpy joblib
  python gen.py --dataset dataset && python ml.py train && python ml.py eval
Trained and evaluated on synthetic data from our own generator and features, so scores are optimistic by construction."""
import calendar, json, os, sys, time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WIN = 10
TYPES = ["login_ok", "login_fail", "logout", "file_read", "file_write", "sudo", "config_change"]

def _t(ts):
    return calendar.timegm(time.strptime(ts, "%Y-%m-%dT%H:%M:%S"))

def featurize(events):
    import numpy as np
    wins = {}
    for e in events:
        try:
            wins.setdefault(_t(e["ts"]) // WIN * WIN, []).append(e)
        except Exception:
            continue                                            # skip rows without a usable timestamp
    starts = sorted(wins)
    X = []
    for s in starts:
        ev = wins[s]; n = len(ev)
        X.append([sum(e.get("event") == t for e in ev) for t in TYPES]
                 + [n, len({e.get("src_ip") for e in ev}), len({e.get("user") for e in ev}),
                    sum(e.get("event") == "login_fail" for e in ev) / n])
    return starts, np.array(X, dtype=float), wins

def _load(path):
    return [json.loads(l) for l in open(path) if l.strip()]

def train(dataset="dataset"):
    import joblib, numpy as np
    from sklearn.ensemble import IsolationForest
    _, X, _ = featurize(_load(os.path.join(dataset, "train.jsonl")))
    model = IsolationForest(random_state=42).fit(X)
    thr = float(np.percentile(model.score_samples(X), 5))       # lower score = more abnormal
    joblib.dump({"model": model, "threshold": thr}, os.path.join(HERE, "model.joblib"))
    print(f"trained on {len(X)} benign windows, threshold {thr:.4f}")

def evaluate(dataset="dataset"):
    import joblib
    m = joblib.load(os.path.join(HERE, "model.joblib"))
    starts, X, wins = featurize(_load(os.path.join(dataset, "test.jsonl")))
    flag = m["model"].score_samples(X) < m["threshold"]
    y = [any(e.get("label") for e in wins[s]) for s in starts]
    tp = sum(f and t for f, t in zip(flag, y)); fp = sum(f and not t for f, t in zip(flag, y)); fn = sum((not f) and t for f, t in zip(flag, y))
    p = tp / (tp + fp) if tp + fp else 0.0; r = tp / (tp + fn) if tp + fn else 0.0
    out = {"data": "synthetic, own generator", "train_windows": len(featurize(_load(os.path.join(dataset, "train.jsonl")))[0]),
           "test_windows": len(starts), "precision": round(p, 3), "recall": round(r, 3),
           "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0, "threshold": round(m["threshold"], 4),
           "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
    return out

def flag_windows(events):
    """-> [{"window_start","score","flagged"}] for the console chart."""
    import joblib
    m = joblib.load(os.path.join(HERE, "model.joblib"))
    starts, X, _ = featurize(events)
    if not len(starts):
        return []
    sc = m["model"].score_samples(X)
    return [{"window_start": datetime.fromtimestamp(s, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
             "score": float(v), "flagged": bool(v < m["threshold"])} for s, v in zip(starts, sc)]

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "eval"
    ds = sys.argv[2] if len(sys.argv) > 2 else "dataset"
    if cmd == "train":
        train(ds)
    else:
        res = evaluate(ds)
        json.dump(res, open(os.path.join(HERE, "metrics.json"), "w"), indent=2)
        print(json.dumps(res, indent=2))
