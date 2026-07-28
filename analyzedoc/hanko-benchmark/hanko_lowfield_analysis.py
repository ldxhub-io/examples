#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hanko Occlusion — L0 per-field analysis (the script behind the @low write-up).

Reads hanko_scores.jsonl and rebuilds, from the L0 (zero-occlusion) slice only:

  1. the per-field table: each @low variant × each field, hits out of 20
     (4 instances × 5 reps; hit = correct or near, same rule as hanko_report.py)
  2. the gate statistic: how many model×field cells are exactly 0 or exactly 20
     (document fields only — stamp_text excluded)
  3. what fills the unread fields for the new-generation @low variants:
     blank vs. invented counts, and the top invented values per field
  4. the bank-branch co-occurrence check: "correct" branch cells whose sibling
     bank_name in the same response is fabricated (inventions colliding with truth)
  5. the old-generation blank-to-invention ratio, for the closing comparison

Field names and the field display order are derived from the data, not assumed.
Generation membership is pattern-based so the same script serves future runs:
  --newgen  regex for the confident-author generation   (default: 5\\.5|5\\.6)
  --oldgen  regex for the older generation              (default: 5\\.4)

--check-v1 asserts every number the July 2026 article states, against the
2026-07-12 run's scored output. A clean PASS is the acceptance test."""
import argparse, collections, json, re, sys, unicodedata

ORDER = ["doc_title","invoice_no","issue_date","due_date","counterparty_name",
         "issuer_name","issuer_tel","total","subtotal","tax",
         "bank_name","bank_branch","account_number","stamp_text"]
READ4 = {"doc_title","total","subtotal","tax"}          # what the new gen reads
V1_ROWSUMS = [150,144,80,84,79,260,81,78,81,76]         # sorted @low rows, 2026-07-12 run

