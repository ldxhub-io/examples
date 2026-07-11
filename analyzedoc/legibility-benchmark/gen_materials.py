# -*- coding: utf-8 -*-
"""Legibility Frontier v1 — material generator (deterministic).
Canvas: 2480x3508 (A4@300dpi). Ladder: simulated scan dpi via down/up resample."""
from PIL import Image, ImageDraw, ImageFont
import json, os

W,H = 2480,3508
M = 200
LADDER = [300,150,100,70,50,35,25]   # L0..L6 — v1.1: probe-driven (fine dies ~35, body ~25)
OUT = "materials"; os.makedirs(OUT, exist_ok=True)

# --- pinned font (byte-reproducible across platforms) ---
FONT_DIR = "fonts"
FONT_TAG = "Sans2.004"   # notofonts/noto-cjk release tag; SIL OFL 1.1
FONTS = {
 "NotoSansCJKjp-Regular.otf": "68a3fc98800b2a27b371f2fb79991daf3633bd89309d4ffaa6946fd587f375b5",
 "NotoSansCJKjp-Bold.otf":    "e53dcb0dcb2922e45d01aae1ebd2f382bb81d4229b18b6b883bd170678af1f76",
}
def ensure_fonts():
    import hashlib, urllib.request
    os.makedirs(FONT_DIR, exist_ok=True)
    for name, sha in FONTS.items():
        path = os.path.join(FONT_DIR, name)
        if not os.path.exists(path):
            url = f"https://raw.githubusercontent.com/notofonts/noto-cjk/{FONT_TAG}/Sans/OTF/Japanese/{name}"
            print(f"downloading {name} (~16 MB, one time)...")
            urllib.request.urlretrieve(url, path)
        got = hashlib.sha256(open(path, "rb").read()).hexdigest()
        if got != sha:
            raise SystemExit(f"font checksum mismatch for {name}: {got}\ndelete {path} and re-run")
ensure_fonts()

def jp(bold, size):
    name = "NotoSansCJKjp-Bold.otf" if bold else "NotoSansCJKjp-Regular.otf"
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

PX = lambda pt: round(pt*300/72)   # 28→117, 16→67, 14→58, 10.5→44, 7.5→31
F = {"title":jp(True,PX(28)), "large":jp(True,PX(16)), "large14":jp(False,PX(14)),
     "body":jp(False,PX(10.5)), "bodyb":jp(True,PX(10.5)), "fine":jp(False,PX(7.5)),
     "u9":jp(False,PX(9)), "u11":jp(True,PX(11))}

INV = {
 "A": dict(counterparty="株式会社アオバ物流", invoice_no="INV-2026-0630-018",
      issue="2026年6月30日", issue_iso="2026-06-30", due="2026年7月31日", due_iso="2026-07-31",
      subtotal=458000, tax=45800, total=503800,
      bank="みずなら銀行", branch="青葉台支店", acct_type="普通", account="3482716",
      items=[("配送管理システム 保守料（6月分）",1,320000,320000),("追加開発作業",23,6000,138000)]),
 "B": dict(counterparty="有限会社ミナト設計", invoice_no="INV-2026-0630-024",
      issue="2026年6月28日", issue_iso="2026-06-28", due="2026年7月31日", due_iso="2026-07-31",
      subtotal=1237500, tax=123750, total=1361250,
      bank="ほしかげ信用金庫", branch="本店営業部", acct_type="当座", account="0091553",
      items=[("CADデータ変換サービス",1500,750,1125000),("図面レビュー支援",15,7500,112500)]),
}
ISSUER = dict(name="クレハ電装株式会社", addr="東京都品川区南大井 6-16-2", tel="03-6845-2217", reg="T7-0113-4589-2201")
yen = lambda v: "¥{:,}".format(v)

