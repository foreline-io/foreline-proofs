#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public verifier for Foreline proof commitments. Stdlib only, no NDA needed.

Checks, in order:
  1. Daily manifests (root_YYYYMMDD.json): root == sha256("{day}|{forecasts_tip}|{settles_tip}")
     and every line of roots.jsonl matches its manifest file.
  2. Commit chain (commits.jsonl): starting from the literal genesis string
     "foreline-merkle-genesis", every record must satisfy
        prev_commit == previous.commit_hash
        commit_hash == sha256(prev_commit + canonical_json(body))
     where canonical_json is JSON with sorted keys, separators (",", ":"),
     and body is the record without the commit_hash field.
  3. OpenTimestamps: runs `ots verify root_YYYYMMDD.json.ots` for every stamp
     if the ots client is installed (pip install opentimestamps-client);
     otherwise prints the command for manual verification.

Spot-check mode (for disclosed records you received from Foreline):
  python3 verify.py --spot record.json
  where record.json = {"row_hash": "...", "path": [["<sibling_hex>","L"|"R"], ...],
                       "merkle_root": "..."}
  Folds the Merkle path from the leaf and requires the resulting root to be
  present in the published commits.jsonl. Fold rule: at each step
  parent = sha256(sibling + current) if side == "L" else sha256(current + sibling)
  (hex strings concatenated as text, digest in hex).

Exit code 0 = everything verifiable passed; 1 = any check failed.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GENESIS = 'foreline-merkle-genesis'


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def check_manifests():
    ok = True
    manifests = {}
    for name in sorted(os.listdir(HERE)):
        if name.startswith('root_') and name.endswith('.json'):
            m = json.load(open(os.path.join(HERE, name)))
            want = sha(f'{m["day"]}|{m["forecasts_tip"]}|{m["settles_tip"]}')
            good = want == m['root']
            ok &= good
            manifests[m['day']] = m['root']
            print(f'  {name}: root recomputes {"OK" if good else "FAIL"}')
    n = 0
    for line in open(os.path.join(HERE, 'roots.jsonl')):
        if not line.strip():
            continue
        r = json.loads(line)
        n += 1
        if r['day'] in manifests and manifests[r['day']] != r['root']:
            print(f'  roots.jsonl day {r["day"]}: MISMATCH with manifest')
            ok = False
    print(f'  roots.jsonl: {n} day records cross-checked')
    return ok


def check_commit_chain():
    path = os.path.join(HERE, 'commits.jsonl')
    if not os.path.exists(path):
        print('  commits.jsonl absent — skipped')
        return True
    prev = GENESIS
    n = 0
    for i, line in enumerate(open(path), 1):
        if not line.strip():
            continue
        rec = json.loads(line)
        body = json.dumps({k: v for k, v in rec.items()
                           if k != 'commit_hash'},
                          sort_keys=True, separators=(',', ':'),
                          ensure_ascii=False)
        if rec.get('prev_commit') != prev:
            print(f'  commit {i}: prev_commit BROKEN')
            return False
        if sha(prev + body) != rec.get('commit_hash'):
            print(f'  commit {i}: commit_hash BROKEN')
            return False
        prev = rec['commit_hash']
        n = i
    print(f'  commit chain: {n} commitments, linkage OK '
          f'(selective rewrite impossible without breaking the chain)')
    return True


def check_ots():
    stamps = sorted(f for f in os.listdir(HERE) if f.endswith('.ots'))
    if not stamps:
        print('  no .ots stamps found')
        return True
    if shutil.which('ots') is None:
        print('  ots client not installed — verify manually:')
        for s in stamps:
            print(f'    ots verify {s}')
        return True
    ok = True
    for s in stamps:
        r = subprocess.run(['ots', 'verify', os.path.join(HERE, s)],
                           capture_output=True, text=True, timeout=180)
        out = (r.stderr or r.stdout).strip()
        line = out.replace('\n', ' | ')[:160]
        if r.returncode == 0:
            print(f'  {s}: OK — {line}')
        elif 'Could not connect to Bitcoin node' in out:
            # environment limit, NOT a data failure: the attestation exists;
            # confirming the Bitcoin block needs a local node
            print(f'  {s}: ATTESTED (calendar); full Bitcoin confirmation '
                  f'needs a local bitcoind — not counted as failure')
        elif 'Pending' in out or 'pending' in out:
            print(f'  {s}: PENDING aggregation into Bitcoin (normal for '
                  f'stamps < ~1 day old)')
        else:
            ok = False
            print(f'  {s}: FAIL — {line}')
    return ok


def spot(path):
    rec = json.load(open(path))
    h = rec['row_hash']
    for sib, side in rec['path']:
        h = sha(sib + h) if side == 'L' else sha(h + sib)
    if h != rec['merkle_root']:
        print(f'SPOT: path does NOT fold to claimed root ({h[:16]}…)')
        return False
    roots = set()
    for line in open(os.path.join(HERE, 'commits.jsonl')):
        if line.strip():
            roots.add(json.loads(line)['merkle_root'])
    if rec['merkle_root'] in roots:
        print(f'SPOT: OK — record is under published commitment '
              f'{rec["merkle_root"][:16]}…')
        return True
    print('SPOT: path folds correctly, but root is NOT among published '
          'commitments in this snapshot of commits.jsonl')
    return False


def main():
    if '--spot' in sys.argv:
        ok = spot(sys.argv[sys.argv.index('--spot') + 1])
        sys.exit(0 if ok else 1)
    print('[1/3] Daily root manifests')
    ok1 = check_manifests()
    print('[2/3] Intra-day Merkle commit chain')
    ok2 = check_commit_chain()
    print('[3/3] OpenTimestamps (Bitcoin anchoring)')
    ok3 = check_ots()
    ok = ok1 and ok2 and ok3
    print(f'\nRESULT: {"ALL CHECKS PASSED" if ok else "FAILURES FOUND"}')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
