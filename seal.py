"""LogSeal core: seal events into a hash chain (log + ledger) and push fingerprints to vaults.
CLI: python seal.py --selftest | --reset [--config PATH]"""
import argparse, hashlib, hmac, json, os, sys, time
try:
    import witness
except ImportError:
    witness = None

ZERO = "0" * 64
HERE = os.path.dirname(os.path.abspath(__file__))

def load_config(path="config.json"):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    base = os.path.dirname(os.path.abspath(path))
    for k in ("log_path", "ledger_path"):          # relative paths live next to the config file
        if not os.path.isabs(cfg[k]):
            cfg[k] = os.path.join(base, cfg[k])
    return cfg

def get_key(cfg):
    return os.environ.get(cfg["hmac_key_env"], cfg["hmac_key_default"]).encode()

def sha(x):
    return hashlib.sha256(x if isinstance(x, bytes) else x.encode()).hexdigest()

def make_mac(key, seq, prev, h, lhash):
    return hmac.new(key, f"{seq}:{prev}:{h}:{lhash}".encode(), hashlib.sha256).hexdigest()

def _dump(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))

def _write(path, text):
    with open(path, "ab") as f:                     # append, flush, fsync: durable before we move on
        f.write(text.encode("utf-8")); f.flush(); os.fsync(f.fileno())

def _last_entry(path):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2); size = f.tell(); f.seek(max(0, size - 4096)); chunk = f.read()
    except FileNotFoundError:
        return None
    for ln in reversed(chunk.split(b"\n")):
        try:
            e = json.loads(ln)
            if isinstance(e, dict) and "seq" in e:
                return e
        except Exception:
            continue
    return None

def _build(evt, cfg):
    last = _last_entry(cfg["ledger_path"])
    seq, prev = (last["seq"] + 1, last["hash"]) if last else (1, ZERO)
    evt = dict(evt, seq=seq)
    evt.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S"))
    line = _dump(evt)
    lhash, h = sha(line), sha(prev + line)
    return line, {"seq": seq, "prev": prev, "hash": h, "lhash": lhash,
                  "mac": make_mac(get_key(cfg), seq, prev, h, lhash)}

def append(evt, cfg):
    """Seal one event. Order: log line, ledger entry, then vaults (best effort)."""
    line, entry = _build(evt, cfg)
    _write(cfg["log_path"], line + "\n")
    _write(cfg["ledger_path"], _dump(entry) + "\n")
    if witness and cfg.get("witnesses"):
        res = witness.push(entry, cfg)
        if any(r.get("error") == "GAP" for r in res):
            resync(cfg)
    return entry

