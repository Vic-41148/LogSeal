# 16. Two Windows laptops: two-vault demo link

Purpose: link two Windows laptops over Tailscale and run the LogSeal demo with one vault on each laptop. Laptop A runs the controller, the console and `Vault 2`. Laptop B runs `Vault 1`. Use PowerShell on both laptops. You do not need SSH.

## Fixed facts

| Item | Value |
|---|---|
| Repo | `https://github.com/Vic-41148/LogSeal.git` |
| Branch | `dev` |
| Python | 3.11 or newer. Use 3.12 for the console. |
| Vault script | `witness.py`. Standard library only. |
| Vault port | 8101 on each laptop |
| Console port | 8501 on Laptop A |
| Vault 1 data | `%USERPROFILE%\logseal-vault1` on Laptop B |
| Vault 2 data | `%USERPROFILE%\logseal-vault2` on Laptop A |
| Controller config | `config.windows.json` on Laptop A. Do not edit `config.json`. |

Write down the Tailscale IP of each laptop. The steps call them `A_IP` and `B_IP`.

## 1. Install Tailscale on both laptops

1. Install Tailscale from `https://tailscale.com/download/windows`.
2. Sign in with the same account on both laptops. Both laptops must join the same tailnet.
3. Open PowerShell and run:

```powershell
& "$env:ProgramFiles\Tailscale\tailscale.exe" status
& "$env:ProgramFiles\Tailscale\tailscale.exe" ip -4
```

4. Record the IPv4 address as `A_IP` on Laptop A and `B_IP` on Laptop B.
5. From Laptop A, run:

```powershell
& "$env:ProgramFiles\Tailscale\tailscale.exe" ping B_IP
```

Replace `B_IP` with the real address. The command must print `pong`. From Laptop B, ping `A_IP` the same way.

If the ping fails, fix Tailscale before you start a vault.

## 2. Install Python on both laptops

```powershell
python --version
py -3 --version
```

Use the command that prints `Python 3.11` or newer. If neither works, install Python from `https://www.python.org/downloads/windows/`. Select `Add Python to PATH` during setup.

The vaults need the standard library only. Do not install extra packages on Laptop B.

## 3. Get the repo on both laptops

Run these commands in PowerShell on each laptop:

```powershell
git clone https://github.com/Vic-41148/LogSeal.git
cd LogSeal
git switch dev
git pull --ff-only origin dev
```

If the repo already exists, skip the clone and run the last two lines only. Do not edit code. Do not commit files.

## 4. Open the vault port in Windows Firewall on both laptops

Open PowerShell as Administrator on each laptop. Run:

```powershell
New-NetFirewallRule -DisplayName "LogSeal Vault 8101" -Direction Inbound -Protocol TCP -LocalPort 8101 -Action Allow -Profile Domain,Private
Get-NetFirewallRule -DisplayName "LogSeal Vault 8101" | Select-Object DisplayName,Enabled,Direction,Action
```

The second command must show `Enabled` as `True`, `Direction` as `Inbound` and `Action` as `Allow`.

If the rule already exists, skip the first command. To remove a rule, run:

```powershell
Remove-NetFirewallRule -DisplayName "LogSeal Vault 8101"
```

A connection refused error means a firewall rejected the packet. A timeout means a Tailscale ACL dropped the packet.

## 5. Start Vault 1 on Laptop B

Keep this PowerShell window open during the demo:

```powershell
mkdir "$env:USERPROFILE\logseal-vault1"
cd LogSeal
python witness.py --name "Vault 1" --port 8101 --allow-reset --dir "$env:USERPROFILE\logseal-vault1"
```

Expected output is one line:

```text
Vault 1 listening: http://0.0.0.0:8101/  (holds 0 records)
```

The printed address can differ. The vault binds port 8101 on all interfaces.

Check the vault from Laptop B:

```powershell
curl.exe http://127.0.0.1:8101/head
curl.exe http://B_IP:8101/head
```

Both commands must return JSON with `"name": "Vault 1"`. A fresh vault returns `"count": 0` and a hash of 64 zeros.

## 6. Start Vault 2 on Laptop A

Open a second PowerShell window on Laptop A. Keep it open during the demo:

```powershell
mkdir "$env:USERPROFILE\logseal-vault2"
cd LogSeal
python witness.py --name "Vault 2" --port 8101 --allow-reset --dir "$env:USERPROFILE\logseal-vault2"
```

Expected output is one line that names `Vault 2` and port 8101.

Check the vault from Laptop A:

```powershell
curl.exe http://127.0.0.1:8101/head
curl.exe http://A_IP:8101/head
```

Both commands must return JSON with `"name": "Vault 2"`.

## 7. Write the controller config on Laptop A

