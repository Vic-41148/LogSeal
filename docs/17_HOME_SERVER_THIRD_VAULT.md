# 17. Home server as the third vault

This adds a third independent vault on `vic-home-server`. It needs no new code. `witness.py` is standard library only.

## Fixed facts

| Item | Value |
|---|---|
| Machine | `vic-home-server` |
| Tailscale IP | `100.81.208.118` |
| SSH user | `vic41148` |
| Vault name | `Vault 3` |
| Vault port | `8101` |
| Vault data | `~/logseal-vault3` |
| Controller | `archlinux` at `100.100.12.125` |

## Start the vault

Copy only `witness.py`. No repo clone is needed on the home server.

```bash
scp witness.py vic41148@100.81.208.118:~/witness.py
ssh vic41148@100.81.208.118
mkdir -p ~/logseal-vault3
nohup python3 ~/witness.py --name "Vault 3" --port 8101 --allow-reset \
  --dir ~/logseal-vault3 > ~/logseal-vault3.log 2>&1 &
```

Check from the controller:

```bash
curl -fsS http://100.81.208.118:8101/head
```

## Why the timeout is 5 seconds

The first test used `witness_timeout_s: 1.0`. Pushes to Vault 3 timed out over Tailscale. The vault fell behind and never caught up. The config now uses `witness_timeout_s: 5.0`. After this change, reset every vault and replay from record 1. A vault that misses a push cannot fill the gap by itself.

## Check after a reset

Stop `gen.py`, then run:

```bash
python3 seal.py --reset --config config.json
python3 gen.py --config config.json --rate 2 &
sleep 6
python3 - <<'PY'
import seal, verify
cfg = seal.load_config('config.json')
r = verify.verify(cfg)
print(r['status'])
for n in r['nodes']:
    print(n['name'], n['agrees'], n['head_seq'])
PY
```

All four rows must show `seq` within one record of each other. A brief `WITNESS_AHEAD` can appear while the generator writes. Stop the generator before a manual check.

## What this proves

Three vaults now hold the same fingerprints on three machines over Tailscale: `vic` (Vault 1), `archlinux` (Vault 2), and `vic-home-server` (Vault 3). The generator, log, ledger and console still run on `archlinux`. The vaults are independent witnesses, not a copy of the console.

## What to say to judges

> Three independent vaults on three machines, linked over Tailscale. Each one keeps its own copy of every fingerprint and refuses a rewritten history.

## What not to say

- The Homepage dashboard on port `3001` is not a log source.
- No real logs are sealed. The generator makes synthetic events. The proof is real.
