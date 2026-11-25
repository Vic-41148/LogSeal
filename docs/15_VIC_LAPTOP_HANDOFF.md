# 15. Vic laptop handoff: start Vault 1

Purpose: start one independent LogSeal vault on the `vic` laptop. This is the external vault for the two-laptop demo. Do not edit code. Do not start a generator or a console on this laptop.

## Fixed facts

| Item | Value |
|---|---|
| Laptop | `vic` |
| Tailscale IP | `100.107.224.36` |
| OS | Linux |
| Controller | `archlinux` at `100.100.12.125` |
| Repo | `https://github.com/Vic-41148/LogSeal.git` |
| Branch | `dev` |
| Vault name | `Vault 1` |
| Vault port | `8101` |
| Vault data | `~/logseal-vault1` |

The controller already runs `Vault 2` at `http://100.100.12.125:8101`. The root `config.json` points at both vaults.

## Steps

### 1. Check Tailscale

Run:

```bash
tailscale ip -4
tailscale ping 100.100.12.125
```

The first command must print `100.107.224.36`. The second command must print a `pong`.

If the IP is different, stop and report the new IP. The controller must update `config.json`.

### 2. Get the repo

If the repo is not on this laptop:

```bash
git clone https://github.com/Vic-41148/LogSeal.git
cd LogSeal
git switch dev
```

If the repo exists:

```bash
cd LogSeal
git switch dev
git pull --ff-only origin dev
```

Do not edit any file. Do not commit anything.

### 3. Check Python

```bash
python3 --version
```

The vault needs Python 3.11 or newer. It uses the standard library only. Do not install scikit-learn or Streamlit on this laptop.

### 4. Start the vault

Use a terminal that stays open during the demo:

```bash
mkdir -p ~/logseal-vault1
python3 witness.py --name "Vault 1" --port 8101 --allow-reset --dir ~/logseal-vault1
```

Expected output is one line like:

```text
Vault 1 listening: http://<address>:8101/  (holds 0 records)
```

The exact address does not matter. The vault binds `0.0.0.0:8101`.

If the agent must run the vault in the background, use:

```bash
mkdir -p ~/logseal-vault1
nohup python3 witness.py --name "Vault 1" --port 8101 --allow-reset --dir ~/logseal-vault1 > ~/logseal-vault1.log 2>&1 &
echo $!
```

Keep the process ID. Do not start a second vault on port 8101.

### 5. Check the vault locally

Open a second terminal on `vic`:

```bash
curl -fsS http://127.0.0.1:8101/head
curl -fsS http://100.107.224.36:8101/head
```

Both commands must return JSON with `"name": "Vault 1"`. A new vault returns `"count": 0` and a hash of 64 zeros.

Check the listener:

```bash
ss -ltnp | grep 8101
```

The output must show `0.0.0.0:8101`.

### 6. Open the status page

Open this URL in a browser on `vic`:

```text
http://100.107.224.36:8101/
```

The page must show `Vault 1`, the record count, the latest fingerprint and the green strip `ALL RECORDS CONSISTENT`.

### 7. Report back

Send this exact output to the controller:

```bash
hostname
tailscale ip -4
ss -ltnp | grep 8101
curl -fsS http://127.0.0.1:8101/head
curl -fsS http://100.107.224.36:8101/head
```

## Acceptance

- `Vault 1` listens on `0.0.0.0:8101`.
- `http://127.0.0.1:8101/head` returns `"name": "Vault 1"`.
- `http://100.107.224.36:8101/head` returns the same JSON.
- The status page loads and shows a green strip.
- The controller can seal events and this vault count increases.
- A rewrite attempt from the controller is rejected with `409 CONFLICT`.

## Troubleshooting

### Port 8101 is already in use

Find the old process:

```bash
ss -ltnp | grep 8101
```

Stop only an old `witness.py` process on port 8101. Do not stop other services.

### Python is missing

Ubuntu or Debian:

```bash
sudo apt update && sudo apt install -y python3
```

Arch:

```bash
sudo pacman -S --needed python
```

### Tailscale cannot reach the controller

```bash
tailscale status
tailscale ping 100.100.12.125
```

If the ping fails, reconnect Tailscale before you start the vault.

### The controller cannot reach the vault

On `vic`, check the listener again:

```bash
ss -ltnp | grep 8101
```

If the listener is correct, check the firewall. A connection refused error means the host rejects the packet. A timeout means the packet is dropped.

Arch with `nftables`:

```bash
sudo nft add table inet logseal
sudo nft add chain inet logseal input '{ type filter hook input priority 0; }'
sudo nft add rule inet logseal input iifname "tailscale0" tcp dport 8101 accept
sudo nft list ruleset | grep 8101
```

Arch with `iptables`:

```bash
sudo iptables -I INPUT -i tailscale0 -p tcp --dport 8101 -j ACCEPT
sudo iptables -S | grep 8101
```

Ubuntu or Debian:

```bash
sudo ufw allow 8101/tcp
sudo ufw reload
```

Fedora:

```bash
sudo firewall-cmd --add-port=8101/tcp --permanent
sudo firewall-cmd --reload
```

Then check from `vic`:

```bash
curl -fsS http://100.107.224.36:8101/head
```

Send the result to the controller. The controller must repeat the check from `archlinux`.

### The Tailscale IP changes

Stop the vault. Send the new IP. The controller must update `config.json` and restart the demo stack.

## Do not do these

- Do not run `gen.py`, `app.py`, `attack.py`, `ml.py` or `bench.py` on this laptop.
- Do not edit `witness.py` or any other code.
- Do not change `config.json`.
- Do not use `--allow-reset` outside the demo.
- Do not expose the vault outside the tailnet.
