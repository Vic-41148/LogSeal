"""The contract in docs/03_CONTRACT.md, checked by code.

Run: python -m unittest tests.test_contract -v
"""
import ast
import inspect
import json
import os
import sys
import tempfile
import unittest

from .support import EVENT_TYPES, ROOT, ZERO, gen, make_cfg, read_json, seal, verify
import witness

CORE_MODULES = ["seal.py", "verify.py", "witness.py", "gen.py", "attack.py", "bench.py"]
ALL_MODULES = CORE_MODULES + ["app.py", "ml.py"]
THIRD_PARTY_OK = {"app.py", "ml.py"}      # contract: only the console and ML may use pip packages
LOCAL_MODULES = {"seal", "verify", "witness", "gen", "attack", "bench", "ml", "app"}


def imported_names(path):
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


class ConfigContract(unittest.TestCase):
    KEYS = {"log_path", "ledger_path", "hmac_key_env", "hmac_key_default",
            "witnesses", "witness_timeout_s", "pending_grace_s"}

    def test_both_configs_have_every_key(self):
        for name in ("config.json", "config.local.json"):
            cfg = read_json(os.path.join(ROOT, name))
            self.assertEqual(self.KEYS, set(cfg), name)
            self.assertIsInstance(cfg["witnesses"], list)
            self.assertGreaterEqual(len(cfg["witnesses"]), 1, name)
            for w in cfg["witnesses"]:
                self.assertEqual({"name", "url"}, set(w), name)
                self.assertTrue(w["url"].startswith("http://"), name)

    def test_fallback_config_is_localhost_only(self):
        cfg = read_json(os.path.join(ROOT, "config.local.json"))
        for w in cfg["witnesses"]:
            self.assertIn("127.0.0.1", w["url"])


class ApiContract(unittest.TestCase):
    def test_module_functions_exist_with_contract_arguments(self):
        expected = {
            seal: {"load_config": ["path"], "get_key": ["cfg"], "append": ["evt", "cfg"],
                   "resync": ["cfg"], "reset": ["cfg"]},
            verify: {"verify": ["cfg", "log_path", "ledger_path", "use_witnesses"]},
            witness: {"push": ["entry", "cfg"], "head": ["url", "timeout"],
                      "entry": ["url", "seq", "timeout"], "reset": ["cfg"]},
        }
        for module, funcs in expected.items():
            for name, params in funcs.items():
                self.assertTrue(hasattr(module, name), f"{module.__name__}.{name} is missing")
                got = list(inspect.signature(getattr(module, name)).parameters)
                self.assertEqual(got, params, f"{module.__name__}.{name}{tuple(got)}")

    def test_core_modules_import_stdlib_only(self):
        stdlib = set(getattr(sys, "stdlib_module_names", ()))
        for filename in CORE_MODULES:
            imports = imported_names(os.path.join(ROOT, filename)) - LOCAL_MODULES - stdlib
            self.assertEqual(set(), imports, f"{filename} imports third-party modules: {sorted(imports)}")

    def test_every_python_file_parses(self):
        for filename in ALL_MODULES + ["seal.py"]:
            path = os.path.join(ROOT, filename)
            with open(path, encoding="utf-8") as f:
                ast.parse(f.read(), filename=path)


class EventContract(unittest.TestCase):
    def test_generated_event_has_exactly_the_contract_fields(self):
        import random
        event = gen.make_event(random.Random(7))
        self.assertEqual({"ts", "host", "user", "event", "src_ip", "msg"}, set(event))
        self.assertIn(event["event"], EVENT_TYPES)

    def test_canonical_line_and_ledger_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = make_cfg(tmp)
            import random
            evt = gen.make_event(random.Random(3))
            entry = seal.append(evt, cfg)
            raw = open(cfg["log_path"], "rb").read().rstrip(b"\n")
            evt["seq"] = 1
            self.assertEqual(json.dumps(evt, sort_keys=True, separators=(",", ":")).encode(), raw)
            self.assertEqual({"seq", "prev", "hash", "lhash", "mac"}, set(entry))
            self.assertEqual(1, entry["seq"])
            self.assertEqual(ZERO, entry["prev"])
            self.assertEqual(seal.sha(raw), entry["lhash"])
            self.assertEqual(seal.sha((ZERO + raw.decode()).encode()), entry["hash"])

    def test_verify_return_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = make_cfg(tmp)
            r = verify.verify(cfg, use_witnesses=False)
            self.assertEqual({"status", "checked_at", "log_lines", "ledger_entries",
                              "findings", "nodes", "feed"}, set(r))
            self.assertEqual("OK", r["status"])
            self.assertEqual([], r["findings"])
            self.assertEqual(1, len(r["nodes"]))
            self.assertEqual("server", r["nodes"][0]["role"])
            self.assertEqual({"name", "role", "reachable", "head_seq", "head_hash", "agrees"},
                             set(r["nodes"][0]))

    def test_finding_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = make_cfg(tmp)
            import random
            seal.append(gen.make_event(random.Random(1)), cfg)
            lines = open(cfg["log_path"], "rb").read().split(b"\n")[:-1]
            lines[0] = lines[0].replace(b"srv-01", b"srv-02", 1)
            open(cfg["log_path"], "wb").write(b"\n".join(lines) + b"\n")
            finding = verify.verify(cfg, use_witnesses=False)["findings"][0]
            self.assertEqual({"class", "seq", "expected", "actual", "detail", "confirmed_by"},
                             set(finding))
            self.assertIsInstance(finding["confirmed_by"], list)


if __name__ == "__main__":
    unittest.main()
