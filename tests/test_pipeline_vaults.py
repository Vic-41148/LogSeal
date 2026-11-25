"""End-to-end: server + two real vault processes + verify()."""
import tempfile
import unittest

import seal
import verify
import witness
from .support import Vault, make_cfg, read_lines, seed, write_lines


class Pipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.v1 = Vault("Vault 1", self.tmp.name).start()
        self.v2 = Vault("Vault 2", self.tmp.name).start()
        self.addCleanup(self.v1.stop)
        self.addCleanup(self.v2.stop)
        self.cfg = make_cfg(self.tmp.name, witnesses=[
            {"name": "Vault 1", "url": self.v1.url},
            {"name": "Vault 2", "url": self.v2.url},
        ])
        seed(self.cfg, 60)

    def test_clean_run_all_three_agree(self):
        result = verify.verify(self.cfg)
        self.assertEqual("OK", result["status"])
        self.assertEqual([], result["findings"])
        self.assertEqual(3, len(result["nodes"]))
        self.assertTrue(result["nodes"][0]["agrees"])
        self.assertTrue(result["nodes"][1]["agrees"])
        self.assertTrue(result["nodes"][2]["agrees"])
        self.assertEqual(60, result["nodes"][0]["head_seq"])
        self.assertEqual(60, result["nodes"][1]["head_seq"])

    def test_manual_edit_names_the_record_and_both_vaults_confirm(self):
        lines = read_lines(self.cfg["log_path"])
        lines[23] = lines[23].replace(b"srv-01", b"srv-02", 1)
        write_lines(self.cfg["log_path"], lines)
        result = verify.verify(self.cfg)
        self.assertEqual("TAMPERED", result["status"])
        self.assertEqual("EDIT", result["findings"][0]["class"])
        self.assertEqual(24, result["findings"][0]["seq"])
        self.assertEqual({"Vault 1", "Vault 2"}, set(result["findings"][0]["confirmed_by"]))
        self.assertFalse(result["nodes"][0]["agrees"])
        self.assertTrue(result["nodes"][1]["agrees"])
        self.assertTrue(result["nodes"][2]["agrees"])

    def test_root_rewrite_is_green_locally_and_red_at_the_vaults(self):
        lines = read_lines(self.cfg["log_path"])
        lines[19] = lines[19].replace(b"srv-01", b"evil", 1)
        write_lines(self.cfg["log_path"], lines)
        seal.rebuild_ledger(self.cfg)

        local = verify.verify(self.cfg, use_witnesses=False)
        self.assertEqual("OK", local["status"], "the attacker fixed the server files")

        result = verify.verify(self.cfg)
        self.assertEqual("TAMPERED", result["status"])
        conflict = next(f for f in result["findings"] if f["class"] == "WITNESS_CONFLICT")
        self.assertEqual(20, conflict["seq"])
        self.assertTrue(result["nodes"][0]["agrees"])
        self.assertFalse(result["nodes"][1]["agrees"])
        self.assertFalse(result["nodes"][2]["agrees"])

    def test_vault_rejects_the_rewritten_entry(self):
        lines = read_lines(self.cfg["log_path"])
        lines[19] = lines[19].replace(b"srv-01", b"evil", 1)
        write_lines(self.cfg["log_path"], lines)
        seal.rebuild_ledger(self.cfg)
        rewritten = seal._ledger_entries(self.cfg)[19]
        results = witness.push(rewritten, self.cfg)
        self.assertEqual({409}, {r["status"] for r in results})

    def test_consistent_wipe_leaves_the_vault_ahead(self):
        lines = read_lines(self.cfg["log_path"])
        write_lines(self.cfg["log_path"], lines[:30])
        seal.rebuild_ledger(self.cfg)
        self.assertEqual("OK", verify.verify(self.cfg, use_witnesses=False)["status"])
        result = verify.verify(self.cfg)
        self.assertEqual("TAMPERED", result["status"])
        ahead = next(f for f in result["findings"] if f["class"] == "WITNESS_AHEAD")
        self.assertEqual(31, ahead["seq"])

    def test_vault_that_is_behind_agrees_and_resync_catches_up(self):
        v3 = Vault("Vault 3", self.tmp.name).start()
        self.addCleanup(v3.stop)
        self.cfg["witnesses"].append({"name": "Vault 3", "url": v3.url})
        result = verify.verify(self.cfg)
        self.assertEqual("OK", result["status"])
        node = result["nodes"][3]
        self.assertTrue(node["agrees"])
        self.assertEqual(0, node["head_seq"])

        seal.resync(self.cfg)
        self.assertEqual(60, v3.head()["count"])
        self.assertEqual("OK", verify.verify(self.cfg)["status"])

    def test_one_dead_vault_goes_grey_and_does_not_stop_the_check(self):
        self.v2.stop()
        self.cfg["witness_timeout_s"] = 0.3
        result = verify.verify(self.cfg)
        self.assertEqual("OK", result["status"])
        self.assertFalse(result["nodes"][2]["reachable"])
        self.assertIsNone(result["nodes"][2]["agrees"])

    def test_restore_after_a_rewrite_returns_to_green(self):
        original_log = open(self.cfg["log_path"], "rb").read()
        original_ledger = open(self.cfg["ledger_path"], "rb").read()
        lines = read_lines(self.cfg["log_path"])
        lines[19] = lines[19].replace(b"srv-01", b"evil", 1)
        write_lines(self.cfg["log_path"], lines)
        seal.rebuild_ledger(self.cfg)
        self.assertEqual("TAMPERED", verify.verify(self.cfg)["status"])

        open(self.cfg["log_path"], "wb").write(original_log)
        open(self.cfg["ledger_path"], "wb").write(original_ledger)
        self.assertEqual("OK", verify.verify(self.cfg)["status"])


if __name__ == "__main__":
    unittest.main()
