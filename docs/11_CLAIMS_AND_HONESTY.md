# 11. Claims and Honesty (what may be said to judges)

An academic panel will cross-question. Overclaiming costs more than any missing feature.

## Safe to say
- Attackers delete logs to hide: MITRE ATT&CK T1070 Indicator Removal covers this, with the Ivanti "Cutting Edge" campaign as an example (page opened and checked during research).
- AWS CloudTrail log-file integrity validation uses SHA-256 and signed, chained digest files (page opened and checked).
- The trust model (hash chain + independent witnesses) mirrors Certificate Transparency, Sigstore Rekor, CloudTrail validation and immudb (well known; cite generally, do not quote specifics you have not opened).
- Our own numbers, **if printed by our scripts that day**: "N mutations of a copy of the log, M detected, median X ms", "precision/recall/F1 on a synthetic holdout".

## Check the source yourself before putting on a slide
MITRE sub-technique ID T1685.006 and similar new IDs, AWS QLDB shutdown date (31 Jul 2025), Splunk downtime figures ($400B, $600B), PCI DSS 10.3.4 exact wording, CERT-In 180-day log retention wording, market-size figures, any library version number. These came from search snippets in the research chat and were not opened or confirmed.

## Targets are not results
The earlier research documents listed benchmark targets (5,000 events/s, p95 <= 2 s, F1 >= 0.87, ECE <= 0.05, 100% over 1,000 mutations, about 200 B/event, <1 ms verify, <= 8-hash proofs). **Nothing was measured.** None of these may appear on a slide. Show only `bench.json` and `metrics.json` contents.

## Wording rules
- Say: "authenticated append-only ledger with independent witnesses, a prototype of the permissioned model". Never "blockchain".
- Say: "synthetic data, our generator, our features, measured today".
- Say the limits yourselves: detects not prevents; nothing before sealing; vaults here are laptops on one hotspot; needs at least one honest vault.
- Do not claim real-time at scale, production readiness, or compliance certification.
- If AI coding assistants built parts of the code, say so if asked, and confirm with the organisers at 09:00 that this is allowed.
