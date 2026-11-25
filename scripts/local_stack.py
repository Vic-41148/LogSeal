#!/usr/bin/env python3
"""Run a private LogSeal stack: two vaults, optional generator and console.

Each developer uses a different --name. Ports, config, logs and data stay inside
.run/<name>/, so four people can run at the same time on one machine.

  python scripts/local_stack.py up --name p1 --with-gen --with-console
  python scripts/local_stack.py status --name p1
  python scripts/local_stack.py down --name p1
  python scripts/local_stack.py reset --name p1
"""
import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
RUN = os.path.join(ROOT, ".run")


def free_block(start, count):
    for offset in range(0, 4000, 4):
        ports = [start + offset + i for i in range(count)]
        if all(_free(port) for port in ports):
            return ports
    raise RuntimeError("no free port block")


def _free(port):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def paths(name):
    folder = os.path.join(RUN, name)
    return {
        "dir": folder,
        "config": os.path.join(folder, "config.json"),
        "pids": os.path.join(folder, "pids.json"),
    }


def base_port(name):
    return 18000 + (int(hashlib.sha256(name.encode()).hexdigest()[:8], 16) % 300) * 4


def load_pids(name):
    p = paths(name)["pids"]
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def head(url, timeout=0.4):
    try:
        with urllib.request.urlopen(url + "/head", timeout=timeout) as response:
            return json.loads(response.read())
    except Exception:
        return None


def spawn(cmd, log_path, env=None):
    handle = open(log_path, "ab")
    try:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT,
                                start_new_session=True, env=env)
    finally:
        handle.close()
    return proc


def start_vault(name, number, port, folder):
    proc = spawn([sys.executable, os.path.join(ROOT, "witness.py"),
                  "--name", f"Vault {number}", "--port", str(port), "--allow-reset",
                  "--dir", folder], os.path.join(folder, f"vault{number}.log"))
    for _ in range(100):
        if head(f"http://127.0.0.1:{port}") is not None:
            return proc
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    raise RuntimeError(f"Vault {number} did not start; read {folder}/vault{number}.log")


def up(name, with_gen, with_console, rate):
    p = paths(name)
    os.makedirs(p["dir"], exist_ok=True)
    pids = load_pids(name)
    if any(alive(pid) for pid in pids.values()):
        raise SystemExit(f"stack '{name}' is already running. Run: down --name {name}")

    [v1, v2, console_port] = free_block(base_port(name), 3)
    cfg = {
        "log_path": "app.log.jsonl",
        "ledger_path": "ledger.jsonl",
        "hmac_key_env": "LOGSEAL_KEY",
        "hmac_key_default": "demo-key-change-me",
        "witnesses": [
            {"name": "Vault 1", "url": f"http://127.0.0.1:{v1}"},
            {"name": "Vault 2", "url": f"http://127.0.0.1:{v2}"},
        ],
        "witness_timeout_s": 1.0,
        "pending_grace_s": 3,
    }
    with open(p["config"], "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    running = {}
    try:
        running["vault1"] = start_vault(name, 1, v1, p["dir"]).pid
        running["vault2"] = start_vault(name, 2, v2, p["dir"]).pid
        if with_gen:
            running["gen"] = spawn([sys.executable, os.path.join(ROOT, "gen.py"),
                                    "--config", p["config"], "--rate", str(rate)],
                                   os.path.join(p["dir"], "gen.log")).pid
        if with_console:
            try:
                import streamlit  # noqa: F401
            except ImportError:
                print("streamlit is not installed; skipped the console")
            else:
                env = dict(os.environ, LOGSEAL_CONFIG=p["config"])
                running["console"] = spawn([sys.executable, "-m", "streamlit", "run",
                                            os.path.join(ROOT, "app.py"),
                                            "--server.port", str(console_port),
                                            "--server.address", "127.0.0.1",
                                            "--server.headless", "true"],
                                           os.path.join(p["dir"], "console.log"), env).pid
    except Exception:
        for pid in running.values():
            _terminate(pid)
        raise

    with open(p["pids"], "w", encoding="utf-8") as f:
        json.dump(running, f, indent=2)

    print(f"stack '{name}' ready")
    print(f"  config   {p['config']}")
    print(f"  Vault 1  http://127.0.0.1:{v1}/")
    print(f"  Vault 2  http://127.0.0.1:{v2}/")
    if "console" in running:
        print(f"  console  http://127.0.0.1:{console_port}/")
    if "gen" in running:
        print(f"  events   generator running at {rate}/s")
    print(f"  logs     {p['dir']}/*.log")
    print(f"  stop     python scripts/local_stack.py down --name {name}")


def _terminate(pid):
    try:
        if os.name == "nt":
            os.kill(pid, signal.SIGTERM)
        else:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
    except OSError:
        pass


def down(name):
    pids = load_pids(name)
    for role, pid in pids.items():
        if alive(pid):
            _terminate(pid)
            print(f"stopped {role} (pid {pid})")
    try:
        os.remove(paths(name)["pids"])
    except OSError:
        pass


def status(name):
    p = paths(name)
    if not os.path.exists(p["config"]):
        print(f"no stack '{name}'. Run: up --name {name}")
        return
    with open(p["config"], encoding="utf-8") as f:
        cfg = json.load(f)
    pids = load_pids(name)
    print(f"stack '{name}'  config {p['config']}")
    for role, pid in pids.items():
        print(f"  {role:8} pid {pid:<7} {'alive' if alive(pid) else 'DEAD'}")
    for witness in cfg["witnesses"]:
        h = head(witness["url"])
        label = "OFFLINE" if h is None else f"count {h['count']}"
        print(f"  {witness['name']:8} {label}")


def reset(name):
    p = paths(name)
    if not os.path.exists(p["config"]):
        raise SystemExit(f"no stack '{name}'")
    if any(alive(pid) for pid in load_pids(name).values()):
        raise SystemExit(f"stop the stack first: down --name {name}")
    import seal
    cfg = seal.load_config(p["config"])
    seal.reset(cfg)
    print(f"reset '{name}': log, ledger and both vaults are empty")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["up", "down", "status", "reset"])
    parser.add_argument("--name", default=os.environ.get("LOGSEAL_STACK", os.environ.get("USER", "dev")))
    parser.add_argument("--with-gen", action="store_true")
    parser.add_argument("--with-console", action="store_true")
    parser.add_argument("--rate", type=float, default=2.0)
    args = parser.parse_args()
    {"up": lambda: up(args.name, args.with_gen, args.with_console, args.rate),
     "down": lambda: down(args.name), "status": lambda: status(args.name),
     "reset": lambda: reset(args.name)}[args.command]()


if __name__ == "__main__":
    main()