def norm(s):
    return re.sub(r"[\s\u3000]+","",unicodedata.normalize("NFKC",str(s)))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scores", nargs="?", default="hanko_scores.jsonl")
    ap.add_argument("--newgen", default=r"5\.5|5\.6")
    ap.add_argument("--oldgen", default=r"5\.4")
    ap.add_argument("--check-v1", action="store_true",
                    help="assert the 2026-07 article numbers (acceptance test)")
    a = ap.parse_args()
    NEW = re.compile(a.newgen); OLD = re.compile(a.oldgen)

    rows = []
    for line in open(a.scores, encoding="utf-8"):
        try: r = json.loads(line)
        except Exception: continue
        if r.get("cls") in ("job_failed","bad_json") or "field" not in r: continue
        if r.get("L") != 0: continue
        rows.append(r)
    if not rows: sys.exit("no L0 field records found")

    FIELDS = sorted({r["field"] for r in rows})
    order  = [f for f in ORDER if f in FIELDS] + [f for f in FIELDS if f not in ORDER]
    docf   = [f for f in order if f != "stamp_text"]
    lows   = sorted({r["model"] for r in rows if "@low" in r["model"]})
    newgen = [m for m in lows if NEW.search(m)]
    oldgen = [m for m in lows if OLD.search(m)]

    hits = collections.defaultdict(lambda: [0,0])       # (model,field) -> [hit,n]
    for r in rows:
        k = (r["model"], r["field"])
        hits[k][0] += 1 if r["cls"] in ("correct","near") else 0
        hits[k][1] += 1

    # 1. per-field table --------------------------------------------------------
    print(f"{'model':32s} " + " ".join(f"{f[:7]:>7s}" for f in order) + "   (hits /20)")
    rowsums = []
    for m in lows:
        cells = [hits[(m,f)][0] if (m,f) in hits else 0 for f in order]
        rowsums.append(sum(cells))
        print(f"{m:32s} " + " ".join(f"{c:>7d}" for c in cells))
        for f in order:
            if (m,f) in hits and hits[(m,f)][1] != 20:
                print(f"  !! {m}/{f}: n={hits[(m,f)][1]} (expected 20 — partial data?)")
    print("row sums:", rowsums)

    # 2. gates ------------------------------------------------------------------
    cells13 = [hits[(m,f)][0] for m in lows for f in docf]
    gates = sum(1 for c in cells13 if c in (0,20))
    print(f"\ngates: {gates} of {len(cells13)} document-field cells are exactly 0 or exactly 20")

    # 3. what fills the unread fields (new generation) --------------------------
    unread = [f for f in docf if f not in READ4 and f != "bank_branch"]
    cls_ct = collections.Counter(); inv = collections.defaultdict(collections.Counter)
    n_reads = 0
    for r in rows:
        if r["model"] in newgen and r["field"] in unread:
            n_reads += 1; cls_ct[r["cls"]] += 1
            if r["cls"] == "fabricated": inv[r["field"]][norm(r.get("got",""))] += 1
    blank, fab = cls_ct["blank"], cls_ct["fabricated"]
    hitc = cls_ct["correct"] + cls_ct["near"]
    print(f"\nnew-gen ({len(newgen)} models) × {len(unread)} unread fields × 20 = {n_reads} reads:")
    print(f"  blank {blank} / invented {fab} / correct-or-near {hitc}"
          f"  (invention rate {fab/n_reads:.0%})")
    for f in unread:
        top = inv[f].most_common(3)
        if top: print(f"  {f:18s} " + "  ".join(f"{v}×{c}" for v,c in top))

    bank_fab   = sum(inv["bank_name"].values())
    megabank   = sum(c for v,c in inv["bank_name"].items()
                     if any(b in v for b in ("みずほ","三井住友","三菱UFJ")))
    acct_1234  = sum(1 for r in rows if r["model"] in newgen and r["field"]=="account_number"
                     and "1234567" in re.sub(r"\D","",str(r.get("got",""))))
    dates_fab  = sum(inv[f].total() if hasattr(inv[f],'total') else sum(inv[f].values())
                     for f in ("issue_date","due_date"))
    dates_2025 = sum(c for f in ("issue_date","due_date") for v,c in inv[f].items() if "2025" in v)
    print(f"\n  bank_name: {megabank} of {bank_fab} inventions are megabanks")
    print(f"  account_number: literal 1234567 in {acct_1234} of {len(newgen)*20} reads")
    print(f"  dates: {dates_2025} of {dates_fab} inventions say 2025")

    # 4. branch co-occurrence ----------------------------------------------------
    by_key = collections.defaultdict(dict)
    for r in rows:
        if r["model"] in newgen and r["field"] in ("bank_name","bank_branch"):
            by_key[r["key"]][r["field"]] = r
    hits6 = [(k,v) for k,v in by_key.items()
             if v.get("bank_branch",{}).get("cls") == "correct"]
    co_fab = [(k,v) for k,v in hits6 if v.get("bank_name",{}).get("cls") == "fabricated"]
    print(f"\nbank_branch 'correct' cells (new gen): {len(hits6)}, "
          f"with fabricated bank_name in the same response: {len(co_fab)}")
    for k,v in sorted(hits6):
        bn = v.get("bank_name",{})
        print(f"  {k:34s} bank_name={bn.get('cls','?')}: {bn.get('got','')}")

    # 5. old-gen ratio — same field set as the new-gen tally (unread), so the two
    #    dispositions are compared over the same denominator. 2026-07-18: the article's
    #    original "1.75" was not constructible from any field subset of the L0 data;
    #    the verified symmetric value is 137/52 = 2.63 and the article was corrected.
    oc = collections.Counter(r["cls"] for r in rows
                             if r["model"] in oldgen and r["field"] in unread)
    old_ratio = (oc["fabricated"]/oc["blank"]) if oc["blank"] else float("inf")
    new_ratio = fab/blank if blank else float("inf")
    print(f"\nblank ratio — old gen: 1 blank per {old_ratio:.2f} inventions"
          f" / new gen: 1 per {new_ratio:.2f}")

    # acceptance ------------------------------------------------------------------
    if a.check_v1:
        assert len(lows) == 10 and len(newgen) == 7 and len(oldgen) == 2, (lows,newgen,oldgen)
        assert rowsums == V1_ROWSUMS, rowsums
        assert (gates, len(cells13)) == (113, 130), (gates, len(cells13))
        assert (n_reads, blank, fab, hitc) == (1120, 181, 938, 1), (n_reads, blank, fab, hitc)
        assert (megabank, bank_fab) == (98, 101), (megabank, bank_fab)
        assert acct_1234 == 88, acct_1234
        assert (dates_2025, dates_fab) == (231, 250), (dates_2025, dates_fab)
        assert len(hits6) == 6 and len(co_fab) == 6, (len(hits6), len(co_fab))
        assert (oc["blank"], oc["fabricated"]) == (52, 137), dict(oc)
        assert 5.1 <= new_ratio <= 5.3, new_ratio
        print("\nCHECK-V1: PASS — all article numbers reproduced")

if __name__ == "__main__":
    main()
