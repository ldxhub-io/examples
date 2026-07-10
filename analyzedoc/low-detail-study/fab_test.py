#!/usr/bin/env python3
# fab_test.py — Statistical test: do low-detail vision modes fabricate text
#               when extracting from document images?
#
# Generates a fully synthetic invoice (all names fictional), renders it to
# PNG and JPEG, then runs N repeats of the same extraction across model
# configurations and scores every result against frozen ground truth.
#
# Usage:
#   pip install requests pillow
#   export LDXHUB_API_KEY="your-key"     # https://gw.portal.ldxhub.io
#   python3 fab_test.py                  # 11 configs x {jpg,png} x 5 repeats = 110 jobs
#
# Tunables (env vars):
#   REPEATS=3 python3 fab_test.py
#   BASE_URL=https://... python3 fab_test.py
#
# Output:
#   fab_results_<ts>.txt   — per-run verdicts + summary table
#   fab_raw_<ts>.jsonl     — every raw model output
#
# The recorded runs in results/ are from 2026-07-10. Provider vision
# pipelines change; re-run before trusting the numbers.

import os, sys, json, time, itertools
from datetime import datetime
import requests
from PIL import Image, ImageDraw, ImageFont

BASE_URL = os.environ.get("BASE_URL", "https://gw.ldxhub.io")
API_KEY  = os.environ["LDXHUB_API_KEY"]
H = {"Authorization": f"Bearer {API_KEY}"}
REPEATS  = int(os.environ.get("REPEATS", "5"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR  = os.path.join(BASE_DIR, "images")

# ---- Ground truth (entirely fictional) -------------------------------------
TRUTH = {
    "vendor_key":  "K Northwind",            # substring match keys
    "vendor":      "K Northwind Trading Ltd.",
    "bill_to_key": "Aozora",
    "bill_to":     "Aozora Manufacturing Inc.",
    "invoice_number": "INV-2026-0731",
    "total": 833.25,
}

# ---- Material generation ----------------------------------------------------
def load_font(size, bold=False):
    cands = (["/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial Bold.ttf"]
             if bold else
             ["/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf"])
    cands.append("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    for p in cands:
        try: return ImageFont.truetype(p, size)
        except Exception: pass
    return ImageFont.load_default()

def make_invoice(png_path, jpg_path):
    W, Ht = 1240, 1754
    img = Image.new("RGB", (W, Ht), "white"); d = ImageDraw.Draw(img)
    f_title, f_h, f_m, f_s = load_font(64, True), load_font(26, True), load_font(24), load_font(20)

    d.text((110, 120), "INVOICE", font=f_title, fill=(20, 24, 34))
    d.text((640, 130), TRUTH["vendor"], font=f_m, fill=(70, 70, 70))
    d.text((640, 165), "3-8-1 Kita-Aoyama, Minato-ku", font=f_s, fill=(120, 120, 120))
    d.text((640, 192), "Tokyo 107-0061, Japan", font=f_s, fill=(120, 120, 120))

    d.text((110, 300), "BILL TO", font=f_s, fill=(150, 150, 150))
    d.text((110, 330), TRUTH["bill_to"], font=f_m, fill="black")
    d.text((110, 362), "1-2-3 Harumi, Chuo-ku", font=f_s, fill="black")
    d.text((110, 389), "Tokyo 104-0053, Japan", font=f_s, fill="black")
    d.text((640, 300), "INVOICE NO.", font=f_s, fill=(150, 150, 150))
    d.text((640, 330), TRUTH["invoice_number"], font=f_m, fill="black")
    d.text((930, 300), "DATE", font=f_s, fill=(150, 150, 150))
    d.text((930, 330), "2026-07-31", font=f_m, fill="black")

    left, right, top = 110, 1130, 470
    cols = [110, 700, 830, 980, 1130]
    d.rectangle([left, top, right, top + 50], fill=(40, 45, 60))
    for i, h in enumerate(["Description", "Qty", "Unit Price", "Amount"]):
        d.text((cols[i] + 16, top + 12), h, font=f_h, fill="white")
    rows = [("PDF-to-Word conversion (JP)", "120", "$2.50", "$300.00"),
            ("XLIFF translation refinement", "80", "$3.00", "$240.00"),
            ("OCR document processing", "45", "$1.50", "$67.50"),
            ("Vision structured extraction", "30", "$5.00", "$150.00")]
    y = top + 50
    for idx, r in enumerate(rows):
        if idx % 2 == 1:
            d.rectangle([left, y, right, y + 50], fill=(243, 244, 246))
        for i, cell in enumerate(r):
            if i == 0:
                d.text((cols[i] + 16, y + 12), cell, font=f_m, fill="black")
            else:  # numeric columns right-aligned
                w = d.textlength(cell, font=f_m)
                d.text((cols[i + 1] - 20 - w, y + 12), cell, font=f_m, fill="black")
        y += 50
    d.line([(left, y), (right, y)], fill=(180, 180, 180), width=2)

    ty = y + 70
    for label, val, big in [("Subtotal", "$757.50", False),
                            ("Tax (10%)", "$75.75", False),
                            ("Total", "$833.25", True)]:
        f = f_h if big else f_m
        w1 = d.textlength(label, font=f); d.text((980 - w1, ty), label, font=f, fill="black")
        w2 = d.textlength(val, font=f);   d.text((1130 - w2, ty), val, font=f, fill="black")
        if big: d.line([(760, ty - 12), (1130, ty - 12)], fill="black", width=2)
        ty += 44
    d.text((110, ty + 60), "All amounts are in USD. Payment due within 30 days.",
           font=f_s, fill=(130, 130, 130))
    d.text((110, Ht - 90), "This is a synthetic invoice generated for testing. All names are fictional.",
           font=f_s, fill=(170, 170, 170))
    img.save(png_path, "PNG")
    img.save(jpg_path, "JPEG", quality=90)

# ---- Configurations ---------------------------------------------------------
# "Suspects": low-detail modes of the GPT-5.5 / GPT-5.6 generations.
# "Controls": previous generation at the same detail level, a different
# provider at a *smaller* token budget, and one high-detail reference.
MODELS = ["openai/gpt-5.5@low",
          "openai/gpt-5.6-sol@low", "openai/gpt-5.6-terra@low", "openai/gpt-5.6-luna@low",
          "azure/gpt-5.6-sol@low",  "azure/gpt-5.6-terra@low",  "azure/gpt-5.6-luna@low",
          "azure/gpt-5.4@low", "azure/gpt-5.4-mini@low",
          "google/gemini-3.5-flash@low",
          "openai/gpt-5.6-sol@high"]

SYSTEM_PROMPT = ("Extract this invoice into structured JSON: vendor, bill_to, "
                 "invoice_number, date, line_items (each with description, qty, "
                 "unit_price, amount), subtotal, tax, total, currency.")

# Non-X.0 decimals on purpose: values like 10.0 collapse to integers in JSON
# round-trips, which silently turns the inferred schema into integer fields
# and produces a convincing false positive ("the model corrupts decimals").
EXAMPLE_OUTPUT = {
    "vendor": "Acme Corp", "bill_to": "John Doe",
    "invoice_number": "INV-001", "date": "2026-01-01",
    "line_items": [{"description": "Widget", "qty": 2,
                    "unit_price": 12.34, "amount": 24.68}],
    "subtotal": 24.68, "tax": 2.47, "total": 27.15, "currency": "USD",
}

# ---- Verdicts (criteria frozen before any run) ------------------------------
# OK           : all four of total / invoice_number / vendor / bill_to match
# FABRICATED   : none of the four match (= a different, invented document)
# PARTIAL(n/4) : in between (misreads or partial invention)
# INT_TRUNC    : total came back as the integer part (schema-degradation guard)
def verdict(o):
    if not isinstance(o, dict):
        return "PARSE_FAIL", ""
    try:    total_ok = abs(float(o.get("total", -1)) - TRUTH["total"]) < 0.005
    except: total_ok = False
    inv_ok  = o.get("invoice_number") == TRUTH["invoice_number"]
    ven_ok  = TRUTH["vendor_key"]  in str(o.get("vendor", ""))
    bill_ok = TRUTH["bill_to_key"] in str(o.get("bill_to", ""))
    score = sum([total_ok, inv_ok, ven_ok, bill_ok])
    if score == 4: v = "OK"
    elif score == 0: v = "FABRICATED"
    else:
        v = f"PARTIAL({score}/4)"
        try:
            if not total_ok and abs(float(o.get("total", -1)) - int(TRUTH["total"])) < 0.005:
                v = "INT_TRUNC"
        except: pass
    detail = f"total={o.get('total')} inv={o.get('invoice_number')} vendor={str(o.get('vendor',''))[:28]!r}"
    return v, detail

# ---- API --------------------------------------------------------------------
def upload(path):
    with open(path, "rb") as f:
        r = requests.post(f"{BASE_URL}/files", headers=H,
                          files={"file": (os.path.basename(path), f)}, timeout=120)
    r.raise_for_status(); return r.json()["file_id"]

def submit(model, file_id):
    body = {"model": model, "file_id": file_id, "output_format": "json",
            "system_prompt": SYSTEM_PROMPT, "example_output": EXAMPLE_OUTPUT}
    r = requests.post(f"{BASE_URL}/analyzedoc/jobs",
                      headers={**H, "Content-Type": "application/json"},
                      data=json.dumps(body), timeout=60)
    r.raise_for_status(); return r.json()["job_id"]

def wait_done(job_id, max_polls=12):
    for _ in range(max_polls):
        r = requests.get(f"{BASE_URL}/analyzedoc/jobs/{job_id}", headers=H,
                         params={"wait": 30}, timeout=60)
        r.raise_for_status(); j = r.json()
        if j["status"] in ("completed", "failed"): return j
    return {"status": "timeout", "job_id": job_id}

def download(file_id):
    r = requests.get(f"{BASE_URL}/files/{file_id}/content", headers=H, timeout=120)
    r.raise_for_status()
    try: return r.json()
    except Exception: return r.text

# ---- Run --------------------------------------------------------------------
def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    res_path, raw_path = f"fab_results_{ts}.txt", f"fab_raw_{ts}.jsonl"
    print(f"env={BASE_URL}  repeats={REPEATS}")

    os.makedirs(IMG_DIR, exist_ok=True)
    png = os.path.join(IMG_DIR, "fab_invoice.png")
    jpg = os.path.join(IMG_DIR, "fab_invoice.jpg")
    make_invoice(png, jpg)
    fids = {"jpg": upload(jpg), "png": upload(png)}
    for k, v in fids.items(): print(f"uploaded {k}: {v}")

    jobs = []
    for run in range(1, REPEATS + 1):
        for model, fmt in itertools.product(MODELS, fids):
            try: jid = submit(model, fids[fmt])
            except Exception as e:
                jobs.append((model, fmt, run, f"SUBMIT_ERR:{e}")); continue
            jobs.append((model, fmt, run, jid))
            print(f"submitted r{run} {model} {fmt} -> {jid}")
            time.sleep(0.3)

    lines, tally = [], {}
    raw = open(raw_path, "w", encoding="utf-8")
    for model, fmt, run, jid in jobs:
        if jid.startswith("SUBMIT_ERR"):
            v, detail, out = "SUBMIT_ERR", jid, None
        else:
            j = wait_done(jid)
            if j["status"] != "completed":
                v, detail, out = j["status"].upper(), jid, None
            else:
                out = download(j["output_file_id"])
                v, detail = verdict(out)
        raw.write(json.dumps({"model": model, "fmt": fmt, "run": run,
                              "job_id": jid, "verdict": v, "output": out},
                             ensure_ascii=False) + "\n")
        line = f"{model:34s} {fmt:4s} r{run}  {v:14s} {detail}"
        print(line); lines.append(line)
        tally.setdefault((model, fmt), []).append(v)
    raw.close()

    smry = ["", "=" * 72, f"SUMMARY  (env={BASE_URL}, repeats={REPEATS}, {ts})", "=" * 72]
    for (model, fmt), vs in sorted(tally.items()):
        c = {}
        for v in vs: c[v] = c.get(v, 0) + 1
        smry.append(f"{model:34s} {fmt:4s}  " + "  ".join(f"{k}x{n}" for k, n in sorted(c.items())))
    text = "\n".join(lines + smry)
    open(res_path, "w", encoding="utf-8").write(text)
    print("\n".join(smry))
    print(f"\nsaved: {res_path} / {raw_path}")

if __name__ == "__main__":
    main()
