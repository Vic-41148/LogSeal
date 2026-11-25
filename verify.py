"""LogSeal verifier: re-hash the raw log, compare with the ledger and the vaults.
CLI: python verify.py [--config PATH] [--watch]"""
import argparse, hmac, json, os, time
from datetime import datetime
import seal
try:
    import witness
except ImportError:
    witness = None

ZERO = "0" * 64
LOCAL = {"EDIT", "DELETE", "INSERT", "TRUNCATE", "UNSEALED", "LEDGER_FORGED"}

def _read_lines(path, keep_partial):
    """Raw byte lines. A last line without newline is an in-progress write."""
    try:
        with open(path, "rb") as f:                 # reopen every call, hold no handles
            parts = f.read().split(b"\n")
    except FileNotFoundError:
        return []
    if parts and parts[-1] == b"":
        parts.pop()
    elif parts and not keep_partial:
        parts.pop()
    return parts

def _check_ledger(raw, key):
    entries, bad, prev = [], None, ZERO
    for i, ln in enumerate(raw, 1):
        e, ok = {}, False
        try:
            e = json.loads(ln)
            ok = (e["seq"] == i and e["prev"] == prev and all(isinstance(e[k], str) for k in ("hash", "lhash", "mac"))
                  and hmac.compare_digest(e["mac"], seal.make_mac(key, i, e["prev"], e["hash"], e["lhash"])))
        except Exception:
            if not isinstance(e, dict):
                e = {}
        entries.append(e if isinstance(e, dict) else {})
        if not ok and bad is None:
            bad = i
        if isinstance(entries[-1].get("hash"), str):
            prev = entries[-1]["hash"]
    return entries, bad

def _finding(cls, seq, expected, actual, detail):
    return {"class": cls, "seq": seq, "expected": expected, "actual": actual, "detail": detail, "confirmed_by": []}

def _state_path(log_path):
    return os.path.join(os.path.dirname(os.path.abspath(log_path)), ".verify_state.json")

