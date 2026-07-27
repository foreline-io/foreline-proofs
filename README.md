# Foreline — public forecast commitments

This repository contains **cryptographic commitments** to Foreline's live
price-movement forecasts (Pinnacle universe, football & basketball).
No forecasts, signals or odds are published here — only hashes.

## What is committed
- `roots.jsonl` — one record per day: tip hashes of the append-only forecast
  and settlement ledgers (each ledger record contains the hash of the
  previous one; days are chained together).
- `commits.jsonl` — intra-day Merkle commitments (~every 30 min): the root
  of a Merkle tree over the row-hashes of ALL forecasts issued since the
  previous commitment. Selective disclosure is impossible: a forecast is
  either under a published root or it does not exist.
- `root_YYYYMMDD.json` + `.ots` — daily root manifests and their
  OpenTimestamps proofs (anchored in Bitcoin).

## How to verify
Run the bundled verifier (stdlib Python, no NDA required):

```bash
python3 verify.py
```

It checks that (1) every daily manifest's root recomputes from its tip
hashes, (2) the intra-day Merkle commit chain is intact from genesis —
selective rewriting is impossible without breaking it, and (3) every
`.ots` stamp verifies against Bitcoin (if `opentimestamps-client` is
installed; otherwise it prints the manual commands).

Additional paths:
1. `ots verify root_YYYYMMDD.json.ots` — proves the daily root existed at
   the stamped time (requires opentimestamps-client).
2. Under NDA, clients receive the full ledger; every record re-hashes into
   the published chain and Merkle roots.
3. Spot-checks: for any single forecast we produce the record plus its
   Merkle path to a published root — verify offline with
   `python3 verify.py --spot record.json`, without seeing anything else.

Contact: contact@foreline.io
