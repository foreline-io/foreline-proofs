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
1. `ots verify root_YYYYMMDD.json.ots` — proves the daily root existed at
   the stamped time (requires opentimestamps-client).
2. Under NDA, clients receive the full ledger; every record re-hashes into
   the published chain and Merkle roots (verifier script included there).
3. Spot-checks: for any single forecast we can produce the record plus its
   Merkle path to a published root — verifiable without seeing anything else.

Contact: (to be added)