def verify(cfg=None, log_path=None, ledger_path=None, use_witnesses=True):
    cfg = cfg or seal.load_config()
    log_path, ledger_path = log_path or cfg["log_path"], ledger_path or cfg["ledger_path"]
    now = time.time()
    # READ LEDGER FIRST: the writer appends log before ledger, so log >= ledger always holds.
    raw_led = _read_lines(ledger_path, False)
    raw_log = _read_lines(log_path, True)
    entries, bad = _check_ledger(raw_led, seal.get_key(cfg))
    L = [seal.sha(x) for x in raw_log]
    G, H = [e.get("lhash") for e in entries], [e.get("hash") for e in entries]
    findings, pending = [], False

    if bad:
        findings.append(_finding("LEDGER_FORGED", bad, None, None,
                                 f"Sealed record {bad} in the ledger does not match its signature: the ledger itself was edited."))
    n = min(len(L), len(G))
    f = next((i for i in range(n) if L[i] != G[i]), None)
    if f is None:
        if len(L) < len(G):
            s = len(L) + 1
            findings.append(_finding("TRUNCATE", s, G[s - 1], None,
                                     f"{len(G) - len(L)} record(s) were cut off the end of the log (records {s} to {len(G)})."))
    elif L[f + 1:] == G[f:]:
        findings.append(_finding("INSERT", f + 1, G[f], L[f], f"A record was inserted into the log at position {f + 1}; it was never sealed."))
    elif L[f:] == G[f + 1:]:
        findings.append(_finding("DELETE", f + 1, G[f], None, f"Record {f + 1} was removed from the log."))
    elif L[f + 1:] == G[f + 1:]:
        findings.append(_finding("EDIT", f + 1, G[f], L[f], f"Record {f + 1} was changed after it was sealed."))
    else:
        findings.append(_finding("EDIT", f + 1, G[f], L[f],
                                 f"Record {f + 1} was changed after it was sealed (multiple records differ, or records were reordered)."))

    sp = _state_path(log_path)
    if f is None and len(L) > len(G):                       # trailing lines not yet sealed
        try:
            with open(sp) as f:
                st = json.load(f)
        except Exception:
            st = {}
        if st.get("count") != len(G):
            st = {"count": len(G), "since": now}
            try:
                with open(sp, "w") as f:
                    json.dump(st, f)
            except OSError:
                pass
        if now - st["since"] > cfg.get("pending_grace_s", 3):
            findings.append(_finding("UNSEALED", len(G) + 1, None, L[len(G)],
                                     f"{len(L) - len(G)} record(s) at the end of the log were never sealed."))
        else:
            pending = True
    elif os.path.exists(sp):
        try:
            os.remove(sp)
        except OSError:
            pass

    # ---- vaults
    t = cfg.get("witness_timeout_s", 1.0)
    vaults = cfg.get("witnesses", []) if (use_witnesses and witness) else []
    heads = witness._parallel(lambda w: witness.head(w["url"], t), vaults) if vaults else []
    local_bad = any(x["class"] in LOCAL for x in findings)
    nodes = [{"name": "Server", "role": "server", "reachable": True, "head_seq": len(G),
              "head_hash": H[-1] if H else ZERO, "agrees": not local_bad}]
    for w, h in zip(vaults, heads):
        node = {"name": w["name"], "role": "vault", "reachable": h is not None, "head_seq": None, "head_hash": None, "agrees": None}
        nodes.append(node)
        if h is None:
            continue
        cnt = int(h.get("count", 0))
        node.update(head_seq=cnt, head_hash=h.get("hash"), agrees=True)
        fnd = None
        if cnt > len(G):
            e = witness.entry(w["url"], len(G) + 1, t)
            fnd = _finding("WITNESS_AHEAD", len(G) + 1, (e or h).get("hash"), None,
                           f"The vaults remember {cnt} records but the server only has {len(G)}: records {len(G) + 1} to {cnt} were removed.")
        elif cnt > 0 and H[cnt - 1] != h.get("hash"):
            lo, hi = 1, cnt                                  # first seq where vault and server ledger disagree
            while lo < hi:
                mid = (lo + hi) // 2
                e = witness.entry(w["url"], mid, t)
                if e is None:
                    break
                lo, hi = (mid + 1, hi) if e.get("hash") == H[mid - 1] else (lo, mid)
            e = witness.entry(w["url"], hi, t)
            fnd = _finding("WITNESS_CONFLICT", hi, (e or h).get("hash"), H[hi - 1],
                           f"The server's records were rewritten: the vaults remember record {hi} differently.")
        if fnd:
            node["agrees"] = False
            same = next((x for x in findings if x["class"] == fnd["class"] and x["seq"] == fnd["seq"]), None)
            if same:
                same["confirmed_by"].append(w["name"])
            else:
                fnd["confirmed_by"] = [w["name"]]; findings.append(fnd)
        else:
            node["_ok"] = w                                   # temp marker for confirmed_by below
    for x in findings:                                        # which vaults still hold the ORIGINAL fingerprint
        if x["class"] in LOCAL and 1 <= x["seq"] <= len(G) and H[x["seq"] - 1]:
            for node in nodes:
                w = node.get("_ok")
                if w and (node["head_seq"] or 0) >= x["seq"]:
                    e = witness.entry(w["url"], x["seq"], t)
                    if e and e.get("hash") == H[x["seq"] - 1]:
                        x["confirmed_by"].append(node["name"])
    for node in nodes:
        node.pop("_ok", None)

    bad_seqs = {x["seq"] for x in findings}
    feed, base = [], max(0, len(raw_log) - 50)
    for i, ln in enumerate(raw_log[base:], base + 1):
        try:
            e = json.loads(ln.decode("utf-8"))
            feed.append({"seq": i, "ts": e.get("ts"), "event": e["event"], "user": e.get("user"),
                         "src_ip": e.get("src_ip"), "ok": i not in bad_seqs})
        except Exception:
            feed.append({"seq": i, "event": "UNPARSEABLE", "ok": False})
    return {"status": "TAMPERED" if findings else ("PENDING" if pending else "OK"),
            "checked_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "log_lines": len(raw_log), "ledger_entries": len(raw_led),
            "findings": findings, "nodes": nodes, "feed": feed}

def watch(cfg):
    col = {"OK": "\033[92m", "PENDING": "\033[93m", "TAMPERED": "\033[91m\033[1m"}
    while True:
        try:
            r = verify(cfg)
            extra = "  " + "; ".join(f"{x['class']} @ record {x['seq']}" for x in r["findings"]) if r["findings"] else ""
            tiles = " ".join(f"[{n['name']}: {'OFFLINE' if n['agrees'] is None else ('ok' if n['agrees'] else 'MISMATCH')}]" for n in r["nodes"])
            print(f"{col[r['status']]}{r['status']:9}\033[0m {r['log_lines']} records {tiles}{extra}", flush=True)
        except Exception as e:
            print(f"verifier error: {e}", flush=True)
        time.sleep(1)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json"); ap.add_argument("--watch", action="store_true")
    a = ap.parse_args(); c = seal.load_config(a.config)
    if a.watch:
        try:
            watch(c)
        except KeyboardInterrupt:
            pass
    else:
        r = verify(c); r.pop("feed"); print(json.dumps(r, indent=2))
