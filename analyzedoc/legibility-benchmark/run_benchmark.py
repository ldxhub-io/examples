#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legibility Frontier — benchmark runner (resume-safe).

Usage:
  export LDXHUB_API_KEY=...
  python3 run_benchmark.py --dry-run                 # enumerate jobs only (no API calls)
  python3 run_benchmark.py --models pilot --yes      # P3 pilot (3 models)
  python3 run_benchmark.py --models all --yes        # full matrix (松)
  python3 run_benchmark.py --models ume --yes        # free-tier reproduction subset

Design: docs/legibility-benchmark-design.md v1.1.
The extraction prompt is deliberately neutral about unreadable text — whether a model
guesses (fabricates) or leaves a field empty is the measurand, so we must not instruct
either behavior.
"""
import argparse, json, os, random, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = os.environ.get("LDXHUB_BASE_URL", "https://gw.ldxhub.io")
LADDER = [300, 150, 100, 70, 50, 35, 25]           # L0..L6
T1_INSTANCES = ["A", "B"]
T2_DOCS = {"t2_invoice": "invoice", "t2_receipt": "receipt",
           "t2_card": "business_card", "t2_minutes": "meeting_minutes"}
UPLOAD_TTL_H = 24

MODELS = [  # canonical order (provider-grouped), AnalyzeDoc catalog 2026-11-07 (retired variants removed; see README),
 "openai/gpt-6.1-sol@high","openai/gpt-6.1-sol@low",
 "openai/gpt-6.1-terra@high","openai/gpt-6.1-terra@low",
 "openai/gpt-6-astra@high","openai/gpt-6-astra@low",
 "openai/gpt-6-luna@high","openai/gpt-6-luna@low",
 "azure/gpt-6.1-sol@high","azure/gpt-6.1-sol@low",
 "azure/gpt-6.1-terra@high","azure/gpt-6.1-terra@low",
 "azure/gpt-6-astra@high","azure/gpt-6-astra@low",
 "azure/gpt-6-luna@high","azure/gpt-6-luna@low",
 "google/gemini-4-carbon@high","google/gemini-4-carbon@medium","google/gemini-4-carbon@low",
 "google/gemini-4-argon@high","google/gemini-4-argon@medium","google/gemini-4-argon@low",
 "google/gemini-4-hydrogen@high","google/gemini-4-hydrogen@medium","google/gemini-4-hydrogen@low",
 "google/gemini-3.8-flash@high","google/gemini-3.8-flash@medium","google/gemini-3.8-flash@low",
 "google/gemini-3.5-flash-lite@high","google/gemini-3.5-flash-lite@medium","google/gemini-3.5-flash-lite@low",
 "anthropic/claude-opus-5-5","anthropic/claude-sonnet-5-5","anthropic/claude-haiku-5-5",
 "anthropic/claude-fable-5-2",
 "anthropic/claude-fable-5-1",
 "bedrock/global.amazon.nova-2-lite-v1:0",
]
# Cost: AnalyzeDoc is billed by the AI model's input and output tokens (since 2026-11-06). The runner keeps
# no rate table and prints no estimate; each completed job's `usage` (input_tokens / output_tokens) is saved
# to the results file. Rates: https://gw.portal.ldxhub.io/credits-and-pricing
PILOT = ["google/gemini-3.8-flash@high","openai/gpt-6.1-terra@low","anthropic/claude-fable-5-1"]  # 2026-11-07: successors of the retired 3.5 Flash, GPT-5.5 and Fable 5
UME   = ["google/gemini-3.8-flash@high","openai/gpt-6.1-terra@low","azure/gpt-6-luna@low"]  # 2026-11-07: successors of the retired 3.5 Flash, GPT-5.5 and Azure GPT-5.4 mini

T1_PROMPT = (
 "Extract the following 12 fields from this Japanese invoice, exactly as printed in the "
 "document (keep the original formatting, including commas and currency symbols). "
 "All values are strings. Use an empty string for a field that is not present in the document.\n"
 "- doc_title: the document heading\n"
 "- total: the tax-included total amount shown in the amount box\n"
 "- invoice_no: the invoice number\n"
 "- counterparty_name: the addressee company name (without honorifics such as 御中)\n"
 "- issue_date / due_date: as printed\n"
 "- subtotal / tax: from the totals section\n"
 "- bank_name / bank_branch / account_number: from the bank transfer section\n"
 "- issuer_tel: the issuer's telephone number"
)
T1_EXAMPLE = {"doc_title":"","total":"","invoice_no":"","counterparty_name":"","issue_date":"",
              "due_date":"","subtotal":"","tax":"","bank_name":"","bank_branch":"","account_number":"","issuer_tel":""}
T2_PROMPT = ("Classify this document. Answer with exactly one of: "
             "invoice, receipt, business_card, meeting_minutes.")
T2_EXAMPLE = {"type":""}

_lock = threading.Lock()

def api(method, path, key, retries=6, **kw):
    """HTTP with 429/5xx backoff. Honors Retry-After; exponential + jitter otherwise.
    Gateway policy note: the files API is limited to ~100 req/min per key — backoff,
    don't hammer."""
    import random, requests
    headers = kw.pop("headers", {}); headers["Authorization"] = f"Bearer {key}"
    for attempt in range(retries + 1):
        r = requests.request(method, BASE_URL + path, headers=headers, timeout=90, **kw)
        if r.status_code == 429 or r.status_code >= 500:
            if attempt == retries:
                r.raise_for_status()
            ra = r.headers.get("Retry-After", "")
            delay = float(ra) if ra.replace(".", "", 1).isdigit() else min(60, 2 ** attempt)
            time.sleep(delay + random.uniform(0, 1.5))
            continue
        r.raise_for_status()
        return r

