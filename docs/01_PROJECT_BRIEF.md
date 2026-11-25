# 01. Project Brief

## Event facts (from the event site)
- Tech Fusion 4.0, CodeStorm day = 25 Nov, 09:00-16:00. Entry Rs 500/team. Total prize pool Rs 30,000 across coding and gaming arenas (split unpublished).
- Schedule: 09:00 check-in, 10:00 coding starts, 12:30-13:00 break, 13:00-15:00 pitching round, 15:30 results.
- Theme: **Artificial Intelligence** (4 tracks, 8 briefs). Judges: academic panel (Dean DSW, two SOET assistant professors). Rubric is not public; the only stated criteria (PS-04A) are problem clarity, technical depth of the AI, real-world viability, live demo execution. Treat those as the house rubric.
- Rules for team size, pre-built code, pitch length and AI-assistant use are **not published**. The human asks the Technical Head at 09:00.

## Chosen problem: PS-03B Tamper-Proof Security Audit & SIEM Logging
Official text: *Build a decentralized, append-only log integrity verifier that hashes critical system events onto a permissioned ledger in real time. Any unauthorized modification to local logs triggers an immediate cryptographic mismatch alert.*

Deliverables the brief asks for:
1. Real-time SIEM event hashing and permissioned-ledger anchoring
2. Instant cryptographic mismatch and tamper alerting
3. Forensic verification console proving log immutability

Because the event theme is AI, we add one small, honest ML feature: an IsolationForest flagging suspicious bursts (for example brute-force logins). It is secondary. The tamper demo is the main story.

## Pitch in one line
"Attackers delete logs to hide. LogSeal makes the deletion itself the evidence."

## Real-world use
Incident response (prove which entries were wiped), compliance audits (PCI DSS, HIPAA, SOX, ISO 27001 expect protected audit logs; India's CERT-In directive requires log retention, verify exact terms before quoting), insider-threat resistance, legal/forensic evidence, multi-party trust. The same trust model already exists in production in Certificate Transparency, Sigstore Rekor, AWS CloudTrail log-file validation and immudb.

## What this is NOT
- Not a blockchain. Not a SIEM replacement.
- Detects tampering, does not prevent it.
- Cannot protect events altered or suppressed before they were sealed.
- Vaults in the demo are separate laptops on one hotspot. In production they would sit in different organisations with keys off the logged host.

## Constraints
- Build window about 150 minutes. Target: working demo by about 11:40, the rest is debugging, deck, rehearsal.
- Venue network is hostile. Everything must also run on one laptop via localhost.
- 5 laptops (3 gaming, 2 normal). Nothing here needs GPU. Roles are chosen for visibility, see `08_DEMO_AND_PITCH.md`.
