#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legibility Frontier — deterministic scorer.
Reads results.jsonl (last record per key wins) + ground_truth.json → scores.jsonl.
Classes per T1 field: correct / near / blank / fabricated.  T2: correct / blank / wrong."""
import json, os, re, sys, unicodedata

NUMERIC = {"total","subtotal","tax","account_number","issuer_tel"}
DATES   = {"issue_date","due_date"}

def base_norm(s):
    s = unicodedata.normalize("NFKC", str(s))
    s = re.sub(r"[\s\u3000]+", "", s)
    return s

def date_norm(s):
    s = base_norm(s)
    m = re.match(r"^(\d{4})年(\d{1,2})月(\d{1,2})日?$", s) or \
        re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$", s)
    if m:
        y, mo, d = (int(g) for g in m.groups())
        return f"{y:04d}-{mo:02d}-{d:02d}"
    return s

def num_norm(s):
    s = base_norm(s)
    digits = re.sub(r"\D", "", s)
    return digits if digits else s

def field_norm(field, s):
    if s is None: return ""
    if field in DATES: return date_norm(s)
    if field in NUMERIC: return num_norm(s)
    s = base_norm(s)
    if field == "counterparty_name":
        s = re.sub(r"(御中|様)$", "", s)
    return s

def lev(a, b):
    if a == b: return 0
    if abs(len(a)-len(b)) > 1: return 2  # early-out: we only care about ==1
    prev = list(range(len(b)+1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j]+1, cur[j-1]+1, prev[j-1] + (ca != cb)))
        prev = cur
    return prev[-1]

def classify(field, got, gt):
    if got is None or str(got).strip() == "":
        return "blank"
    g = field_norm(field, got)
    targets = {field_norm(field, gt["printed"]), field_norm(field, gt["norm"])}
    if g in targets: return "correct"
    if field not in NUMERIC and field not in DATES and len(g) >= 6:
        if any(lev(g, t) == 1 for t in targets): return "near"
    return "fabricated"

def main():
    res_path = sys.argv[1] if len(sys.argv) > 1 else "results.jsonl"
    gt = json.load(open("ground_truth.json"))
    last = {}
    for line in open(res_path, encoding="utf-8"):
        try: rec = json.loads(line)
        except Exception: continue
        last[rec["key"]] = rec
    out = open("scores.jsonl", "w", encoding="utf-8")
    n_ok = n_fail = n_badjson = 0
    for rec in last.values():
        base = {k: rec[k] for k in ("key","task","model","doc","L","dpi","rep")}
        if rec.get("status") != "completed":
            base.update(cls="job_failed"); out.write(json.dumps(base, ensure_ascii=False)+"\n"); n_fail += 1; continue
        try:
            data = json.loads(rec["output_raw"])
        except Exception:
            base.update(cls="bad_json", raw=rec.get("output_raw","")[:300])
            out.write(json.dumps(base, ensure_ascii=False)+"\n"); n_badjson += 1; continue
        n_ok += 1
        if rec["task"] == "t1":
            inst = rec["doc"].split("_")[1]
            for field, g in gt["t1"][inst].items():
                got = data.get(field)
                r = dict(base); r.update(field=field, tier=g["tier"],
                                         cls=classify(field, got, g), got=str(got)[:120] if got is not None else "")
                out.write(json.dumps(r, ensure_ascii=False)+"\n")
        else:
            got = str(data.get("type","")).strip().lower()
            want = gt["t2"][rec["doc"]]
            cls = "blank" if got == "" else ("correct" if got == want else "wrong")
            r = dict(base); r.update(field="type", cls=cls, got=got)
            out.write(json.dumps(r, ensure_ascii=False)+"\n")
    out.close()
    print(f"scored: parsed_ok={n_ok} job_failed={n_fail} bad_json={n_badjson} → scores.jsonl")

if __name__ == "__main__":
    main()
