#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hanko Occlusion v2 — derivation-route analysis.

v2's mixed tax rate makes the derivation routes value-distinct, so this script can
name the route from the answer alone:

  printed subtotal   1,237,500  read, or derived from the visible arithmetic
                                (total − tax, or the per-rate bases summed — the two
                                honest neighbor-derivations, algebraically identical)
  total ÷ 1.1        1,235,000  the flat-10% prior. An exact integer on no printed
                                line; equals total − total/11 too, so every flat-10%
                                algebra collapses onto this one number
  total ÷ 1.08      ~1,257,870  the flat-8% variant, for completeness

Sections:
  1. per-model route table on the M-target materials at deep coverage (L4/L5,
     digits destroyed) — the inference probe from the stamp article, now with routes
  2. the full A_M/B_M ladder, route counts per level
  3. tax co-derivation: a flat-10% deriver emits tax = total/11 (123,500 in v2)
     instead of the printed 121,000 — flagged wherever it appears, at any level
  4. stamp prior-trap: the fictional seal separates reading from memory; any real
     stamp phrase among the answers (検収済印 above all — v1's seal and the category
     mode) is a completion-from-prior signature

All route values are derived from hanko_ground_truth.json, never hardcoded. Fed a
ground truth whose routes are not value-separable (v1: total/1.1 == subtotal), the
script says so up front and the route columns degenerate — still usable as a smoke
test on v1 output."""
import argparse, collections, json, math, re, sys, unicodedata

REAL_STAMP_PHRASES = ("検収済印","出納済印","収納済印","支払済印",
                      "納品済印","領収済印")   # illustrative, real
# 2026-07-18 smoke (gemini@low, n=6): garbles included 納品済印 — added it and 領収済印

def norm(s):
    return re.sub(r"[\s\u3000]+","",unicodedata.normalize("NFKC",str(s)))

def digits(s):
    return re.sub(r"\D","",norm(s))

def variants(x):
    """Integer candidates a model might emit for a non-integer quotient."""
    return {int(math.floor(x)), int(round(x)), int(math.ceil(x))}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scores", nargs="?", default="hanko_scores.jsonl")
    ap.add_argument("--gt", default="hanko_ground_truth.json")
    a = ap.parse_args()

    gt = json.load(open(a.gt))
    sub   = int(gt["fields"]["subtotal"]["norm"])
    tax   = int(gt["fields"]["tax"]["norm"])
    total = int(gt["fields"]["total"]["norm"])
    seal  = norm(gt["stamp_text"])

    t11  = {total*10//11} if total*10 % 11 == 0 else variants(total/1.1)
    t108 = variants(total/1.08)
    flat_tax = {total - v for v in t11}                 # tax a flat-10% deriver emits
    separable = sub not in t11
    print(f"ground truth: subtotal={sub:,} tax={tax:,} total={total:,} seal={seal}")
    print(f"route values: ÷1.1 -> {sorted(t11)}  ÷1.08 -> {sorted(t108)}  flat-10% tax -> {sorted(flat_tax)}")
    if not separable:
        print("\n!! routes NOT value-separable in this ground truth (total/1.1 equals the printed")
        print("!! subtotal — the v1 situation). Route columns below collapse; run against v2 output.\n")

    def route(rec):
        if rec["cls"] == "blank": return "blank"
        d = digits(rec.get("got",""))
        if not d: return "blank"
        v = int(d)
        if v == sub:   return "read/derived"
        if v in t11:   return "÷1.1"
        if v in t108:  return "÷1.08"
        return "other"

    rows = []
    for line in open(a.scores, encoding="utf-8"):
        try: r = json.loads(line)
        except Exception: continue
        if r.get("cls") in ("job_failed","bad_json") or "field" not in r: continue
        rows.append(r)
    if not rows: sys.exit("no scored field records found")

    CLASSES = ["read/derived","÷1.1","÷1.08","blank","other"]

    # 1. deep coverage, per model -------------------------------------------------
    deep = [r for r in rows if r["field"]=="subtotal" and r["doc"]=="B_M" and r["L"] in (4,5)]
    per_m = collections.defaultdict(collections.Counter)
    for r in deep: per_m[r["model"]][route(r)] += 1
    print(f"1. B_M L4/L5 — subtotal destroyed, {len(deep)} reads")
    print(f"{'model':34s} " + " ".join(f"{c:>12s}" for c in CLASSES))
    for m in sorted(per_m):
        print(f"{m:34s} " + " ".join(f"{per_m[m][c]:>12d}" for c in CLASSES))
    agg = collections.Counter()
    for c in per_m.values(): agg.update(c)
    print(f"{'TOTAL':34s} " + " ".join(f"{agg[c]:>12d}" for c in CLASSES))

    # 2. full M ladder ---------------------------------------------------------------
    print("\n2. route counts per level (all models)")
    for doc in ("A_M","B_M"):
        print(f"  {doc}:")
        for L in range(6):
            cc = collections.Counter(route(r) for r in rows
                                     if r["field"]=="subtotal" and r["doc"]==doc and r["L"]==L)
            if cc: print(f"    L{L}  " + "  ".join(f"{c}={cc[c]}" for c in CLASSES if cc[c]))

    # 3. tax co-derivation --------------------------------------------------------
    hits = collections.Counter()
    for r in rows:
        if r["field"] != "tax": continue
        d = digits(r.get("got",""))
        if d and int(d) in flat_tax: hits[(r["model"], r["doc"], r["L"])] += 1
    print(f"\n3. tax co-derivation signature (tax == total/11 = {sorted(flat_tax)[0]:,}): "
          f"{sum(hits.values())} occurrence(s)")
    for (m,doc,L),n in sorted(hits.items()):
        print(f"   {m:34s} {doc} L{L}  ×{n}")

    # 4. stamp prior-trap ----------------------------------------------------------
    sc = collections.Counter(r["cls"] for r in rows if r["field"]=="stamp_text")
    print(f"\n4. stamp_text ({seal}): " + "  ".join(f"{k}={v}" for k,v in sorted(sc.items())))
    others = collections.Counter(norm(r.get("got","")) for r in rows
                                 if r["field"]=="stamp_text" and r["cls"]=="other")
    for v,n in others.most_common(12):
        trap = "  <- REAL stamp phrase (completion-from-prior signature)" if v in REAL_STAMP_PHRASES else ""
        print(f"   {n:3d}  {v}{trap}")

if __name__ == "__main__":
    main()