def render_invoice(inst):
    d0 = INV[inst]
    img = Image.new('RGB',(W,H),'white'); d = ImageDraw.Draw(img)
    # title (28pt)
    t="御 請 求 書"; w=d.textlength(t,font=F["title"])
    d.text(((W-w)/2, 240), t, font=F["title"], fill=(10,10,10))
    d.line([(W-w)/2-40, 240+PX(28)+24, (W+w)/2+40, 240+PX(28)+24], fill=(10,10,10), width=4)
    # right: issuer block (unscored) + tel (fine, scored)
    rx=W-M-880; y=560
    d.text((rx,y), ISSUER["name"], font=F["u11"], fill=(20,20,20)); y+=PX(11)+18
    d.text((rx,y), ISSUER["addr"], font=F["u9"], fill=(60,60,60)); y+=PX(9)+14
    d.text((rx,y), "TEL: "+ISSUER["tel"], font=F["fine"], fill=(60,60,60)); y+=PX(7.5)+12
    d.text((rx,y), "登録番号: "+ISSUER["reg"], font=F["fine"], fill=(60,60,60))
    # left: counterparty (body) + invoice meta
    y=560
    d.text((M,y), d0["counterparty"]+" 御中", font=F["bodyb"], fill=(10,10,10)); y+=PX(10.5)+56
    d.text((M,y), "下記の通りご請求申し上げます。", font=F["u9"], fill=(60,60,60))
    y=560+PX(10.5)+150
    d.text((M,y), "請求書番号: ", font=F["u9"], fill=(60,60,60))
    d.text((M+d.textlength("請求書番号: ",font=F["u9"]), y-6), d0["invoice_no"], font=F["large14"], fill=(10,10,10)); y+=PX(14)+26
    d.text((M,y), "発行日: "+d0["issue"], font=F["body"], fill=(10,10,10)); y+=PX(10.5)+22
    d.text((M,y), "お支払期限: "+d0["due"], font=F["body"], fill=(10,10,10))
    # amount box (16pt bold)
    by=1140
    d.rectangle([M,by,M+1250,by+170], outline=(10,10,10), width=4)
    d.text((M+40,by+50), "御請求金額（税込）", font=F["bodyb"], fill=(10,10,10))
    tv=yen(d0["total"]); d.text((M+1250-60-d.textlength(tv,font=F["large"]), by+46), tv, font=F["large"], fill=(10,10,10))
    # items table
    ty=1480; cols=[M, M+1200, M+1500, M+1830, W-M]
    d.rectangle([cols[0],ty,cols[-1],ty+70], fill=(235,235,238), outline=(120,120,120), width=2)
    for cx,label in zip(cols,["品目・内容","数量","単価","金額"]):
        d.text((cx+24,ty+16), label, font=F["u9"], fill=(30,30,30))
    ry=ty+70
    for name,q,u,amt in d0["items"]:
        d.rectangle([cols[0],ry,cols[-1],ry+78], outline=(170,170,170), width=1)
        d.text((cols[0]+24,ry+18), name, font=F["body"], fill=(20,20,20))
        for j,v in enumerate(["{:,}".format(q),"{:,}".format(u),"{:,}".format(amt)]):
            right = cols[j+2]-24   # value j lives in cols[j+1]..cols[j+2]
            d.text((right-d.textlength(v,font=F["body"]), ry+18), v, font=F["body"], fill=(20,20,20))
        ry+=78
    for x in cols: d.line([x,ty,x,ry], fill=(120,120,120), width=1)
    # totals (body 10.5)
    sy=ry+60; lx=cols[2]
    for label,val in [("小計", d0["subtotal"]), ("消費税（10%）", d0["tax"]), ("合計（税込）", d0["total"])]:
        d.text((lx, sy), label, font=F["body"], fill=(20,20,20))
        v=yen(val); d.text((cols[-1]-24-d.textlength(v,font=F["body"]), sy), v, font=F["body"], fill=(20,20,20))
        sy+=PX(10.5)+26
    # bank block (fine 7.5)
    by2=2560
    d.text((M,by2), "お振込先", font=F["bodyb"], fill=(10,10,10)); y=by2+PX(10.5)+26
    for line in [d0["bank"]+"　"+d0["branch"], d0["acct_type"]+"　口座番号 "+d0["account"], "口座名義　クレハデンソウ（カ"]:
        d.text((M,y), line, font=F["fine"], fill=(20,20,20)); y+=PX(7.5)+18
    d.text((M, y+30), "※お振込手数料は貴社にてご負担願います。", font=F["fine"], fill=(90,90,90))
    d.line([M,H-180,W-M,H-180], fill=(190,190,190), width=2)
    d.text((M,H-150), ISSUER["name"], font=F["fine"], fill=(140,140,140))
    return img