Create `config.windows.json` in the repo folder on Laptop A. Use this JSON. Replace both IP placeholders:

```json
{
  "log_path": "app.log.jsonl",
  "ledger_path": "ledger.jsonl",
  "hmac_key_env": "LOGSEAL_KEY",
  "hmac_key_default": "demo-key-change-me",
  "witnesses": [
    {"name": "Vault 1", "url": "http://B_IP:8101"},
    {"name": "Vault 2", "url": "http://A_IP:8101"}
  ],
  "witness_timeout_s": 1.5,
  "pending_grace_s": 3
}
```

Keep the name order. Keep port 8101 on both URLs. Use Tailscale IPs, not Wi-Fi IPs. Do not commit this file.

Check the config:

```powershell
python -c 'import seal; print(seal.load_config("config.windows.json")["witnesses"])'
```

## 8. Start the console on Laptop A

Only Laptop A needs these packages:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
$env:LOGSEAL_CONFIG = "config.windows.json"
.\.venv\Scripts\python -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

Keep this window open. Check the console from Laptop A:

```powershell
curl.exe http://127.0.0.1:8501/_stcore/health
```

The command must print `ok`.

Open `http://A_IP:8501` in a browser. Use `?stage=1` for the projector theme. The page must show three tiles: Server, Vault 1 and Vault 2.

## 9. Check both vaults from Laptop A

```powershell
curl.exe http://B_IP:8101/head
curl.exe http://A_IP:8101/head
```

The first answer must name `Vault 1`. The second answer must name `Vault 2`. If an answer fails, stop and fix the firewall or the config.

## 10. Seal events and verify across the tailnet

Run this on Laptop A:

```powershell
python -c 'import seal, verify, gen, random, json; cfg=seal.load_config("config.windows.json"); [seal.append(gen.make_event(random.Random(i)), cfg) for i in range(20)]; r=verify.verify(cfg); print(json.dumps({"status": r["status"], "nodes": [{"name": n["name"], "agrees": n["agrees"], "head_seq": n["head_seq"]} for n in r["nodes"]]}, indent=2))'
```

Expected result:

- `status` is `OK`.
- Three nodes appear: Server, Vault 1 and Vault 2.
- `agrees` is `true` for each node.
- `head_seq` is 20 for each node.

Both vault counts must now read 20. Check them:

```powershell
curl.exe http://B_IP:8101/head
curl.exe http://A_IP:8101/head
```

## 11. Reset before the pitch

Run this on Laptop A:

```powershell
python -c 'import seal; seal.reset(seal.load_config("config.windows.json"))'
curl.exe http://B_IP:8101/head
curl.exe http://A_IP:8101/head
```

Both vaults must return `"count": 0`. The console must show a green banner with three green tiles.

## Acceptance

- `tailscale ping` works in both directions.
- Port 8101 is open on both laptops.
- Vault 1 lives on Laptop B. Vault 2 lives on Laptop A.
- `curl.exe` reaches each vault through its Tailscale IP from Laptop A.
- The console shows Server, Vault 1 and Vault 2.
- Twenty sealed events give `status: OK` and `head_seq: 20` on three nodes.
- Reset returns both vaults to zero records.

## Troubleshooting

### Port 8101 is already in use

```powershell
Get-NetTCPConnection -LocalPort 8101 | Select-Object LocalAddress,LocalPort,State,OwningProcess
```

Stop only an old `python` process that runs `witness.py`. Do not stop other services.

### The controller gets connection refused

Run the firewall rule from step 4 on the vault laptop as Administrator. Then repeat the `curl.exe` check.

### The controller gets a timeout

Check Tailscale on both laptops:

```powershell
& "$env:ProgramFiles\Tailscale\tailscale.exe" status
& "$env:ProgramFiles\Tailscale\tailscale.exe" ping OTHER_IP
```

Replace `OTHER_IP` with the peer address. Reconnect Tailscale if the ping fails.

### A vault answers with the wrong name

Stop the vault with `Ctrl+C`. Start it again with the exact name from step 5 or step 6. The names must match the config.

### The console shows a vault as offline

Check the config on Laptop A. Confirm both Tailscale IPs and port 8101. Then check the vault with `curl.exe` from Laptop A.

### A Tailscale IP changes

Update `config.windows.json` on Laptop A. Restart the console. The vaults can keep running.

## Do not do these

- Do not run `gen.py`, `attack.py`, `ml.py` or `bench.py` on a vault laptop.
- Do not install Streamlit or scikit-learn on Laptop B.
- Do not edit `witness.py` or any other code.
- Do not edit or commit the tracked `config.json`.
- Do not use `--allow-reset` outside the demo.
- Do not expose port 8101 outside the tailnet.