def upload_all(files, key, cache_path="uploads.json"):
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    now = time.time(); changed = False
    for path in files:
        e = cache.get(path)
        if e and now - e["uploaded_at"] < UPLOAD_TTL_H * 3600:
            continue
        data = open(path, "rb").read()  # bytes, so retries re-send the full body
        r = api("POST", "/files", key, files={"file": (os.path.basename(path), data, "image/png")})
        cache[path] = {"file_id": r.json()["file_id"], "uploaded_at": now}; changed = True
        print(f"  uploaded {os.path.basename(path)}")
    if changed: json.dump(cache, open(cache_path, "w"), indent=1)
    return {p: cache[p]["file_id"] for p in files}

def enumerate_jobs(models, t1_reps, t2_reps, mat_dir, t1_instances=T1_INSTANCES):
    jobs = []
    for m in models:
        for li, dpi in enumerate(LADDER):
            for inst in t1_instances:
                for rep in range(t1_reps):
                    jobs.append(dict(key=f"t1|{m}|t1_{inst}|L{li}|r{rep}", task="t1", model=m,
                                     doc=f"t1_{inst}", L=li, dpi=dpi, rep=rep,
                                     path=f"{mat_dir}/t1_{inst}_L{li}_{dpi}dpi.png",
                                     prompt=T1_PROMPT, example=T1_EXAMPLE))
            for doc in T2_DOCS:
                for rep in range(t2_reps):
                    jobs.append(dict(key=f"t2|{m}|{doc}|L{li}|r{rep}", task="t2", model=m,
                                     doc=doc, L=li, dpi=dpi, rep=rep,
                                     path=f"{mat_dir}/{doc}_L{li}_{dpi}dpi.png",
                                     prompt=T2_PROMPT, example=T2_EXAMPLE))
    return jobs

def done_keys(out_path):
    done = set()
    if os.path.exists(out_path):
        for line in open(out_path, encoding="utf-8"):
            try: rec = json.loads(line)
            except Exception: continue
            if rec.get("status") == "completed": done.add(rec["key"])
    return done

# Optional client-side cap on concurrent jobs per provider, e.g. {"anthropic": 2}.
# Normally unnecessary: the gateway rate-shapes provider file APIs server-side.
PROVIDER_LIMITS = {}
_provider_sems = {}

def _sem_for(model):
    lim = PROVIDER_LIMITS.get(model.split("/")[0])
    if lim is None:
        return None
    with _lock:
        return _provider_sems.setdefault(model.split("/")[0], threading.Semaphore(lim))

