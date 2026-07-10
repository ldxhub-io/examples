#!/usr/bin/env python3
# sort_test.py — Can the same low-detail modes that fabricate text still
#                classify documents by type? Basic 5-way test.
#
# Generates five layout-distinct synthetic documents (invoice, receipt,
# business card, contract, blank page) and asks each configuration to
# classify them. Companion to fab_test.py.
#
# Usage:
#   pip install requests pillow
#   export LDXHUB_API_KEY="your-key"     # https://gw.portal.ldxhub.io
#   python3 sort_test.py                 # 9 configs x 5 materials x 3 repeats = 135 jobs
#
# Output: sort_results_<ts>.txt / sort_raw_<ts>.jsonl

import os, sys, json, time, itertools, textwrap
from datetime import datetime
import requests
from PIL import Image, ImageDraw, ImageFont

BASE_URL = os.environ.get("BASE_URL", "https://gw.ldxhub.io")
API_KEY  = os.environ["LDXHUB_API_KEY"]
H = {"Authorization": f"Bearer {API_KEY}"}
REPEATS  = int(os.environ.get("REPEATS", "3"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR  = os.path.join(BASE_DIR, "images")

# ---- Fonts ------------------------------------------------------------------
def load_font(size, bold=False):
    cands = (["/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial Bold.ttf"]
             if bold else
             ["/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf"])
    cands.append("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    for p in cands:
        try: return ImageFont.truetype(p, size)
        except Exception: pass
    return ImageFont.load_default()

# ---- Materials (all fully synthetic, deterministic) -------------------------
def make_invoice(path):
    # Same synthetic invoice as fab_test.py (PNG only).
    W, Ht = 1240, 1754
    img = Image.new("RGB", (W, Ht), "white"); d = ImageDraw.Draw(img)
    f_title, f_h, f_m, f_s = load_font(64, True), load_font(26, True), load_font(24), load_font(20)
    d.text((110, 120), "INVOICE", font=f_title, fill=(20, 24, 34))
    d.text((640, 130), "K Northwind Trading Ltd.", font=f_m, fill=(70, 70, 70))
    d.text((640, 165), "3-8-1 Kita-Aoyama, Minato-ku", font=f_s, fill=(120, 120, 120))
    d.text((640, 192), "Tokyo 107-0061, Japan", font=f_s, fill=(120, 120, 120))
    d.text((110, 300), "BILL TO", font=f_s, fill=(150, 150, 150))
    d.text((110, 330), "Aozora Manufacturing Inc.", font=f_m, fill="black")
    d.text((110, 362), "1-2-3 Harumi, Chuo-ku", font=f_s, fill="black")
    d.text((110, 389), "Tokyo 104-0053, Japan", font=f_s, fill="black")
    d.text((640, 300), "INVOICE NO.", font=f_s, fill=(150, 150, 150))
    d.text((640, 330), "INV-2026-0731", font=f_m, fill="black")
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
            else:
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
    img.save(path, "PNG")

def make_receipt(path):
    W, Ht = 400, 900
    img = Image.new("RGB", (W, Ht), "white"); d = ImageDraw.Draw(img)
    big, mid, sml = load_font(28), load_font(20), load_font(16)
    def center(y, t, f):
        w = d.textlength(t, font=f); d.text(((W - w) / 2, y), t, fill="black", font=f)
    center(40, "GREEN MART", big)
    center(80, "2-3-4 Sakura St, Tokyo", sml)
    center(105, "TEL 03-0000-1111", sml)
    d.text((20, 150), "-" * 46, font=sml, fill="black")
    items = [("Milk 1L", "248"), ("Bread", "158"), ("Eggs 10pk", "298"),
             ("Apple x4", "480"), ("Coffee beans", "980"), ("Butter", "420"),
             ("Yogurt", "138"), ("Rice 2kg", "1180")]
    y = 185
    for name, price in items:
        d.text((30, y), name, font=mid, fill="black")
        w = d.textlength(price, font=mid); d.text((W - 40 - w, y), price, font=mid, fill="black")
        y += 38
    d.text((20, y + 10), "-" * 46, font=sml, fill="black")
    d.text((30, y + 50), "TOTAL", font=big, fill="black")
    w = d.textlength("3,902", font=big); d.text((W - 40 - w, y + 50), "3,902", font=big, fill="black")
    center(y + 130, "Thank you!", mid)
    img.save(path, "PNG")

def make_business_card(path):
    W, Ht = 650, 380
    img = Image.new("RGB", (W, Ht), "white"); d = ImageDraw.Draw(img)
    d.rectangle([6, 6, W - 7, Ht - 7], outline=(60, 60, 60), width=2)
    big, mid, sml = load_font(36), load_font(22), load_font(16)
    d.text((40, 40), "Sakura Trading Co., Ltd.", font=mid, fill=(30, 30, 120))
    d.text((40, 140), "Taro Yamada", font=big, fill="black")
    d.text((40, 192), "Sales Manager", font=mid, fill=(80, 80, 80))
    d.text((40, 280), "TEL: 03-1234-0000   MAIL: t.yamada@example.co.jp", font=sml, fill="black")
    d.text((40, 310), "5-6-7 Chuo, Minato-ku, Tokyo 100-0000", font=sml, fill="black")
    img.save(path, "PNG")

def make_contract(path):
    W, Ht = 900, 1273
    img = Image.new("RGB", (W, Ht), "white"); d = ImageDraw.Draw(img)
    big, mid, sml = load_font(30), load_font(20), load_font(16)
    t = "SERVICE AGREEMENT"
    w = d.textlength(t, font=big); d.text(((W - w) / 2, 60), t, font=big, fill="black")
    d.text((70, 130), "This Agreement is entered into by and between Party A and Party B", font=sml, fill="black")
    d.text((70, 152), "as of the date of the last signature below.", font=sml, fill="black")
    body = ("The parties agree to the terms and conditions set forth herein. Each "
            "provision of this Agreement shall be interpreted in accordance with "
            "applicable law and neither party may assign its rights without consent.")
    y = 215
    for i, title in enumerate(["Purpose", "Term", "Fees and Payment",
                               "Confidentiality", "Termination", "Governing Law"], 1):
        d.text((70, y), f"Article {i} ({title})", font=mid, fill="black"); y += 32
        for line in textwrap.wrap(body, 86):
            d.text((90, y), line, font=sml, fill="black"); y += 22
        y += 14
    d.text((70, Ht - 140), "IN WITNESS WHEREOF, the parties have executed this Agreement.", font=sml, fill="black")
    d.text((70, Ht - 90), "Party A: ____________________    Party B: ____________________", font=sml, fill="black")
    img.save(path, "PNG")

def make_blank(path):
    Image.new("RGB", (900, 1273), "white").save(path, "PNG")

# label -> (filename, generator)
MATERIALS = {
    "invoice":       ("sort_invoice.png",       make_invoice),
    "receipt":       ("sort_receipt.png",       make_receipt),
    "business_card": ("sort_business_card.png", make_business_card),
    "contract":      ("sort_contract.png",      make_contract),
    "blank":         ("sort_blank.png",         make_blank),
}

# Same suspects/controls as fab_test.py (minus the 5.4-generation controls;
# add them back if you want the full grid).
SUSPECTS = ["openai/gpt-5.5@low",
            "openai/gpt-5.6-sol@low", "openai/gpt-5.6-terra@low", "openai/gpt-5.6-luna@low",
            "azure/gpt-5.6-sol@low",  "azure/gpt-5.6-terra@low",  "azure/gpt-5.6-luna@low"]
CONTROLS = ["google/gemini-3.5-flash@low", "openai/gpt-5.6-sol@high"]
MODELS = SUSPECTS + CONTROLS

SYSTEM_PROMPT = ("Classify this document image into exactly one of these types: "
                 "invoice, receipt, business_card, contract, blank, other. "
                 "Judge from the overall layout and structure of the page.")

EXAMPLE_OUTPUT = {"document_type": "other",
                  "reason": "layout does not match any listed type"}

def verdict(expected, o):
    if not isinstance(o, dict):
        return "PARSE_FAIL", ""
    dt = str(o.get("document_type", "")).strip().lower().replace(" ", "_").replace("-", "_")
    v = "OK" if dt == expected else f"MISS->{dt or '?'}"
    return v, f"reason={str(o.get('reason', ''))[:60]!r}"

# ---- API (identical to fab_test.py) -----------------------------------------
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
    res_path, raw_path = f"sort_results_{ts}.txt", f"sort_raw_{ts}.jsonl"
    print(f"env={BASE_URL}  repeats={REPEATS}")

    os.makedirs(IMG_DIR, exist_ok=True)
    fids = {}
    for label, (fname, maker) in MATERIALS.items():
        p = os.path.join(IMG_DIR, fname)
        maker(p)
        fids[label] = upload(p)
        print(f"uploaded {label}: {fids[label]}")

    jobs = []
    for run in range(1, REPEATS + 1):
        for model, label in itertools.product(MODELS, MATERIALS):
            try: jid = submit(model, fids[label])
            except Exception as e:
                jobs.append((model, label, run, f"SUBMIT_ERR:{e}")); continue
            jobs.append((model, label, run, jid))
            print(f"submitted r{run} {model} {label} -> {jid}")
            time.sleep(0.3)

    lines, tally = [], {}
    raw = open(raw_path, "w", encoding="utf-8")
    for model, label, run, jid in jobs:
        if jid.startswith("SUBMIT_ERR"):
            v, detail, out = "SUBMIT_ERR", jid, None
        else:
            j = wait_done(jid)
            if j["status"] != "completed":
                v, detail, out = j["status"].upper(), jid, None
            else:
                out = download(j["output_file_id"])
                v, detail = verdict(label, out)
        raw.write(json.dumps({"model": model, "material": label, "run": run,
                              "job_id": jid, "verdict": v, "output": out},
                             ensure_ascii=False) + "\n")
        line = f"{model:34s} {label:14s} r{run}  {v:22s} {detail}"
        print(line); lines.append(line)
        tally.setdefault((model, label), []).append(v)
    raw.close()

    smry = ["", "=" * 72, f"SUMMARY  (env={BASE_URL}, repeats={REPEATS}, {ts})", "=" * 72]
    for (model, label), vs in sorted(tally.items()):
        c = {}
        for v in vs: c[v] = c.get(v, 0) + 1
        smry.append(f"{model:34s} {label:14s}  " + "  ".join(f"{k}x{n}" for k, n in sorted(c.items())))
    text = "\n".join(lines + smry)
    open(res_path, "w", encoding="utf-8").write(text)
    print("\n".join(smry))
    print(f"\nsaved: {res_path} / {raw_path}")

if __name__ == "__main__":
    main()