def _ledger_entries(cfg):
    out = []
    try:
        with open(cfg["ledger_path"], "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        return out
    for ln in raw.split(b"\n"):
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out

def resync(cfg):
    """Replay ledger entries a vault is missing (vault was offline or restarted empty)."""
    if not witness:
        return
    entries = _ledger_entries(cfg)
    for w in cfg.get("witnesses", []):
        h = witness.head(w["url"], cfg.get("witness_timeout_s", 1.0))
        if h is None:
            continue
        for e in entries[int(h.get("count", 0)):]:
            if not witness.push(e, {**cfg, "witnesses": [w]})[0]["ok"]:
                break

def reset(cfg):
    for p in (cfg["log_path"], cfg["ledger_path"]):
        open(p, "wb").close()
    try:
        os.remove(os.path.join(os.path.dirname(os.path.abspath(cfg["log_path"])), ".verify_state.json"))
    except OSError:
        pass
    if witness:
        witness.reset(cfg)

def rebuild_ledger(cfg, key=None):
    """Recompute the whole ledger from the current log lines with the real key.
    Used by attack.py (root attacker) and the selftest. Not part of normal operation."""
    key = key or get_key(cfg)
    with open(cfg["log_path"], "rb") as f:
        lines = f.read().split(b"\n")[:-1]
    prev, out = ZERO, []
    for i, raw in enumerate(lines, 1):
        line = raw.decode("utf-8", "replace")
        lhash, h = sha(raw), sha(prev + line)
        out.append(_dump({"seq": i, "prev": prev, "hash": h, "lhash": lhash, "mac": make_mac(key, i, prev, h, lhash)}))
        prev = h
    with open(cfg["ledger_path"], "wb") as f:
        f.write(("\n".join(out) + ("\n" if out else "")).encode())

def _free_port():
    """Ask the OS for a free localhost port. Tests must not use a fixed port:
    four people may run the suite at the same time on one machine."""
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def _start_test_vault(tmp):
    """Start witness.py on a free port. Retry when another process takes the port first."""
    import subprocess
    for _ in range(5):
        port = _free_port()
        proc = subprocess.Popen([sys.executable, os.path.join(HERE, "witness.py"), "--name", "T1", "--port", str(port),
                                 "--allow-reset", "--dir", tmp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        vurl = f"http://127.0.0.1:{port}"
        for _ in range(60):
            if witness.head(vurl, 0.2) is not None:
                return proc, vurl
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        proc.terminate(); proc.wait()
    raise RuntimeError("could not start the test vault")

# ------------------------------------------------------------------ selftest (mutation tests)
def selftest():
    import atexit, random, shutil, tempfile, threading
    import gen, verify as V
    tmp, fails = tempfile.mkdtemp(prefix="logseal_"), []
    proc, vurl = _start_test_vault(tmp)
    atexit.register(lambda: proc.poll() is None and proc.terminate())

    def check(name, cond, extra=""):
        print(("PASS  " if cond else "FAIL  ") + name + (f"   {extra}" if extra else ""))
        if not cond:
            fails.append(name)

    def fresh(tag, n=50, vault=False):
        d = os.path.join(tmp, tag); os.makedirs(d)
        cfg = {"log_path": f"{d}/app.log.jsonl", "ledger_path": f"{d}/ledger.jsonl", "hmac_key_env": "LOGSEAL_KEY",
               "hmac_key_default": "selftest-key", "witnesses": [{"name": "Vault 1", "url": vurl}] if vault else [],
               "witness_timeout_s": 1.0, "pending_grace_s": 3}
        cfg["log_path"], cfg["ledger_path"] = [os.path.abspath(cfg[k]) for k in ("log_path", "ledger_path")]
        if vault:
            witness.reset(cfg)
        rng = random.Random(1)
        for _ in range(n):
            append(gen.make_event(rng), cfg)
        return cfg

    def rd(p):  return open(p, "rb").read().split(b"\n")[:-1]
    def wr(p, ls): open(p, "wb").write(b"\n".join(ls) + b"\n")
    def classes(cfg, **kw):
        r = V.verify(cfg, use_witnesses=kw.get("w", False)); return r, {f["class"] for f in r["findings"]}

    def mutate(name, fn, want, seq=None):
        cfg = fresh(name.replace(" ", "_")); fn(cfg)
        r, cl = classes(cfg)
        ok = want in cl and r["status"] == "TAMPERED" and (seq is None or any(f["seq"] == seq for f in r["findings"] if f["class"] == want))
        check(name, ok, f"-> {sorted(cl)} @ {[f['seq'] for f in r['findings']]}")

    check("clean log has no findings", classes(fresh("clean"))[0]["status"] == "OK")
    def edit(c):   l = rd(c["log_path"]); l[23] = l[23].replace(b"srv-01", b"srv-02", 1); wr(c["log_path"], l)
    def space(c):  l = rd(c["log_path"]); l[10] += b" "; wr(c["log_path"], l)
    def dele(c):   l = rd(c["log_path"]); del l[19]; wr(c["log_path"], l)
    def ins(c):    l = rd(c["log_path"]); l.insert(30, b'{"event":"login_ok","user":"mallory"}'); wr(c["log_path"], l)
    def trunc(c):  wr(c["log_path"], rd(c["log_path"])[:-5])
    def swap(c):   l = rd(c["log_path"]); l[9], l[10] = l[10], l[9]; wr(c["log_path"], l)
    def forge(c):  l = rd(c["ledger_path"]); l[14] = l[14].replace(b'"hash":"', b'"hash":"0', 1); wr(c["ledger_path"], l)
    mutate("edit one character", edit, "EDIT", 24)
    mutate("add one space (whitespace must alarm)", space, "EDIT", 11)
    mutate("delete a middle line", dele, "DELETE", 20)
    mutate("insert a line in the middle", ins, "INSERT", 31)
    mutate("drop last 5 lines", trunc, "TRUNCATE", 46)
    mutate("swap two adjacent lines", swap, "EDIT")
    mutate("forge a ledger entry", forge, "LEDGER_FORGED", 15)

    cfg = fresh("vault", vault=True)
    r = V.verify(cfg)
    check("vault run is clean and vault agrees", r["status"] == "OK" and r["nodes"][1]["agrees"] is True)
    shutil.copy(cfg["log_path"], cfg["log_path"] + ".bak"); shutil.copy(cfg["ledger_path"], cfg["ledger_path"] + ".bak")
    l = rd(cfg["log_path"]); l[19] = l[19].replace(b"srv-01", b"evil", 1); wr(cfg["log_path"], l); rebuild_ledger(cfg)
    r0 = V.verify(cfg, use_witnesses=False); r = V.verify(cfg)
    check("root rewrite: server alone says OK", r0["status"] == "OK")
    check("root rewrite: vault reports WITNESS_CONFLICT at 20, server tile green, vault tile red",
          any(f["class"] == "WITNESS_CONFLICT" and f["seq"] == 20 for f in r["findings"])
          and r["nodes"][0]["agrees"] is True and r["nodes"][1]["agrees"] is False, str([f["seq"] for f in r["findings"]]))
    check("vault rejects pushing rewritten history", witness.push(_ledger_entries(cfg)[19], cfg)[0]["status"] == 409)
    shutil.copy(cfg["log_path"] + ".bak", cfg["log_path"]); shutil.copy(cfg["ledger_path"] + ".bak", cfg["ledger_path"])
    check("restore returns to green", V.verify(cfg)["status"] == "OK")
    wr(cfg["log_path"], rd(cfg["log_path"])[:30]); rebuild_ledger(cfg)
    r0 = V.verify(cfg, use_witnesses=False); r = V.verify(cfg)
    check("consistent wipe: server says OK, vault reports WITNESS_AHEAD",
          r0["status"] == "OK" and any(f["class"] == "WITNESS_AHEAD" for f in r["findings"]))

    cfg = fresh("pending", n=10); cfg["pending_grace_s"] = 0.4
    line, entry = _build({"host": "srv-01", "user": "bob", "event": "login_ok", "src_ip": "10.0.0.5", "msg": "x"}, cfg)
    _write(cfg["log_path"], line + "\n")
    check("unsealed line -> PENDING (no alarm)", V.verify(cfg, use_witnesses=False)["status"] == "PENDING")
    _write(cfg["ledger_path"], _dump(entry) + "\n")
    check("ledger catches up -> OK", V.verify(cfg, use_witnesses=False)["status"] == "OK")
    _write(cfg["log_path"], line.replace("bob", "eve") + "\n"); V.verify(cfg, use_witnesses=False); time.sleep(0.6)
    check("line never sealed -> UNSEALED after grace", "UNSEALED" in classes(cfg)[1])

    cfg = fresh("live", n=5); bad, calls = [], 0
    def writer():
        rng = random.Random(7)
        for _ in range(300):
            append(gen.make_event(rng), cfg)
    t = threading.Thread(target=writer); t.start()
    while t.is_alive() or calls < 200:
        r = V.verify(cfg, use_witnesses=False); calls += 1
        if r["status"] == "TAMPERED":
            bad.append(r["findings"])
    t.join()
    check(f"{calls} verify calls during live appends: zero false alarms", not bad, str(bad[:1]))
    final = V.verify(cfg, use_witnesses=False)
    check("ends clean after writer stops", final["status"] in ("OK", "PENDING") and not final["findings"])

    cfg = fresh("big", n=1000); t0 = time.time(); V.verify(cfg, use_witnesses=False); dt = time.time() - t0
    check("verify() on 1,000 events under 1 second", dt < 1.0, f"{dt*1000:.0f} ms")

    proc.terminate(); shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json"); ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if a.reset:
        reset(load_config(a.config)); print("reset done")
