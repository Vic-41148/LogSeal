"""Synthetic security-event generator. Always launch from a terminal (never from the UI).
  python gen.py --rate 2                 live benign events, sealed
  python gen.py --attack burst           ~40 failed logins from one external IP, then a success (sealed)
  python gen.py --dataset DIR            labeled train.jsonl / test.jsonl for ml.py (NOT sealed)"""
import argparse, json, os, random, time
from datetime import datetime, timedelta

USERS = ["alice", "bob", "carol", "dave", "erin", "frank", "grace"]
IPS = [f"10.0.0.{i}" for i in range(5, 15)]
MIX = [("file_read", 40), ("login_ok", 15), ("file_write", 15), ("logout", 12), ("sudo", 4), ("login_fail", 3), ("config_change", 1)]
MSG = {"login_ok": "login ok", "login_fail": "bad password", "logout": "session closed", "file_read": "read /var/data/report.csv",
       "file_write": "wrote /var/data/report.csv", "sudo": "sudo systemctl restart app", "config_change": "edited /etc/app.conf"}
FMT = "%Y-%m-%dT%H:%M:%S"
ATTACKER_IP = "203.0.113.50"

def make_event(rng, ts=None, event=None, user=None, ip=None):
    ev = event or rng.choices([e for e, _ in MIX], [w for _, w in MIX])[0]
    return {"ts": (ts or datetime.now()).strftime(FMT), "host": "srv-01", "user": user or rng.choice(USERS),
            "event": ev, "src_ip": ip or rng.choice(IPS), "msg": MSG[ev]}

def burst_events(rng, ts, n=40, span=10.0):
    user = rng.choice(USERS)
    out = [(ts + timedelta(seconds=span * i / n), make_event(rng, ts + timedelta(seconds=span * i / n), "login_fail", user, ATTACKER_IP)) for i in range(n)]
    last = ts + timedelta(seconds=span)
    out.append((last, make_event(rng, last, "login_ok", user, ATTACKER_IP)))
    return out

def write_dataset(folder, seed):
    rng, start = random.Random(seed), datetime(2026, 11, 20, 8, 0, 0)
    os.makedirs(folder, exist_ok=True)

    def benign(t0, secs, rate=2.0):
        t, out = 0.0, []
        while True:
            t += rng.expovariate(rate)
            if t >= secs:
                return out
            ts = t0 + timedelta(seconds=t)
            out.append((ts, dict(make_event(rng, ts), label=0)))

    train = benign(start, 4 * 3600)
    test = benign(start + timedelta(days=1), 3600)
    for k in range(6):                                           # six injected bursts, spaced out
        t0 = start + timedelta(days=1, seconds=300 + k * 560 + rng.randint(0, 120))
        test += [(ts, dict(e, label=1)) for ts, e in burst_events(rng, t0)]
    for name, rows in (("train.jsonl", train), ("test.jsonl", sorted(test, key=lambda r: r[0]))):
        with open(os.path.join(folder, name), "w") as f:
            for _, e in rows:
                f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"wrote {len(train)} train and {len(test)} test events to {folder}/")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rate", type=float, default=2.0); ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--attack", choices=["burst"]); ap.add_argument("--dataset")
    ap.add_argument("--config", default="config.json")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    if a.dataset:
        write_dataset(a.dataset, a.seed if a.seed is not None else 42)
        raise SystemExit
    import seal
    cfg = seal.load_config(a.config)
    if a.attack == "burst":
        for ts, e in burst_events(rng, datetime.now()):
            seal.append(e, cfg); time.sleep(0.25)
        print("burst sealed")
        raise SystemExit
    print(f"generating ~{a.rate} events/s, Ctrl+C to stop")
    try:
        while True:
            seal.append(make_event(rng), cfg); time.sleep(1.0 / a.rate)
    except KeyboardInterrupt:
        print("stopped")