def render_receipt():
    img=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(img); cx=W//2
    t="領　収　書"; d.text((cx-d.textlength(t,font=F["title"])/2, 380), t, font=F["title"], fill=(10,10,10))
    y=700
    d.text((M+200,y), "株式会社アオバ物流 御中", font=F["bodyb"], fill=(10,10,10)); y+=160
    d.rectangle([M+200,y,W-M-200,y+180], outline=(10,10,10), width=4)
    d.text((M+240,y+56), "金額", font=F["bodyb"], fill=(10,10,10))
    v="¥12,340 −"; d.text((W-M-260-d.textlength(v,font=F["large"]), y+50), v, font=F["large"], fill=(10,10,10))
    y+=280
    for line in ["但し　配送資材代として","上記正に領収いたしました。","発行日: 2026年7月2日"]:
        d.text((M+200,y), line, font=F["body"], fill=(20,20,20)); y+=90
    d.rectangle([W-M-560,y+80,W-M-200,y+340], outline=(150,150,150), width=2)
    d.text((W-M-520,y+100), "収入\n印紙", font=F["u9"], fill=(120,120,120))
    d.text((M+200,H-700), "クレハ電装株式会社", font=F["u11"], fill=(20,20,20))
    d.text((M+200,H-620), "東京都品川区南大井 6-16-2　TEL: 03-6845-2217", font=F["fine"], fill=(60,60,60))
    return img

def render_card():
    img=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(img)
    x0,y0,x1,y1 = W//2-1000, H//2-620, W//2+1000, H//2+620
    d.rectangle([x0,y0,x1,y1], outline=(90,90,90), width=3)
    d.text((x0+90,y0+120), "クレハ電装株式会社", font=F["u11"], fill=(30,30,60))
    d.text((x0+90,y0+300), "営業部 課長", font=F["u9"], fill=(60,60,60))
    d.text((x0+90,y0+400), "柏木　伸也", font=jp(True,PX(20)), fill=(10,10,10))
    d.text((x0+90,y1-360), "〒140-0013 東京都品川区南大井 6-16-2", font=F["fine"], fill=(60,60,60))
    d.text((x0+90,y1-290), "TEL: 03-6845-2217　MAIL: kashiwagi@kureha-densou.example", font=F["fine"], fill=(60,60,60))
    return img

def render_minutes():
    img=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(img)
    d.text((M,240), "生産管理システム更改 定例会議 議事録", font=jp(True,PX(18)), fill=(10,10,10))
    y=460
    for m in ["日時：2026年7月3日（金）10:00〜11:30","場所：本社 第2会議室","出席者：柏木、青山、水島、戸田"]:
        d.text((M,y), m, font=F["u9"], fill=(60,60,60)); y+=76
    y+=60
    paras=[("議題1：移行スケジュールの確認","現行システムからのデータ移行は8月第2週に実施することで合意した。移行リハーサルを7月下旬に2回実施し、切替当日の手順書は水島が7月18日までに作成する。"),
           ("議題2：在庫マスタの整備","品目コードの重複が42件確認された。重複解消の方針として、新コード体系への一本化を採用する。対応表の作成は青山が担当し、期限は7月24日とする。"),
           ("議題3：帳票出力の要件","現場から要望のあった日次出荷一覧は標準機能で対応可能と判明。カスタム帳票は3種類に絞り込み、見積を戸田が取得する。")]
    def wrap(t,f,mx):
        lines=[];c=""
        for ch in t:
            if d.textlength(c+ch,font=f)>mx: lines.append(c);c=ch
            else: c+=ch
        lines.append(c); return lines
    for h,body in paras:
        d.text((M,y), h, font=F["bodyb"], fill=(15,15,60)); y+=PX(10.5)+30
        for ln in wrap(body,F["body"],W-2*M):
            d.text((M,y), ln, font=F["body"], fill=(25,25,25)); y+=PX(10.5)+22
        y+=54
    return img

