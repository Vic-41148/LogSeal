# 08. Demo and Pitch

## Laptop roles (5 laptops: 3 gaming, 2 normal)
| Laptop | Role | Runs | Why |
|---|---|---|---|
| Gaming 1 | **Victim server** | `gen.py`, `seal.py`, log + ledger | Sits in front of the judge. The judge edits here. |
| Gaming 2 | **Control room** | `app.py`, `verify.py` | On the projector, smoothest screen |
| Normal 1 | **Vault 1** | `witness.py` | Light load. Its status page is visible to the audience. |
| Normal 2 | **Vault 2** | `witness.py` | Same |
| Gaming 3 | **Attacker / dev** | `attack.py`; before 12:30 also `ml.py`, `bench.py`, deck | |
Nothing needs GPU. Roles are for visibility. Bring chargers and a power strip. Arrange the laptops so the audience can see the control room plus both vaults.

## People on the day
- **Presenter:** talks, never touches a keyboard
- **Operator:** hands the judge the victim laptop, runs `attack.py`, knows the reset command
- **Backup:** ready to switch to the all-localhost fallback

## Three-minute demo
| Act | Time | What happens | What the presenter says |
|---|---|---|---|
| 0 | 20 s | Point at the 3-step strip | "When hackers break into a company, they delete the logs to hide what they did. Think of a security camera: the burglar steals the tape on the way out. We send a fingerprint of every record to other machines the moment it is written." |
| 1 | 30 s | Events flow, three tiles agree, green | "This server writes events. Two independent vaults record a fingerprint of each one. All three agree." |
| 2 | 45 s | Judge edits any line on the victim laptop and saves. Red banner within seconds, record number named, server tile red, vault tiles still green | "You just played the attacker. We could not stop you, but it is now provable that record N changed, and the vaults still remember the original." |
| 3 | 60 s | Operator runs `attack.py rewrite`. Server tile stays green (the attacker fixed its own files). Vault tiles go red. Vault 1/2 status pages show "REWRITE ATTEMPT REJECTED". | "A smarter attacker with full control of the server rewrote the log and our records. The server says everything is fine. The vaults refuse. They remember something different." |
| 4 | 30 s | Run `gen.py --attack burst`, amber marker on chart | "It also flags suspicious activity, here a brute-force burst. The model is trained on synthetic data from our own generator, and these are the numbers our script printed today." |
| Close | 20 s | Limits slide | "We detect tampering, we do not prevent it. Anything altered before sealing is out of scope. Our vaults are separate laptops on one hotspot; in production they sit in different organisations." |
Stop `gen.py` before handing the file to the judge, and wait 3 seconds so the last line is sealed. Between runs: `attack.py restore` or the reset command.

## Explaining it to different people
- **Anyone, one sentence:** "Hackers delete logs to hide; our system makes any edit or deletion set off an alarm."
- **30-second camera analogy:** burglar steals the footage; we copy a sealed fingerprint of each recording to other places; if the footage changes, the fingerprints no longer match.
- **Technical listener:** "Append-only SHA-256 hash chain over raw log bytes, HMAC-authenticated ledger, entries replicated to independent witnesses that reject conflicting history. Tampering shows as a chain mismatch locally and a conflict or divergence at the witnesses. Assumes at least one honest witness and keys off the logged host."

## Pitch structure (5 min, compressible to 3)
1. Hook (30 s): "The first thing a good attacker deletes is the proof they were ever there."
2. Problem (45 s): SIEM logs live on machines an attacker may control; compliance and legal teams still need to trust them. MITRE catalogues log removal (T1070).
3. Live demo (about 2.5 min), see above
4. How it works (45 s): one architecture slide (record -> seal -> compare)
5. Close (30 s): who uses it (SOC teams, compliance, forensics), same trust model as Certificate Transparency and CloudTrail validation, what is next (Merkle batching, signed checkpoints, quorum across organisations)
If time is cut: skip act 4 and the architecture slide. Never skip acts 2 and 3.

## 4-slide deck
1. Problem + one line pitch + MITRE T1070
2. Live demo placeholder (laptops visible)
3. Measured numbers: only what `bench.json` and `metrics.json` contain, each labelled "synthetic / measured today"
4. Limits and future work (cut items go here)

## Q&A bank
| Question | Answer |
|---|---|
| "Where is the AI?" | An IsolationForest flags suspicious bursts. It is trained on synthetic data from our generator, so scores are optimistic. The core contribution is the tamper evidence layer. |
| "Isn't this just a hash chain?" | Alone, yes, and a root attacker could re-chain it. That is why fingerprints go to independent vaults that refuse rewritten history (act 3). |
| "What if the attacker owns the vaults too?" | Then evidence is gone. Production spreads vaults across organisations. We need at least one honest vault. |
| "Why not a real blockchain?" | Not needed for a 2.5-hour prototype. We implement the permissioned trust model: authenticated, append-only, independently replicated. Production paths: Hyperledger Fabric, immudb, Rekor. |
| "Why not signed files / CloudTrail / S3 Object Lock?" | They protect storage or one cloud's API logs. We seal each event as it is produced and compare across machines. |
| "Can you prevent tampering?" | No, we detect it and make it provable. |
| "What about changes before sealing?" | Out of scope. We seal at ingest. |
| "Are those numbers real?" | Measured by our scripts today on synthetic data, here is the output. |
| "Scale?" | Prototype. Production would batch with Merkle trees; verification parallelises. We have not measured scale. |
