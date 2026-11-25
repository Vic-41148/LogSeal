"""seal.py unit checks: chain, MAC, restart safety, reset, ledger rebuild."""
import hmac
import os
import tempfile
import unittest
from unittest import mock

import seal
from .support import ZERO, make_cfg, read_lines, seed


class SealChain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = make_cfg(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_chain_links_and_macs(self):
        seed(self.cfg, 10)
        entries = [json_loads(line) for line in read_lines(self.cfg["ledger_path"])]
        self.assertEqual(list(range(1, 11)), [e["seq"] for e in entries])
        self.assertEqual(ZERO, entries[0]["prev"])
        for before, after in zip(entries, entries[1:]):
            self.assertEqual(before["hash"], after["prev"])
        key = seal.get_key(self.cfg)
        for e in entries:
            want = hmac.new(key, f"{e['seq']}:{e['prev']}:{e['hash']}:{e['lhash']}".encode(),
                            "sha256").hexdigest()
            self.assertTrue(hmac.compare_digest(want, e["mac"]))

    def test_seq_continues_after_a_restart(self):
        seed(self.cfg, 3)
        import random
        entry = seal.append(__import__("gen").make_event(random.Random(4)), self.cfg)
        self.assertEqual(4, entry["seq"])
        self.assertEqual(4, len(read_lines(self.cfg["log_path"])))

    def test_key_comes_from_the_environment_first(self):
        with mock.patch.dict(os.environ, {self.cfg["hmac_key_env"]: "from-env"}):
            self.assertEqual(b"from-env", seal.get_key(self.cfg))
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(b"test-key", seal.get_key(self.cfg))

    def test_reset_clears_log_ledger_and_state(self):
        seed(self.cfg, 5)
        state = os.path.join(os.path.dirname(self.cfg["log_path"]), ".verify_state.json")
        with open(state, "w") as f:
            f.write("{}")
        seal.reset(self.cfg)
        self.assertEqual([], read_lines(self.cfg["log_path"]))
        self.assertEqual([], read_lines(self.cfg["ledger_path"]))
        self.assertFalse(os.path.exists(state))

    def test_rebuild_ledger_with_the_key_reproduces_the_same_bytes(self):
        seed(self.cfg, 20)
        before = open(self.cfg["ledger_path"], "rb").read()
        seal.rebuild_ledger(self.cfg)
        self.assertEqual(before, open(self.cfg["ledger_path"], "rb").read())

    def test_rebuild_without_key_fails_verification(self):
        import verify
        seed(self.cfg, 5)
        seal.rebuild_ledger(self.cfg, key=b"wrong-key")
        result = verify.verify(self.cfg, use_witnesses=False)
        self.assertEqual("TAMPERED", result["status"])
        self.assertIn("LEDGER_FORGED", {f["class"] for f in result["findings"]})

    def test_append_assigns_seq_and_ignores_a_supplied_seq(self):
        import random
        event = __import__("gen").make_event(random.Random(5))
        event["seq"] = 999
        entry = seal.append(event, self.cfg)
        self.assertEqual(1, entry["seq"])
        self.assertIn(b'"seq":1', read_lines(self.cfg["log_path"])[0])


def json_loads(raw):
    import json
    return json.loads(raw)


if __name__ == "__main__":
    unittest.main()
