# 10. Setup, Network, Reset

## Folder layout (single git repo or shared folder)
```
logseal/
  config.json  config.local.json
  gen.py  seal.py  verify.py  witness.py  attack.py  ml.py  bench.py  app.py
  (runtime) app.log.jsonl  ledger.jsonl  witness_*.jsonl  metrics.json  bench.json  model.joblib
```
Eight code files. Each person edits only their own files, so merge conflicts should be rare. Share code over the hotspot with git, or use a USB stick as backup.

## Install (every laptop, 09:00-09:15)
```
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install streamlit scikit-learn joblib
```
Core files need nothing. Vault laptops need Python only.

## Run order
1. Vaults (on their laptops): `python witness.py --name "Vault 1" --port 8101 --allow-reset`
2. Server laptop: `export LOGSEAL_KEY=...` (same value everywhere that seals or attacks), then `python gen.py --rate 2`
3. Control room: `streamlit run app.py --server.port 8501`
4. Attacker laptop: `python attack.py ...` when told

## Network checklist
- One laptop's phone hotspot, not venue Wi-Fi (often isolates clients)
- Each vault laptop: note its IP, put it in `config.json`
- From the server laptop and control room: `curl http://<vault-ip>:8101/head` must answer
- Windows firewall: allow inbound TCP 8101 on vault laptops
- If Streamlit port 8501 is busy: `--server.port 8502`

## Fallback (rehearse once)
`--config config.local.json` on every tool, vaults started on `--port 8101` and `--port 8102` on the server laptop. Same code, no rewrite. Judges will still see two vault status pages in browser tabs.

## Reset between runs (under 30 seconds)
1. Stop `gen.py` (Ctrl+C)
2. `python attack.py restore` if an attack was run, otherwise `python -c "import seal; c=seal.load_config(); seal.reset(c)"`
3. Make sure vaults were started with `--allow-reset` (reset clears them too)
4. Restart `gen.py`, check the console is green
Test the reset three times before the pitch.

## Insurance
- Phone recording of one clean run, made during the break
- Printed architecture sheet (record -> seal -> compare), 3 copies
- Power bank, HDMI adapter, power strip
- Sleep. Pitches are won by rested brains.
