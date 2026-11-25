"""Shared helpers for the LogSeal test suite. Stdlib only.

Every test uses its own temp folder and its own ports, so four people can run
the suite at the same time on one machine.
"""
import json
import os
import random
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import gen       # noqa: E402
import seal      # noqa: E402
import verify    # noqa: E402,F401  (re-exported for tests)
import witness   # noqa: E402

ZERO = "0" * 64
EVENT_TYPES = {"login_ok", "login_fail", "logout", "file_read",
               "file_write", "sudo", "config_change"}


def free_port():
    """Return a currently free localhost port."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def make_cfg(folder, witnesses=(), grace=3.0, timeout=0.5, key="test-key"):
    """A config dict that points at files inside `folder`."""
    os.makedirs(folder, exist_ok=True)
    return {
        "log_path": os.path.join(folder, "app.log.jsonl"),
        "ledger_path": os.path.join(folder, "ledger.jsonl"),
        "hmac_key_env": "LOGSEAL_TEST_KEY",
        "hmac_key_default": key,
        "witnesses": list(witnesses),
        "witness_timeout_s": timeout,
        "pending_grace_s": grace,
    }


def seed(cfg, n=50, seed_value=1):
    """Append n valid events through the real seal.append()."""
    rng = random.Random(seed_value)
    for _ in range(n):
        seal.append(gen.make_event(rng), cfg)


def read_lines(path):
    """Raw log lines without the trailing newline."""
    try:
        with open(path, "rb") as f:
            parts = f.read().split(b"\n")
    except FileNotFoundError:
        return []
    if parts and parts[-1] == b"":
        parts.pop()
    return parts


def write_lines(path, lines):
    with open(path, "wb") as f:
        f.write(b"\n".join(lines) + (b"\n" if lines else b""))


class Vault:
    """Run witness.py as a real subprocess and stop it cleanly."""

    def __init__(self, name, folder, allow_reset=True):
        self.name = name
        self.folder = folder
        self.allow_reset = allow_reset
        self.proc = None
        self.port = None
        self.url = None

    def start(self, port=None):
        self.port = port or free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        cmd = [sys.executable, os.path.join(ROOT, "witness.py"),
               "--name", self.name, "--port", str(self.port), "--dir", self.folder]
        if self.allow_reset:
            cmd.append("--allow-reset")
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for _ in range(100):
            if witness.head(self.url, 0.3) is not None:
                return self
            if self.proc.poll() is not None:
                break
            time.sleep(0.05)
        self.proc.terminate()
        try:
            output = self.proc.communicate(timeout=2)[0]
        except subprocess.TimeoutExpired:
            self.proc.kill()
            output = b""
        raise RuntimeError(f"{self.name} did not start on {self.url}: {output.decode('utf-8', 'replace')[-500:]}")

    def stop(self):
        if self.proc:
            if self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait()
            if self.proc.stdout:
                self.proc.stdout.close()
        self.proc = None

    def head(self):
        return witness.head(self.url, 1.0)

    def page(self):
        import urllib.request
        with urllib.request.urlopen(self.url + "/", timeout=2) as r:
            return r.read().decode("utf-8")

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