def _attempt(job, file_ids, key, poll_max, wait_s):
    """One create->poll->download cycle. Provider errors (e.g. upstream 429) surface
    as job status=failed here, NOT as HTTP errors — hence the retry loop in run_one."""
    body = dict(model=job["model"], system_prompt=job["prompt"], example_output=job["example"],
                file_id=file_ids[job["path"]], output_format="json")
    job_id = api("POST", "/analyzedoc/jobs", key, json=body).json()["job_id"]
    j = {}
    for _ in range(poll_max):
        j = api("GET", f"/analyzedoc/jobs/{job_id}", key, params={"wait": wait_s}).json()
        if j.get("status") in ("completed", "failed"):
            break
    if j.get("status") == "completed":
        out = api("GET", f"/files/{j['output_file_id']}/content", key).text
        return dict(status="completed", job_id=job_id, output_raw=out, usage=j.get("usage"))
    return dict(status="failed", job_id=job_id, error=json.dumps(j, ensure_ascii=False)[:2000])

def run_one(job, file_ids, key, out_path, poll_max, wait_s, job_retries):
    t0 = time.time()
    rec = {k: job[k] for k in ("key","task","model","doc","L","dpi","rep")}
    sem = _sem_for(job["model"])
    if sem: sem.acquire()
    try:
        for attempt in range(job_retries + 1):
            try:
                r = _attempt(job, file_ids, key, poll_max, wait_s)
            except Exception as e:
                r = dict(status="failed", error=f"{type(e).__name__}: {e}"[:2000])
            if r["status"] == "completed" or attempt == job_retries:
                break
            time.sleep(min(120, 20 * (2 ** attempt)) + random.uniform(0, 3))
        rec.update(r)
        rec["attempts"] = attempt + 1
    finally:
        if sem: sem.release()
    rec["elapsed_s"] = round(time.time() - t0, 1)
    with _lock:
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="pilot", help="all | pilot | ume | comma-separated model IDs")
    ap.add_argument("--t1-reps", type=int, default=5)
    ap.add_argument("--t2-reps", type=int, default=3)
    ap.add_argument("--t1-instances", default="A,B")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--poll-max", type=int, default=90)
    ap.add_argument("--job-retries", type=int, default=3)
    ap.add_argument("--wait", type=int, default=10)
    ap.add_argument("--materials", default="materials")
    ap.add_argument("--out", default="results.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()

    models = MODELS if a.models == "all" else PILOT if a.models == "pilot" else UME if a.models == "ume" \
             else [m.strip() for m in a.models.split(",")]
    unknown = [m for m in models if m not in MODELS]
    if unknown: sys.exit(f"unknown models (not in MODELS): {unknown}")

    jobs = enumerate_jobs(models, a.t1_reps, a.t2_reps, a.materials, [i.strip() for i in a.t1_instances.split(",")])
    missing = [j["path"] for j in jobs if not os.path.exists(j["path"])]
    if missing: sys.exit(f"missing materials ({len(missing)}), e.g. {missing[0]} — run gen_materials.py first")
    done = done_keys(a.out)
    pending = [j for j in jobs if j["key"] not in done]
    print(f"matrix: {len(jobs)} jobs / done: {len(done & {j['key'] for j in jobs})} / pending: {len(pending)}")
    if a.dry_run: return
    if not os.environ.get("LDXHUB_API_KEY"): sys.exit("LDXHUB_API_KEY not set")
    if not a.yes and input("proceed? [y/N] ").lower() != "y": return
    key = os.environ["LDXHUB_API_KEY"]

    print("uploading materials (cached 24h)...")
    file_ids = upload_all(sorted({j["path"] for j in pending}), key)

    t0 = time.time(); ok = fail = 0; tok_in = tok_out = 0
    with ThreadPoolExecutor(a.concurrency) as ex:
        futs = [ex.submit(run_one, j, file_ids, key, a.out, a.poll_max, a.wait, a.job_retries) for j in pending]
        for i, fu in enumerate(as_completed(futs), 1):
            r = fu.result(); ok += r["status"] == "completed"; fail += r["status"] != "completed"
            u = r.get("usage") or {}; tok_in += u.get("input_tokens") or 0; tok_out += u.get("output_tokens") or 0
            if i % 25 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)}  ok={ok} fail={fail}  elapsed={time.time()-t0:,.0f}s")
    print("\n===== RUN SUMMARY =====")
    print(f"pending={len(pending)} ok={ok} fail={fail} elapsed={time.time()-t0:,.0f}s")
    print(f"tokens (completed jobs, this run): input {tok_in:,} / output {tok_out:,}"
          " - rates: https://gw.portal.ldxhub.io/credits-and-pricing")
    print("next: python3 score_results.py && python3 report.py")

if __name__ == "__main__":
    main()
