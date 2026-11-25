# P2: vault lane

You own `witness.py`. You own the independent memory that catches a root attacker.

Detailed reference: `docs/05_TASK_witness.md` and the contract `docs/03_CONTRACT.md`.

## Start now

```
./scripts/bootstrap.sh
make test
make demo NAME=p2
```

The stack starts two vaults. Open both status pages. They refresh every 2 seconds.

## Do these in order

1. **Confirm the HTTP contract.** `make test` runs `tests/test_witness_api.py`. It covers `/head`, `/entry/{seq}`, `/append`, duplicate, conflict, gap, reset flag and restart.
2. **Check the status page.** Open a vault URL from 3 metres. The name, record count and first 8 hash characters must be readable. A conflict must show the red strip `REWRITE ATTEMPT REJECTED`.
3. **Run the conflict scene.** In your stack, seal about 60 events. Then run the rewrite from P4 when it is ready. Confirm both vaults answer `409` and both pages stay red after a restart.
4. **Test a dead vault.** Stop one vault. The console tile must go grey. The other vault must still agree.
5. **Write the real IPs.** After the network check, put the two vault laptop IPs in `config.json`. Use a fixed IP or a hotspot reservation. Tell the team the values.
6. **Open the firewall.** On each vault laptop, allow inbound TCP 8101. Run `curl http://<vault-ip>:8101/head` from the server laptop.

## Done when

- `make ci` passes.
- A rewrite attempt gets `409` from both vaults and leaves a visible conflict row.
- A vault restart keeps entries and conflict history.
- Both pages are readable from 3 metres.
- `config.json` holds the real IPs, and the server laptop can reach both.

## Do not touch

`seal.py`, `verify.py`, `app.py`, P4 files, the contract.
