"""The smart attacker. Has the HMAC key on purpose: the vaults are what stop it, not the key.
  python attack.py rewrite --seq 120 --find alice --replace mallory
  python attack.py wipe --keep 100
  python attack.py restore          (stop gen.py before attacking and before restoring)"""
import argparse, shutil
import seal, witness

def backup(cfg):
    for p in (cfg["log_path"], cfg["ledger_path"]):
        shutil.copyfile(p, p + ".bak")

def rewrite(cfg, seq, find, replace):
    lines = open(cfg["log_path"], "rb").read().split(b"\n")[:-1]
    if not 1 <= seq <= len(lines) or find.encode() not in lines[seq - 1]:
        raise SystemExit(f"record {seq} not found or does not contain '{find}'")
    backup(cfg)
    lines[seq - 1] = lines[seq - 1].replace(find.encode(), replace.encode(), 1)
    open(cfg["log_path"], "wb").write(b"\n".join(lines) + b"\n")
    seal.rebuild_ledger(cfg)                                    # re-chain from seq to the end, with the real key
    print(f"Edited record {seq} and re-sealed records {seq}..{len(lines)} with the real key. The server now looks consistent.")
    e = seal._ledger_entries(cfg)[seq - 1]
    for r in witness.push(e, cfg):
        who = r["name"]
        print(f"  {who} REJECTED the rewrite (conflict at record {seq})" if r["status"] == 409
              else f"  {who}: no answer ({r['error'] or r['status']}), could not push")

def wipe(cfg, keep):
    backup(cfg)
    lines = open(cfg["log_path"], "rb").read().split(b"\n")[:-1]
    open(cfg["log_path"], "wb").write(b"\n".join(lines[:keep]) + (b"\n" if keep else b""))
    seal.rebuild_ledger(cfg)
    print(f"Cut log and ledger back to the first {keep} of {len(lines)} records. The server alone cannot tell.")

def restore(cfg):
    for p in (cfg["log_path"], cfg["ledger_path"]):
        shutil.copyfile(p + ".bak", p)
    print("restored files from .bak")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["rewrite", "wipe", "restore"]); ap.add_argument("--config", default="config.json")
    ap.add_argument("--seq", type=int, default=120); ap.add_argument("--find", default="alice")
    ap.add_argument("--replace", default="mallory"); ap.add_argument("--keep", type=int, default=100)
    a = ap.parse_args(); c = seal.load_config(a.config)
    {"rewrite": lambda: rewrite(c, a.seq, a.find, a.replace), "wipe": lambda: wipe(c, a.keep), "restore": lambda: restore(c)}[a.cmd]()
