"""Mutation benchmark on a COPY of the files. Writes bench.json. Vault cases are tested by hand in rehearsal.
  python bench.py"""
import json, os, random, shutil, statistics, tempfile, time
import gen, seal, verify

def main(n_events=200, n_mut=100, seed=1):
    rng, tmp = random.Random(seed), tempfile.mkdtemp(prefix="bench_")
    cfg = {"log_path": f"{tmp}/log", "ledger_path": f"{tmp}/ledger", "hmac_key_env": "LOGSEAL_KEY", "hmac_key_default": "bench-key",
           "witnesses": [], "witness_timeout_s": 1.0, "pending_grace_s": 3}
    for _ in range(n_events):
        seal.append(gen.make_event(rng), cfg)
    pristine = open(cfg["log_path"], "rb").read().split(b"\n")[:-1]
    by, times = {}, []
    for _ in range(n_mut):
        L, kind, i = list(pristine), rng.choice(["EDIT", "WHITESPACE", "DELETE", "INSERT", "TRUNCATE"]), rng.randrange(len(pristine) - 1)
        if kind == "EDIT":
            j = rng.randrange(len(L[i])); L[i] = L[i][:j] + bytes([65 + (L[i][j] + 1) % 26]) + L[i][j + 1:]
        elif kind == "WHITESPACE":
            j = rng.randrange(len(L[i])); L[i] = L[i][:j] + b" " + L[i][j:]
        elif kind == "DELETE":
            del L[i]
        elif kind == "INSERT":
            L.insert(i, b'{"event":"login_ok","user":"mallory"}')
        else:
            L = L[:-rng.randint(1, 5)]
        open(cfg["log_path"], "wb").write(b"\n".join(L) + b"\n")
        t0 = time.perf_counter(); r = verify.verify(cfg, use_witnesses=False); times.append((time.perf_counter() - t0) * 1000)
        want = "EDIT" if kind == "WHITESPACE" else kind
        b = by.setdefault(want, {"n": 0, "detected": 0}); b["n"] += 1
        b["detected"] += r["status"] == "TAMPERED" and any(f["class"] == want for f in r["findings"])
    times.sort()
    out = {"mutations": n_mut, "detected": sum(b["detected"] for b in by.values()), "by_class": by,
           "latency_ms_median": round(statistics.median(times), 2), "latency_ms_p95": round(times[int(0.95 * len(times)) - 1], 2),
           "note": "local checks on a copy of the files, vaults not included; detected = alarm with the correct class"}
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bench.json"), "w"), indent=2)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"{out['mutations']} mutations, {out['detected']} detected, median {out['latency_ms_median']} ms (p95 {out['latency_ms_p95']} ms)")
    for k, v in by.items():
        print(f"  {k:10} {v['detected']}/{v['n']}")

if __name__ == "__main__":
    main()
