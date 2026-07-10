#!/usr/bin/env python3
# sort_lookalike_test.py — The unfair version of sort_test.py.
#
# Three Japanese business documents — 請求書 (invoice), 御見積書 (quotation),
# 注文書 (purchase order) — with IDENTICAL layouts, tables, amounts and
# document numbers. The only differences are the title and one label line.
# You cannot sort these by shape; the model must read the title.
# Then the same documents are degraded: photocopier noise, a 2° tilt,
# JPEG quality 25, and a worst-case cross (quotation x scan noise).
#
# Usage:
#   pip install requests pillow
#   export LDXHUB_API_KEY="your-key"     # https://gw.portal.ldxhub.io
#   python3 sort_lookalike_test.py       # 9 configs x 7 materials x 3 repeats = 189 jobs
#
# Requires a Japanese font (Hiragino on macOS, Noto Sans CJK on Linux) —
# edit ja_font() below if yours lives elsewhere.
#
# Output: sort_lookalike_results_<ts>.txt / sort_lookalike_raw_<ts>.jsonl

import os, sys, json, time, itertools
from datetime import datetime
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

BASE_URL = os.environ.get("BASE_URL", "https://gw.ldxhub.io")
API_KEY  = os.environ["LDXHUB_API_KEY"]
H = {"Authorization": f"Bearer {API_KEY}"}
REPEATS  = int(os.environ.get("REPEATS", "3"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR  = os.path.join(BASE_DIR, "images")

# ---- Japanese font (macOS -> Linux) -----------------------------------------
def ja_font(size):
    for p in ["/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
              "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
              "/System/Library/Fonts/Hiragino Sans GB.ttc",
              "/Library/Fonts/Osaka.ttf",
              "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
        try: return ImageFont.truetype(p, size)
        except Exception: pass
    sys.exit("Japanese font not found — add a path in ja_font()")

# ---- Look-alike generator (everything identical except title + one line) -----
def make_ja_doc(path, title, extra_label, extra_value):
    W, Ht = 900, 1273
    img = Image.new("RGB", (W, Ht), "white"); d = ImageDraw.Draw(img)
    f_t, f_m, f_s = ja_font(52), ja_font(24), ja_font(18)
    d.text((560, 60), "株式会社サンプル商事", font=f_m, fill="black")
    d.text((560, 100), "東京都中央区日本橋1-2-3", font=f_s, fill="black")
    d.text((560, 126), "TEL 03-0000-2222", font=f_s, fill="black")
    w = d.textlength(title, font=f_t)
    d.text(((W - w) / 2, 180), title, font=f_t, fill="black")
    d.line([(W - w) / 2, 248, (W + w) / 2, 248], fill="black", width=3)
    d.text((70, 300), "テスト株式会社 御中", font=f_m, fill="black")
    d.text((600, 300), "No. 2026-0731", font=f_s, fill="black")
    d.text((600, 328), "発行日: 2026-07-10", font=f_s, fill="black")
    left, right, top = 70, 830, 420
    cols = [70, 470, 590, 700, 830]
    d.rectangle([left, top, right, top + 44], fill=(40, 45, 60))
    for i, h in enumerate(["品名", "数量", "単価", "金額"]):
        d.text((cols[i] + 14, top + 10), h, font=f_m, fill="white")
    rows = [("翻訳サービス（日英）", "20", "6,000", "120,000"),
            ("DTP編集作業", "15", "3,200", "48,000"),
            ("用語集メンテナンス", "1", "30,000", "30,000")]
    y = top + 44
    for r in rows:
        for i, cell in enumerate(r):
            d.text((cols[i] + 14, y + 10), cell, font=f_s, fill="black")
        d.line([(left, y + 42), (right, y + 42)], fill=(180, 180, 180))
        y += 42
    for x in cols:
        d.line([(x, top), (x, y)], fill=(150, 150, 150))
    d.rectangle([left, top, right, y], outline=(60, 60, 60), width=2)
    ty = y + 56
    d.text((560, ty), "小計", font=f_s, fill="black");        d.text((720, ty), "¥198,000", font=f_s, fill="black")
    d.text((560, ty + 30), "消費税（10%）", font=f_s, fill="black"); d.text((720, ty + 30), "¥19,800", font=f_s, fill="black")
    d.text((560, ty + 68), "合計", font=f_m, fill="black");   d.text((700, ty + 68), "¥217,800", font=f_m, fill="black")
    d.text((70, ty + 150), f"{extra_label}: {extra_value}", font=f_m, fill="black")
    d.text((70, Ht - 110), "備考: 本書は検証用に生成された架空の文書です。", font=f_s, fill=(90, 90, 90))
    img.save(path, "PNG")

# ---- Degradations -------------------------------------------------------------
def degrade_scan(src, dst):   # photocopier: noise + blur + lower contrast
    img = Image.open(src).convert("L")
    noise = Image.effect_noise(img.size, 22)
    img = Image.blend(img, noise, 0.18)
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    ImageEnhance.Contrast(img).enhance(0.92).convert("RGB").save(dst, "PNG")

def degrade_tilt(src, dst):   # 2 degree tilt
    Image.open(src).rotate(2.0, expand=True, fillcolor="white",
                           resample=Image.BICUBIC).save(dst, "PNG")

def degrade_jpeg(src, dst):   # heavy compression
    Image.open(src).convert("RGB").save(dst, "JPEG", quality=25)

# (key, expected label, filename)
MATERIALS = [
    ("invoice_ja_clean",   "invoice",        "sort_lookalike_invoice_ja.png"),
    ("quotation_ja_clean", "quotation",      "sort_lookalike_quotation_ja.png"),
    ("po_ja_clean",        "purchase_order", "sort_lookalike_po_ja.png"),
    ("invoice_ja_scan",    "invoice",        "sort_lookalike_invoice_ja_scan.png"),
    ("invoice_ja_tilt",    "invoice",        "sort_lookalike_invoice_ja_tilt.png"),
    ("invoice_ja_jpeg25",  "invoice",        "sort_lookalike_invoice_ja_q25.jpg"),
    ("quotation_ja_scan",  "quotation",      "sort_lookalike_quotation_ja_scan.png"),
]

def build_materials():
    p = {k: os.path.join(IMG_DIR, f) for k, _, f in MATERIALS}
    make_ja_doc(p["invoice_ja_clean"],   "請 求 書", "お支払期限", "2026-08-31")
    make_ja_doc(p["quotation_ja_clean"], "御 見 積 書", "見積有効期限", "発行日より30日間")
    make_ja_doc(p["po_ja_clean"],        "注 文 書", "納品希望日", "2026-07-31")
    degrade_scan(p["invoice_ja_clean"],   p["invoice_ja_scan"])
    degrade_tilt(p["invoice_ja_clean"],   p["invoice_ja_tilt"])
    degrade_jpeg(p["invoice_ja_clean"],   p["invoice_ja_jpeg25"])
    degrade_scan(p["quotation_ja_clean"], p["quotation_ja_scan"])
    return p

MODELS = ["openai/gpt-5.5@low",
          "openai/gpt-5.6-sol@low", "openai/gpt-5.6-terra@low", "openai/gpt-5.6-luna@low",
          "azure/gpt-5.6-sol@low",  "azure/gpt-5.6-terra@low",  "azure/gpt-5.6-luna@low",
          "google/gemini-3.5-flash@low", "openai/gpt-5.6-sol@high"]

SYSTEM_PROMPT = ("Classify this Japanese business document image into exactly one of: "
                 "invoice (請求書), quotation (見積書), purchase_order (注文書/発注書), "
                 "receipt, business_card, contract, blank, other. "
                 "Layouts may be nearly identical — identify the type from the document "
                 "title and wording.")

EXAMPLE_OUTPUT = {"document_type": "other",
                  "reason": "title and wording do not match any listed type"}

def verdict(expected, o):
    if not isinstance(o, dict):
        return "PARSE_FAIL", ""
    dt = str(o.get("document_type", "")).strip().lower().replace(" ", "_").replace("-", "_")
    v = "OK" if dt == expected else f"MISS->{dt or '?'}"
    return v, f"reason={str(o.get('reason', ''))[:60]!r}"

# ---- API ----------------------------------------------------------------------
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

# ---- Run ------------------------------------------------------------------------
def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    res_path = f"sort_lookalike_results_{ts}.txt"
    raw_path = f"sort_lookalike_raw_{ts}.jsonl"
    print(f"env={BASE_URL}  repeats={REPEATS}")

    os.makedirs(IMG_DIR, exist_ok=True)
    paths = build_materials()
    fids, expected = {}, {}
    for key, label, _ in MATERIALS:
        fids[key] = upload(paths[key]); expected[key] = label
        print(f"uploaded {key}: {fids[key]}")

    jobs = []
    for run in range(1, REPEATS + 1):
        for model, (key, _, _) in itertools.product(MODELS, MATERIALS):
            try: jid = submit(model, fids[key])
            except Exception as e:
                jobs.append((model, key, run, f"SUBMIT_ERR:{e}")); continue
            jobs.append((model, key, run, jid))
            print(f"submitted r{run} {model} {key} -> {jid}")
            time.sleep(0.3)

    lines, tally = [], {}
    raw = open(raw_path, "w", encoding="utf-8")
    for model, key, run, jid in jobs:
        if jid.startswith("SUBMIT_ERR"):
            v, detail, out = "SUBMIT_ERR", jid, None
        else:
            j = wait_done(jid)
            if j["status"] != "completed":
                v, detail, out = j["status"].upper(), jid, None
            else:
                out = download(j["output_file_id"])
                v, detail = verdict(expected[key], out)
        raw.write(json.dumps({"model": model, "material": key, "run": run,
                              "job_id": jid, "verdict": v, "output": out},
                             ensure_ascii=False) + "\n")
        line = f"{model:34s} {key:20s} r{run}  {v:24s} {detail}"
        print(line); lines.append(line)
        tally.setdefault((model, key), []).append(v)
    raw.close()

    smry = ["", "=" * 72, f"SUMMARY  (env={BASE_URL}, repeats={REPEATS}, {ts})", "=" * 72]
    for (model, key), vs in sorted(tally.items()):
        c = {}
        for v in vs: c[v] = c.get(v, 0) + 1
        smry.append(f"{model:34s} {key:20s}  " + "  ".join(f"{k}x{n}" for k, n in sorted(c.items())))
    text = "\n".join(lines + smry)
    open(res_path, "w", encoding="utf-8").write(text)
    print("\n".join(smry))
    print(f"\nsaved: {res_path} / {raw_path}")

if __name__ == "__main__":
    main()
