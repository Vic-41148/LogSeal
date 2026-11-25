"""witness.py server and client helpers against the HTTP contract."""
import tempfile
import time
import unittest

import witness
from .support import Vault, free_port

A, B, C = "a" * 64, "b" * 64, "c" * 64
ZERO = "0" * 64


def entry(seq, prev, h):
    return {"seq": seq, "prev": prev, "hash": h}


class WitnessApi(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.vault = Vault("Vault 1", self.tmp.name).start()
        self.addCleanup(self.vault.stop)

    def post(self, path, body):
        return witness._req(self.vault.url + path, body, 1.0)

    def test_empty_head(self):
        h = self.vault.head()
        self.assertEqual(0, h["count"])
        self.assertEqual(ZERO, h["hash"])
        self.assertEqual("Vault 1", h["name"])

    def test_append_sequence_and_boundaries(self):
        self.assertEqual(200, self.post("/append", entry(1, ZERO, A))[0])
        self.assertEqual(200, self.post("/append", entry(2, A, B))[0])
        head = self.vault.head()
        self.assertEqual(2, head["count"])
        self.assertEqual(B, head["hash"])
        self.assertEqual(200, self.post("/append", entry(3, B, C))[0])
        self.assertEqual(3, self.vault.head()["count"])

    def test_duplicate_is_accepted_without_change(self):
        self.post("/append", entry(1, ZERO, A))
        status, body = self.post("/append", entry(1, ZERO, A))
        self.assertEqual(200, status)
        self.assertTrue(body["duplicate"])
        self.assertEqual(1, self.vault.head()["count"])

    def test_conflicting_hash_is_rejected_and_shown(self):
        self.post("/append", entry(1, ZERO, A))
        self.post("/append", entry(2, A, B))
        status, body = self.post("/append", entry(2, A, C))
        self.assertEqual(409, status)
        self.assertEqual("CONFLICT", body["error"])
        self.assertEqual(B, body["stored"])
        self.assertEqual(C, body["offered"])
        page = self.vault.page()
        self.assertIn("REWRITE ATTEMPT REJECTED", page)
        self.assertIn("Record #2", page)
        self.assertEqual(2, self.vault.head()["count"])     # rejected entry did not change the head

    def test_gap_and_wrong_prev_are_rejected(self):
        status, body = self.post("/append", entry(2, ZERO, A))
        self.assertEqual(422, status)
        self.assertEqual("GAP", body["error"])
        self.post("/append", entry(1, ZERO, A))
        status, body = self.post("/append", entry(2, C, B))   # prev is not the head
        self.assertEqual(422, status)
        self.assertEqual(1, self.vault.head()["count"])

    def test_entry_lookup_and_404(self):
        self.post("/append", entry(1, ZERO, A))
        got = witness.entry(self.vault.url, 1, 1.0)
        self.assertEqual(A, got["hash"])
        self.assertIsNone(witness.entry(self.vault.url, 2, 1.0))

    def test_restart_keeps_entries_and_conflicts(self):
        self.post("/append", entry(1, ZERO, A))
        self.post("/append", entry(2, A, B))
        self.post("/append", entry(2, A, C))
        self.vault.stop()
        self.vault.start()
        self.assertEqual(2, self.vault.head()["count"])
        self.assertIn("REWRITE ATTEMPT REJECTED", self.vault.page())

    def test_reset_requires_the_flag(self):
        closed = Vault("Vault 2", self.tmp.name, allow_reset=False).start()
        try:
            status, _ = witness._req(closed.url + "/reset", {}, 1.0)
            self.assertEqual(403, status)
        finally:
            closed.stop()

    def test_reset_clears_with_the_flag(self):
        self.post("/append", entry(1, ZERO, A))
        status, _ = self.post("/reset", {})
        self.assertEqual(200, status)
        self.assertEqual(0, self.vault.head()["count"])

    def test_client_helpers_never_raise(self):
        dead = f"http://127.0.0.1:{free_port()}"
        self.assertIsNone(witness.head(dead, 0.2))
        self.assertIsNone(witness.entry(dead, 1, 0.2))
        cfg = {"witnesses": [{"name": "Dead", "url": dead}], "witness_timeout_s": 0.2}
        start = time.perf_counter()
        result = witness.push(entry(1, ZERO, A), cfg)
        self.assertEqual(1, len(result))
        self.assertFalse(result[0]["ok"])
        self.assertLess(time.perf_counter() - start, 2.0)

    def test_reset_client_never_raises(self):
        dead = f"http://127.0.0.1:{free_port()}"
        result = witness.reset({"witnesses": [{"name": "Dead", "url": dead}],
                                "witness_timeout_s": 0.2})
        self.assertEqual("Dead", result[0]["name"])
        self.assertIsNone(result[0]["status"])


if __name__ == "__main__":
    unittest.main()
