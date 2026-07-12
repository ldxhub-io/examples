#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legibility Frontier — benchmark runner (resume-safe).

Usage:
  export LDXHUB_API_KEY=...
  python3 run_benchmark.py --dry-run                 # enumerate + cost preflight only
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
T1_OUT_CHARS, T2_OUT_CHARS = 350, 25               # cost-estimate assumptions
UPLOAD_TTL_H = 24

MODELS = [  # canonical order (provider-grouped) — 27 entries, AnalyzeDoc catalog 2026-07-11
 "openai/gpt-5.6-sol@high","openai/gpt-5.6-sol@low","openai/gpt-5.6-terra@high","openai/gpt-5.6-terra@low",
 "openai/gpt-5.6-luna@high","openai/gpt-5.6-luna@low","openai/gpt-5.5@high","openai/gpt-5.5@low",
 "openai/gpt-5.4@high","openai/gpt-5.4-mini@high",
 "azure/gpt-5.6-sol@high","azure/gpt-5.6-sol@low","azure/gpt-5.6-terra@high","azure/gpt-5.6-terra@low",
 "azure/gpt-5.6-luna@high","azure/gpt-5.6-luna@low","azure/gpt-5.4@high","azure/gpt-5.4@low",
 "azure/gpt-5.4-mini@high","azure/gpt-5.4-mini@low",
 "google/gemini-3.5-flash@high","google/gemini-3.5-flash@medium","google/gemini-3.5-flash@low",
 "anthropic/claude-fable-5","anthropic/claude-sonnet-5","anthropic/claude-opus-4-8",
 "bedrock/global.amazon.nova-2-lite-v1:0",
]
RATES = {  # (page_rate, output_rate/1000 chars) — billing.json 2026-07-11
 "openai/gpt-5.6-sol@high":(602,900),"openai/gpt-5.6-sol@low":(63,900),
 "openai/gpt-5.6-terra@high":(301,450),"openai/gpt-5.6-terra@low":(32,450),
 "openai/gpt-5.6-luna@high":(121,180),"openai/gpt-5.6-luna@low":(13,180),
 "openai/gpt-5.5@high":(602,900),"openai/gpt-5.5@low":(63,900),
 "openai/gpt-5.4@high":(301,450),"openai/gpt-5.4-mini@high":(91,135),
 "azure/gpt-5.6-sol@high":(334,1080),"azure/gpt-5.6-sol@low":(76,1080),
 "azure/gpt-5.6-terra@high":(167,540),"azure/gpt-5.6-terra@low":(38,540),
 "azure/gpt-5.6-luna@high":(67,216),"azure/gpt-5.6-luna@low":(16,216),
 "azure/gpt-5.4@high":(167,540),"azure/gpt-5.4@low":(38,540),
 "azure/gpt-5.4-mini@high":(51,162),"azure/gpt-5.4-mini@low":(12,162),
 "google/gemini-3.5-flash@high":(66,270),"google/gemini-3.5-flash@medium":(32,270),"google/gemini-3.5-flash@low":(16,270),
 "anthropic/claude-fable-5":(1909,1500),"anthropic/claude-sonnet-5":(573,450),"anthropic/claude-opus-4-8":(955,750),
 "bedrock/global.amazon.nova-2-lite-v1:0":(4,75),
}
PILOT = ["google/gemini-3.5-flash@high","openai/gpt-5.5@low","anthropic/claude-fable-5"]
UME   = ["google/gemini-3.5-flash@high","openai/gpt-5.5@low","azure/gpt-5.4-mini@low"]

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
                                     prompt=T1_PROMPT, example=T1_EXAMPLE, out_chars=T1_OUT_CHARS))
            for doc in T2_DOCS:
                for rep in range(t2_reps):
                    jobs.append(dict(key=f"t2|{m}|{doc}|L{li}|r{rep}", task="t2", model=m,
                                     doc=doc, L=li, dpi=dpi, rep=rep,
                                     path=f"{mat_dir}/{doc}_L{li}_{dpi}dpi.png",
                                     prompt=T2_PROMPT, example=T2_EXAMPLE, out_chars=T2_OUT_CHARS))
    return jobs

def done_keys(out_path):
    done = set()
    if os.path.exists(out_path):
        for line in open(out_path, encoding="utf-8"):
            try: rec = json.loads(line)
            except Exception: continue
            if rec.get("status") == "completed": done.add(rec["key"])
    return done

def estimate(jobs):
    return sum(RATES[j["model"]][0] + j["out_chars"] * RATES[j["model"]][1] / 1000 for j in jobs)

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
        return dict(status="completed", job_id=job_id, output_raw=out)
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
    unknown = [m for m in models if m not in RATES]
    if unknown: sys.exit(f"unknown models: {unknown}")

    jobs = enumerate_jobs(models, a.t1_reps, a.t2_reps, a.materials, [i.strip() for i in a.t1_instances.split(",")])
    missing = [j["path"] for j in jobs if not os.path.exists(j["path"])]
    if missing: sys.exit(f"missing materials ({len(missing)}), e.g. {missing[0]} — run gen_materials.py first")
    done = done_keys(a.out)
    pending = [j for j in jobs if j["key"] not in done]
    cr = estimate(pending)
    print(f"matrix: {len(jobs)} jobs / done: {len(done & {j['key'] for j in jobs})} / pending: {len(pending)}")
    print(f"estimated pending cost: {cr:,.0f} credits (≈ ${cr*1e-4:,.2f} list)")
    if a.dry_run: return
    if not os.environ.get("LDXHUB_API_KEY"): sys.exit("LDXHUB_API_KEY not set")
    if not a.yes and input("proceed? [y/N] ").lower() != "y": return
    key = os.environ["LDXHUB_API_KEY"]

    print("uploading materials (cached 24h)...")
    file_ids = upload_all(sorted({j["path"] for j in pending}), key)

    t0 = time.time(); ok = fail = 0
    with ThreadPoolExecutor(a.concurrency) as ex:
        futs = [ex.submit(run_one, j, file_ids, key, a.out, a.poll_max, a.wait, a.job_retries) for j in pending]
        for i, fu in enumerate(as_completed(futs), 1):
            r = fu.result(); ok += r["status"] == "completed"; fail += r["status"] != "completed"
            if i % 25 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)}  ok={ok} fail={fail}  elapsed={time.time()-t0:,.0f}s")
    print("\n===== RUN SUMMARY =====")
    print(f"pending={len(pending)} ok={ok} fail={fail} elapsed={time.time()-t0:,.0f}s")
    print(f"estimated credits consumed: {estimate([j for j in pending]):,.0f} (page+assumed output)")
    print("next: python3 score_results.py && python3 report.py")

if __name__ == "__main__":
    main()