def degrade(img,dpi):
    if dpi>=300: return img.copy()
    s=dpi/300
    small=img.resize((max(1,round(W*s)),max(1,round(H*s))), Image.LANCZOS)
    return small.resize((W,H), Image.BILINEAR)

# ---- generate ----
masters = {}
for inst in ("A","B"): masters[f"t1_{inst}"]=render_invoice(inst)
masters["t2_invoice"]=masters["t1_A"]
masters["t2_receipt"]=render_receipt(); masters["t2_card"]=render_card(); masters["t2_minutes"]=render_minutes()

count=0
for key,img in masters.items():
    if key=="t2_invoice": continue  # reuse t1_A files logically; still emit for T2 naming clarity
for key in ["t1_A","t1_B","t2_invoice","t2_receipt","t2_card","t2_minutes"]:
    img=masters[key]
    for i,dpi in enumerate(LADDER):
        degrade(img,dpi).save(f"{OUT}/{key}_L{i}_{dpi}dpi.png"); count+=1
print("materials:",count,"files")

# ---- ground truth ----
def gtfields(d0):
    return {
     "doc_title":{"printed":"御 請 求 書","norm":"御請求書","tier":"title"},
     "total":{"printed":yen(d0["total"])+" −","norm":str(d0["total"]),"tier":"large"},
     "invoice_no":{"printed":d0["invoice_no"],"norm":d0["invoice_no"],"tier":"large"},
     "counterparty_name":{"printed":d0["counterparty"],"norm":d0["counterparty"],"tier":"body"},
     "issue_date":{"printed":d0["issue"],"norm":d0["issue_iso"],"tier":"body"},
     "due_date":{"printed":d0["due"],"norm":d0["due_iso"],"tier":"body"},
     "subtotal":{"printed":yen(d0["subtotal"]),"norm":str(d0["subtotal"]),"tier":"body"},
     "tax":{"printed":yen(d0["tax"]),"norm":str(d0["tax"]),"tier":"body"},
     "bank_name":{"printed":d0["bank"],"norm":d0["bank"],"tier":"fine"},
     "bank_branch":{"printed":d0["branch"],"norm":d0["branch"],"tier":"fine"},
     "account_number":{"printed":d0["account"],"norm":d0["account"],"tier":"fine"},
     "issuer_tel":{"printed":ISSUER["tel"],"norm":ISSUER["tel"].replace("-",""),"tier":"fine"},
    }
gt={"canvas":[W,H],"ladder_dpi":LADDER,
    "t1":{k:gtfields(INV[k]) for k in ("A","B")},
    "t2":{"t2_invoice":"invoice","t2_receipt":"receipt","t2_card":"business_card","t2_minutes":"meeting_minutes"}}
json.dump(gt,open("ground_truth.json","w"),ensure_ascii=False,indent=1)
# ---- self-check (ladder-derived; catches stale/missing files) ----
import glob
DOCS=["t1_A","t1_B","t2_invoice","t2_receipt","t2_card","t2_minutes"]
expected={f"{k}_L{i}_{dpi}dpi.png" for k in DOCS for i,dpi in enumerate(LADDER)}
present={os.path.basename(p) for p in glob.glob(f"{OUT}/*.png")}
missing=expected-present
assert not missing, f"missing materials: {sorted(missing)[:3]}"
extras=present-expected
if extras:
    print(f"note: {len(extras)} unexpected file(s) in {OUT}/ (stale from an older ladder?), e.g. {sorted(extras)[:3]}")
print(f"self-check OK: {len(expected)}/{len(expected)} materials present; ground_truth.json written")
