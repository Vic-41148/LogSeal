#!/usr/bin/env python3
"""Fast pre-commit gate: does the repo still obey docs/03_CONTRACT.md?

Run: python scripts/check_contract.py
Exit code 0 = pass, 1 = contract broken.
"""
import ast
import inspect
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

FILES = ["seal.py", "verify.py", "witness.py", "gen.py", "attack.py", "bench.py", "app.py", "ml.py",
         "config.json", "config.local.json", "requirements.txt"]
CORE = ["seal.py", "verify.py", "witness.py", "gen.py", "attack.py", "bench.py"]
LOCAL = {"seal", "verify", "witness", "gen", "attack", "bench", "ml", "app"}
CONFIG_KEYS = {"log_path", "ledger_path", "hmac_key_env", "hmac_key_default",
               "witnesses", "witness_timeout_s", "pending_grace_s"}
EVENTS = {"login_ok", "login_fail", "logout", "file_read", "file_write", "sudo", "config_change"}

failures = []


def check(name, condition, detail=""):
    print(("PASS  " if condition else "FAIL  ") + name + (f"   {detail}" if detail else ""))
    if not condition:
        failures.append(name)


def imports_of(filename):
    tree = ast.parse(open(os.path.join(ROOT, filename), encoding="utf-8").read(), filename=filename)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def main():
    for filename in FILES:
        check(f"{filename} exists", os.path.exists(os.path.join(ROOT, filename)))

    for filename in ("config.json", "config.local.json"):
        try:
            cfg = json.load(open(os.path.join(ROOT, filename), encoding="utf-8"))
            check(f"{filename} has the contract keys", set(cfg) == CONFIG_KEYS, str(sorted(set(cfg) ^ CONFIG_KEYS)))
            check(f"{filename} lists at least one vault",
                  isinstance(cfg.get("witnesses"), list) and len(cfg["witnesses"]) >= 1)
        except Exception as exc:
            check(f"{filename} parses", False, repr(exc))

    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    for filename in CORE:
        extra = imports_of(filename) - LOCAL - stdlib
        check(f"{filename} is stdlib only", not extra, str(sorted(extra)))

    import seal, verify, witness
    signatures = {
        (seal, "append"): ["evt", "cfg"],
        (seal, "load_config"): ["path"],
        (seal, "resync"): ["cfg"],
        (seal, "reset"): ["cfg"],
        (verify, "verify"): ["cfg", "log_path", "ledger_path", "use_witnesses"],
        (witness, "push"): ["entry", "cfg"],
        (witness, "head"): ["url", "timeout"],
        (witness, "entry"): ["url", "seq", "timeout"],
    }
    for (module, function), expected in signatures.items():
        exists = hasattr(module, function)
        check(f"{module.__name__}.{function} exists", exists)
        if exists:
            got = list(inspect.signature(getattr(module, function)).parameters)
            check(f"{module.__name__}.{function} arguments", got == expected, str(got))

    import gen
    check("event types match the contract", {e for e, _ in gen.MIX} == EVENTS,
          str(sorted({e for e, _ in gen.MIX} ^ EVENTS)))

    print()
    print("CONTRACT OK" if not failures else f"{len(failures)} CONTRACT FAILURE(S)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
