"""The mutation table from docs/04_TASK_seal_verify.md, one test per row."""
import random
import tempfile
import threading
import time
import unittest

import gen
import seal
import verify
from .support import make_cfg, read_lines, seed, write_lines


class VerifyMutations(unittest.TestCase):
    def fresh(self, n=50, grace=3.0):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cfg = make_cfg(tmp.name, grace=grace)
        seed(cfg, n)
        return cfg

    def classes(self, cfg):
        result = verify.verify(cfg, use_witnesses=False)
        return result, {f["class"] for f in result["findings"]}

    def test_clean_log_is_ok(self):
        self.assertEqual("OK", verify.verify(self.fresh(), use_witnesses=False)["status"])

    def test_edit_one_character_is_edit_at_that_record(self):
        cfg = self.fresh()
        lines = read_lines(cfg["log_path"])
        lines[23] = lines[23].replace(b"srv-01", b"srv-02", 1)
        write_lines(cfg["log_path"], lines)
        result, classes = self.classes(cfg)
        self.assertEqual("TAMPERED", result["status"])
        self.assertIn("EDIT", classes)
        self.assertEqual(24, result["findings"][0]["seq"])

    def test_add_one_space_is_edit(self):
        cfg = self.fresh()
        lines = read_lines(cfg["log_path"])
        lines[10] += b" "
        write_lines(cfg["log_path"], lines)
        result, classes = self.classes(cfg)
        self.assertIn("EDIT", classes)
        self.assertEqual(11, result["findings"][0]["seq"])

    def test_delete_a_middle_line(self):
        cfg = self.fresh()
        lines = read_lines(cfg["log_path"])
        del lines[19]
        write_lines(cfg["log_path"], lines)
        result, classes = self.classes(cfg)
        self.assertIn("DELETE", classes)
        self.assertEqual(20, result["findings"][0]["seq"])

    def test_insert_a_line_in_the_middle(self):
        cfg = self.fresh()
        lines = read_lines(cfg["log_path"])
        lines.insert(30, b'{"event":"login_ok","user":"mallory"}')
        write_lines(cfg["log_path"], lines)
        result, classes = self.classes(cfg)
        self.assertIn("INSERT", classes)
        self.assertEqual(31, result["findings"][0]["seq"])

    def test_drop_last_five_lines(self):
        cfg = self.fresh()
        write_lines(cfg["log_path"], read_lines(cfg["log_path"])[:-5])
        result, classes = self.classes(cfg)
        self.assertIn("TRUNCATE", classes)
        self.assertEqual(46, result["findings"][0]["seq"])

    def test_swap_two_adjacent_lines(self):
        cfg = self.fresh()
        lines = read_lines(cfg["log_path"])
        lines[9], lines[10] = lines[10], lines[9]
        write_lines(cfg["log_path"], lines)
        result, classes = self.classes(cfg)
        self.assertEqual("TAMPERED", result["status"])
        self.assertIn("EDIT", classes)

    def test_forge_one_ledger_entry(self):
        cfg = self.fresh()
        lines = read_lines(cfg["ledger_path"])
        lines[14] = lines[14].replace(b'"hash":"', b'"hash":"0', 1)
        write_lines(cfg["ledger_path"], lines)
        result, classes = self.classes(cfg)
        self.assertIn("LEDGER_FORGED", classes)
        self.assertEqual(15, next(f["seq"] for f in result["findings"] if f["class"] == "LEDGER_FORGED"))

    def test_multiple_edits_still_alarms(self):
        cfg = self.fresh()
        lines = read_lines(cfg["log_path"])
        for i in (5, 6, 7):
            lines[i] = lines[i].replace(b"srv-01", b"srv-99", 1)
        write_lines(cfg["log_path"], lines)
        self.assertEqual("TAMPERED", verify.verify(cfg, use_witnesses=False)["status"])

    def test_feed_has_last_fifty_rows_and_marks_bad_seq(self):
        cfg = self.fresh(n=60)
        lines = read_lines(cfg["log_path"])
        lines[59] = lines[59].replace(b"srv-01", b"srv-02", 1)
        write_lines(cfg["log_path"], lines)
        result = verify.verify(cfg, use_witnesses=False)
        self.assertEqual(50, len(result["feed"]))
        self.assertEqual(60, result["feed"][-1]["seq"])
        self.assertFalse(result["feed"][-1]["ok"])
        self.assertTrue(all(row["ok"] for row in result["feed"][:-1]))

    def test_unparseable_line_is_marked_in_the_feed(self):
        cfg = self.fresh(n=3)
        with open(cfg["log_path"], "ab") as f:
            f.write(b"this is not json\n")
        result = verify.verify(cfg, use_witnesses=False)
        self.assertEqual(4, result["feed"][-1]["seq"])
        self.assertEqual("UNPARSEABLE", result["feed"][-1]["event"])
        self.assertFalse(result["feed"][-1]["ok"])


class PendingAndUnsealed(unittest.TestCase):
    def test_line_without_ledger_entry_is_pending_then_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = make_cfg(tmp, grace=0.4)
            event = gen.make_event(random.Random(1))
            line, entry = seal._build(event, cfg)
            seal._write(cfg["log_path"], line + "\n")
            self.assertEqual("PENDING", verify.verify(cfg, use_witnesses=False)["status"])
            seal._write(cfg["ledger_path"], seal._dump(entry) + "\n")
            self.assertEqual("OK", verify.verify(cfg, use_witnesses=False)["status"])

    def test_line_never_sealed_is_unsealed_after_grace(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = make_cfg(tmp, grace=0.15)
            line, _ = seal._build(gen.make_event(random.Random(2)), cfg)
            seal._write(cfg["log_path"], line + "\n")
            verify.verify(cfg, use_witnesses=False)
            time.sleep(0.3)
            result = verify.verify(cfg, use_witnesses=False)
            self.assertEqual("TAMPERED", result["status"])
            self.assertIn("UNSEALED", {f["class"] for f in result["findings"]})


class LiveWriter(unittest.TestCase):
    def test_no_false_alarms_during_live_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = make_cfg(tmp)
            bad = []

            def writer():
                rng = random.Random(7)
                for _ in range(100):
                    seal.append(gen.make_event(rng), cfg)

            thread = threading.Thread(target=writer)
            thread.start()
            calls = 0
            while thread.is_alive() or calls < 50:
                result = verify.verify(cfg, use_witnesses=False)
                calls += 1
                if result["status"] == "TAMPERED":
                    bad.append(result["findings"])
            thread.join()
            self.assertEqual([], bad)
            final = verify.verify(cfg, use_witnesses=False)
            self.assertIn(final["status"], ("OK", "PENDING"))
            self.assertEqual([], final["findings"])

    def test_verify_one_thousand_events_under_one_second(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = make_cfg(tmp)
            seed(cfg, 1000)
            start = time.perf_counter()
            result = verify.verify(cfg, use_witnesses=False)
            elapsed = time.perf_counter() - start
            self.assertEqual("OK", result["status"])
            self.assertLess(elapsed, 1.0, f"{elapsed * 1000:.0f} ms")


if __name__ == "__main__":
    unittest.main()
