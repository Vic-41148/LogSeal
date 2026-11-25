# P1: core lane

You own `seal.py` and `verify.py`. You own the proof that tampering is visible.

Detailed reference: `docs/04_TASK_seal_verify.md` and the contract `docs/03_CONTRACT.md`.

## Start now

```
./scripts/bootstrap.sh
make test
make selftest
make demo NAME=p1
```

Read the mutation tests in `tests/test_verify_mutations.py`. They are the specification.

## Do these in order

1. **Confirm the mutation table.** Run `make test -v`. Every row must pass:
   edit, whitespace edit, delete, insert, truncate, swap, forged ledger, root rewrite, consistent wipe, pending, unsealed, live appends.
2. **Check the 1,000-event budget.** The test must stay under 1 second on the demo laptop. Record the measured number in your report.
3. **Read the console fields.** `verify()` must fill `detail`, `expected`, `actual` and `confirmed_by` so P3 can show the alarm without extra logic.
4. **Check the write order.** In `seal.append()`, the log line is written and fsynced before the ledger entry. Do not change this order. The verifier depends on it.
5. **Harden one weak spot** only if all tests pass. Examples: clearer `detail` text, a test for a two-line edit, a test for an empty log. Do not add features.

## Done when

- `make ci` passes.
- An edit of any line shows `EDIT`, the correct record number, and both vault names in `confirmed_by`.
- A root rewrite shows `WITNESS_CONFLICT` at the first changed record, with the server tile green and the vault tiles red.
- You can explain the chain in one sentence: content hash, chain hash, HMAC, independent head comparison.

## Do not touch

`witness.py`, `app.py`, `gen.py`, `attack.py`, `ml.py`, `bench.py`, the config files, the contract.

If a test seems wrong, tell the lead. Do not edit a shared test to make your code pass.
