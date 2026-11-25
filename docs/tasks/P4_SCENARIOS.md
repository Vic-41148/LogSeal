# P4: scenarios lane

You own `gen.py`, `attack.py`, `ml.py` and `bench.py`. You own the event stream, the attacker act and the measured numbers.

Detailed reference: `docs/07_TASK_gen_attack_ml_bench.md` and the contract `docs/03_CONTRACT.md`.

## Start now

```
./scripts/bootstrap.sh
make demo NAME=p4
```

The stack starts the generator at 2 events per second. Check that the record count rises on both vault pages.

## Do these in order

1. **Generator.** `make demo NAME=p4` must produce contract events. Stop it with `make down NAME=p4`. Start it again with `make stack NAME=p4` plus `python gen.py --config .run/p4/config.json --rate 2`.
2. **Burst scene.** Run `python gen.py --config .run/p4/config.json --attack burst`. About 40 failed logins from one external IP, then one success. All events must be sealed.
3. **Attacker act.** With the stack running:
   - `python attack.py rewrite --config .run/p4/config.json --seq 20`
   - The local verifier must say `OK`. Both vaults must reject the push.
   - Then `python attack.py restore --config .run/p4/config.json`.
   - Then try `wipe --keep 30`. The server must look clean. The vaults must report `WITNESS_AHEAD`.
4. **Dataset and model.** Run `make dataset`, `make train`, `make eval`. Read the printed precision, recall and F1. Quote only those numbers. They come from synthetic data.
5. **Benchmark.** Run `make bench`. It works on a copy of the files. Read the mutation count, detected count and median latency. Quote only those numbers.
6. **Toast the numbers.** Put the exact script output in the team chat. Never type a number by hand.

## Done when

- `make ci` passes.
- The generator output parses and carries all contract fields.
- Rewrite leaves the server green and the vaults red. Restore returns to green.
- Wipe leaves the server green and the vaults ahead.
- `metrics.json` and `bench.json` exist and contain only measured values.

## Do not touch

`seal.py`, `verify.py`, `witness.py`, `app.py`, the contract.
