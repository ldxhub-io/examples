# -*- coding: utf-8 -*-
"""Hanko Occlusion v2 — material generator (deterministic).
Faithful diff of the v1 generator. Ladder, 2x2, stamp mechanics, fonts, canvas,
targets, approach directions, and all v1 assertions are unchanged. Exactly three
deltas, each closing a stated limitation of v1 (README "future version" notes):

v2Δ1  Mixed tax rate 8%/10% (route fingerprint). v1's round 10% collapsed the two
      derivation routes: total−tax and total÷1.1 gave the same subtotal. v2 keeps the
      printed arithmetic subtotal = total − tax = sum of per-rate bases, while
      total ÷ 1.1 = 1,235,000 — an EXACT integer that equals no printed number. A
      model that derives via the flat-10% prior now signs its route in the output.
      The per-rate breakdown box (区分記載) sits bottom-left, geometrically protected,
      so the totals block keeps v1's shape and the M-target ladder stays comparable.
      Subtotal itself is kept at v1's value (1,237,500) on purpose: same digit count,
      same rendering, longitudinal comparability of the M cell.

v2Δ2  Fictional seal text 納検済印 (web 0-hit, checked 2026-07-18). v1's 検収済印 is a
      real common phrase, so reading couldn't be separated from memory. Bonus probe:
      the real phrase 検収済印 is now the category-mode trap — a model completing from
      prior instead of reading will emit it, and the scorer's "other" class catches it.

v2Δ3  Fictional branch name 月芝支店 (web 0-hit, checked 2026-07-18; 芝支店/月隈支店/
      初芝支店 exist, 月芝支店 does not). v1's 本店営業部 was the category mode and
      produced six coin-flip "correct" cells at L0.

Everything else — redundancy purge, 社判スペース, approach directions, solid-pad
stamp, pixel occlusion checks — is verbatim v1. 300 dpi only."""
from PIL import Image, ImageDraw, ImageFont
import json, os, hashlib, math
import numpy as np

W,H = 2480,3508
M = 200
OVERLAPS = [0,20,40,60,80,100]            # L0..L5 (%)
OUT = "materials_hanko"; os.makedirs(OUT, exist_ok=True)

FONT_DIR="fonts"; FONT_TAG="Sans2.004"
FONTS={"NotoSansCJKjp-Regular.otf":"68a3fc98800b2a27b371f2fb79991daf3633bd89309d4ffaa6946fd587f375b5",
       "NotoSansCJKjp-Bold.otf":"e53dcb0dcb2922e45d01aae1ebd2f382bb81d4229b18b6b883bd170678af1f76"}
def ensure_fonts():
    import urllib.request
    os.makedirs(FONT_DIR, exist_ok=True)
    for name,sha in FONTS.items():
        path=os.path.join(FONT_DIR,name)
        if not os.path.exists(path):
            url=f"https://raw.githubusercontent.com/notofonts/noto-cjk/{FONT_TAG}/Sans/OTF/Japanese/{name}"
            print(f"downloading {name} (~16 MB, one time)..."); urllib.request.urlretrieve(url,path)
        got=hashlib.sha256(open(path,"rb").read()).hexdigest()
        if got!=sha: raise SystemExit(f"font checksum mismatch for {name}: {got}\ndelete {path} and re-run")
ensure_fonts()
def jp(bold,size):
    return ImageFont.truetype(os.path.join(FONT_DIR,"NotoSansCJKjp-Bold.otf" if bold else "NotoSansCJKjp-Regular.otf"),size)
PX=lambda pt: round(pt*300/72)
F={"title":jp(True,PX(28)),"large":jp(True,PX(16)),"large14":jp(False,PX(14)),
   "body":jp(False,PX(10.5)),"bodyb":jp(True,PX(10.5)),"fine":jp(False,PX(7.5)),
   "u9":jp(False,PX(9)),"u11":jp(True,PX(11))}

# v2Δ3: fictional branch. v2Δ1: per-rate bases/taxes; items carry their rate.
D=dict(counterparty="有限会社ミナト設計", invoice_no="INV-2026-1030-047",
       issue="2026年10月30日", issue_iso="2026-10-30", due="2026年11月30日", due_iso="2026-11-30",
       sub8=137500, tax8=11000, sub10=1100000, tax10=110000,
       subtotal=1237500, tax=121000, total=1358500,
       bank="ほしかげ信用金庫", branch="月芝支店", acct_type="当座", account="0091553",
       items=[("CADデータ変換サービス",1200,750,900000,10),
              ("図面レビュー支援",25,8000,200000,10),
              ("オフィス用飲料水（※）",550,250,137500,8)])
ISSUER=dict(name="クレハ電装株式会社", addr="東京都品川区南大井 6-16-2", tel="03-6845-2217", reg="T7-0113-4589-2201")
yen=lambda v:"¥{:,}".format(v)
TRADE="クレハ電装"
STAMP_GAP=300                              # 社判スペース: reserved below issuer name

# ---- v2Δ1: arithmetic freeze + route-fingerprint separation ----------------
assert D["sub8"]+D["sub10"]==D["subtotal"] and D["tax8"]+D["tax10"]==D["tax"]
assert D["sub8"]*8%100==0  and D["tax8"]*100==D["sub8"]*8      # 8% exact, no rounding
assert D["sub10"]%10==0    and D["tax10"]*10==D["sub10"]       # 10% exact, no rounding
assert D["subtotal"]+D["tax"]==D["total"]
assert sum(a for n,q,u,a,r in D["items"] if r==10)==D["sub10"]
assert sum(a for n,q,u,a,r in D["items"] if r==8) ==D["sub8"]
assert all(q*u==a for n,q,u,a,r in D["items"])
# the ÷1.1 route lands on an exact integer that is on no printed line:
assert D["total"]*10%11==0 and D["total"]*10//11==1235000
NUMS={D[k] for k in ("subtotal","tax","total","sub8","sub10","tax8","tax10")} \
     |{a for n,q,u,a,r in D["items"]}
for div in (1.1,1.08):                    # flat-rate heuristics a model might apply
    qv=D["total"]/div
    for g in (1,10,100,1000,10000):       # every plausible rounding granularity
        for f in (round,math.floor,math.ceil):
            v=int(f(qv/g))*g
            assert v not in NUMS,(div,g,f.__name__,v)
print("route fingerprint frozen: total/1.1 =",D["total"]*10//11,"(exact, != any printed number)")

def render_base():
    img=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(img)
    t="御 請 求 書"; w=d.textlength(t,font=F["title"])
    d.text(((W-w)/2,240),t,font=F["title"],fill=(10,10,10))
    d.line([(W-w)/2-40,240+PX(28)+24,(W+w)/2+40,240+PX(28)+24],fill=(10,10,10),width=4)
    rx=W-M-880; y=560
    d.text((rx,y),ISSUER["name"],font=F["u11"],fill=(20,20,20))
    bbox_N=d.textbbox((rx,y),TRADE,font=F["u11"])
    y+=PX(11)+18+STAMP_GAP
    d.text((rx,y),ISSUER["addr"],font=F["u9"],fill=(60,60,60))
    bbox_addr=d.textbbox((rx,y),ISSUER["addr"],font=F["u9"]); y+=PX(9)+14
    d.text((rx,y),"TEL: "+ISSUER["tel"],font=F["fine"],fill=(60,60,60))
    bbox_tel=d.textbbox((rx,y),"TEL: "+ISSUER["tel"],font=F["fine"]); y+=PX(7.5)+12
    d.text((rx,y),"登録番号: "+ISSUER["reg"],font=F["fine"],fill=(60,60,60))
    y=560
    d.text((M,y),D["counterparty"]+" 御中",font=F["bodyb"],fill=(10,10,10)); y+=PX(10.5)+56
    d.text((M,y),"下記の通りご請求申し上げます。",font=F["u9"],fill=(60,60,60))
    y=560+PX(10.5)+150
    d.text((M,y),"請求書番号: ",font=F["u9"],fill=(60,60,60))
    d.text((M+d.textlength("請求書番号: ",font=F["u9"]),y-6),D["invoice_no"],font=F["large14"],fill=(10,10,10)); y+=PX(14)+26
    d.text((M,y),"発行日: "+D["issue"],font=F["body"],fill=(10,10,10)); y+=PX(10.5)+22
    d.text((M,y),"お支払期限: "+D["due"],font=F["body"],fill=(10,10,10))
    by=1140
    d.rectangle([M,by,M+1250,by+170],outline=(10,10,10),width=4)
    d.text((M+40,by+50),"御請求金額（税込）",font=F["bodyb"],fill=(10,10,10))
    tv=yen(D["total"]); d.text((M+1250-60-d.textlength(tv,font=F["large"]),by+46),tv,font=F["large"],fill=(10,10,10))
    ty=1480; cols=[M,M+1200,M+1500,M+1830,W-M]
    d.rectangle([cols[0],ty,cols[-1],ty+70],fill=(235,235,238),outline=(120,120,120),width=2)
    for cx,label in zip(cols,["品目・内容","数量","単価","金額"]):
        d.text((cx+24,ty+16),label,font=F["u9"],fill=(30,30,30))
    ry=ty+70
    for name,q,u,amt,rate in D["items"]:                       # v2Δ1: rate carried, ※ in name
        d.rectangle([cols[0],ry,cols[-1],ry+78],outline=(170,170,170),width=1)
        d.text((cols[0]+24,ry+18),name,font=F["body"],fill=(20,20,20))
        for j,v in enumerate(["{:,}".format(q),"{:,}".format(u),"{:,}".format(amt)]):
            right=cols[j+2]-24
            d.text((right-d.textlength(v,font=F["body"]),ry+18),v,font=F["body"],fill=(20,20,20))
        ry+=78
    for x in cols: d.line([x,ty,x,ry],fill=(120,120,120),width=1)
    sy=ry+60; lx=cols[2]; bbox_M=bbox_tax=bbox_total=None
    # v2Δ1: 税率区分別内訳 — bottom-left, same vertical band as the totals block,
    # geometrically far from both stamp tracks; protected (guard-asserted below).
    ky=sy; kb=None
    for i,line in enumerate(["（税率区分別内訳　※印は軽減税率対象品目）",
                             f"8%対象（税抜） {yen(D['sub8'])}　消費税 {yen(D['tax8'])}",
                             f"10%対象（税抜） {yen(D['sub10'])}　消費税 {yen(D['tax10'])}"]):
        d.text((M,ky),line,font=F["u9"],fill=(60,60,60) if i==0 else (20,20,20))
        bb=d.textbbox((M,ky),line,font=F["u9"])
        kb=list(bb) if kb is None else [min(kb[0],bb[0]),min(kb[1],bb[1]),max(kb[2],bb[2]),max(kb[3],bb[3])]
        ky+=PX(9)+14
    bbox_kubun=kb
    for label,val in [("小計",D["subtotal"]),("消費税合計",D["tax"]),("合計（税込）",D["total"])]:  # v2Δ1: label
        d.text((lx,sy),label,font=F["body"],fill=(20,20,20))
        v=yen(val); vx=cols[-1]-24-d.textlength(v,font=F["body"])
        d.text((vx,sy),v,font=F["body"],fill=(20,20,20))
        bb=d.textbbox((vx,sy),v,font=F["body"])
        if label=="小計": bbox_M=bb
        elif label.startswith("消費税"): bbox_tax=bb
        else: bbox_total=bb
        sy+=PX(10.5)+26
    by2=2560
    d.text((M,by2),"お振込先",font=F["bodyb"],fill=(10,10,10)); y=by2+PX(10.5)+26
    for line in [D["bank"]+"　"+D["branch"], D["acct_type"]+"　口座番号 "+D["account"]]:
        d.text((M,y),line,font=F["fine"],fill=(20,20,20)); y+=PX(7.5)+18
    d.text((M,y+30),"※お振込手数料は貴社にてご負担願います。",font=F["fine"],fill=(90,90,90))
    d.line([M,H-180,W-M,H-180],fill=(190,190,190),width=2)
    boxes={k:[int(v) for v in bb] for k,bb in
           dict(N=bbox_N,M=bbox_M,addr=bbox_addr,tel=bbox_tel,tax=bbox_tax,total=bbox_total,
                kubun=bbox_kubun).items()}
    return img, boxes

# --- solid-pad seal (v2Δ2: fictional text, same 2x2 right-to-left layout) ---
S=248; BW=8; RED=(199,62,58); DARK=(148,36,32); SEAL="納検済印"
assert len(SEAL)==4 and len(set(SEAL))==4
def stamp_arrays():
    """Solid ink pad: alpha=1 everywhere in the square; glyphs+border as darker red decoration."""
    g=Image.new("L",(S,S),0); dd=ImageDraw.Draw(g)
    dd.rectangle([0,0,S-1,S-1],outline=255,width=BW)
    f=jp(True,96); half=S//2
    for ch,(qx,qy) in {SEAL[0]:(half,0),SEAL[1]:(half,half),SEAL[2]:(0,0),SEAL[3]:(0,half)}.items():
        bb=dd.textbbox((0,0),ch,font=f)
        dd.text((qx+(half-(bb[2]-bb[0]))//2-bb[0], qy+(half-(bb[3]-bb[1]))//2-bb[1]),ch,font=f,fill=255)
    gl=np.asarray(g,dtype=np.float64)/255.0
    color=np.empty((S,S,3),dtype=np.float64)
    color[...]=np.array(RED,dtype=np.float64)
    color=color*(1-gl[...,None])+np.array(DARK,dtype=np.float64)*gl[...,None]
    return color
COLOR=stamp_arrays()

def composite(img,top,left,opacity):
    base=np.asarray(img,dtype=np.float64).copy()
    y0,x0=max(0,top),max(0,left); y1,x1=min(H,top+S),min(W,left+S)
    C=COLOR[y0-top:y1-top, x0-left:x1-left]
    reg=base[y0:y1,x0:x1,:]
    if opacity>=1.0: out=C                                  # true occlusion
    else:            out=reg*(1-opacity*(1-C/255.0))        # translucent 朱: dark ink stays dark
    base[y0:y1,x0:x1,:]=out
    return Image.fromarray(np.rint(base).astype(np.uint8))

def place(bbox,frac,direction):
    bx0,by0,bx1,by1=bbox; bw,bh=bx1-bx0,by1-by0
    left=round((bx0+bx1)/2 - S/2)
    if direction=="below":                                  # stamp rises from below into the text
        top = by1+30 if frac==0 else by1-round(frac*bh)
    else:                                                   # "above": stamp descends into the text
        top = by0-S-30 if frac==0 else by0-S+round(frac*bh)
    ih=max(0,min(by1,top+S)-max(by0,top)); iw=max(0,min(bx1,left+S)-max(bx0,left))
    return top,left,(ih*iw)/(bw*bh)

DIRECTION={"N":"below","M":"above"}

base_img,BB=render_base()
meta={"canvas":[W,H],"overlap_ladder_pct":OVERLAPS,
      "stamp":{"size":S,"border":BW,"rgb":RED,"glyph_rgb":DARK,"text":SEAL,"pad":"solid"},
      "layout_deltas":["footer issuer line removed","口座名義 line removed",
                       f"{STAMP_GAP}px 社判スペース inserted below issuer name",
                       "v2: third item row (reduced-rate ※) added",
                       "v2: 税率区分別内訳 box added bottom-left (protected)",
                       "v2: 消費税（10%） label → 消費税合計"],
      "v2_deltas":{"mixed_tax":"8%/10%; total/1.1 = 1,235,000 exact and off-document (route fingerprint)",
                   "seal":"納検済印 — fictional (web 0-hit 2026-07-18); real-phrase trap: 検収済印",
                   "branch":"月芝支店 — fictional (web 0-hit 2026-07-18); v1 branch was the category mode"},
      "tax_design":{"sub8":D["sub8"],"tax8":D["tax8"],"sub10":D["sub10"],"tax10":D["tax10"],
                    "total_div_1_1":D["total"]*10//11},
      "approach":DIRECTION,
      "targets":{"N":{"field":"issuer_name","span":TRADE,"bbox":BB["N"]},
                 "M":{"field":"subtotal","bbox":BB["M"]}},
      "protected":{k:BB[k] for k in ("addr","tel","tax","total","kubun")},
      "materials":{}}
def isect(r1,r2):
    return max(0,min(r1[2],r2[2])-max(r1[0],r2[0]))*max(0,min(r1[3],r2[3])-max(r1[1],r2[1]))
def darkest_in(img,bb):
    a=np.asarray(img.convert("L"))
    return int(a[bb[1]:bb[3],bb[0]:bb[2]].min())
count=0
for op_key,opacity in [("A",0.80),("B",1.00)]:
    for tg in ("N","M"):
        for li,pct in enumerate(OVERLAPS):
            top,left,ach=place(BB[tg],pct/100.0,DIRECTION[tg])
            img=composite(base_img,top,left,opacity)
            name=f"hanko_{op_key}_{tg}_L{li}.png"; img.save(f"{OUT}/{name}"); count+=1
            rect=[left,top,left+S,top+S]
            meta["materials"][name]=dict(opacity=opacity,target=tg,L=li,nominal_pct=pct,
                                         achieved_pct=round(ach*100,2),stamp_rect=rect)
            assert abs(ach*100-pct)<=2.0,(name,ach*100)
            if pct==0: assert ach==0.0
            # 検収: 巻き添え禁止 — Nはaddr/tel、Mはtax/total(導出経路)。区分内訳は両ターゲットで保護。
            guard = ("addr","tel","kubun") if tg=="N" else ("tax","total","kubun")
            for pk in guard: assert isect(rect,BB[pk])==0,(name,pk)
            # v2 addition: the README's pixel claim, executed on the emitted file.
            # Opaque L5: no dark ink survives in the target box (information destroyed).
            # Translucent L5: the black ink underneath is still dark (information present).
            if pct==100:
                dk=darkest_in(img,BB[tg])
                if opacity>=1.0: assert dk>=60,(name,"dark ink survived opaque seal",dk)
                else:            assert dk<=40,(name,"ink lost under translucent seal",dk)
print("materials:",count,"files")

GTF={
 "doc_title":{"printed":"御 請 求 書","norm":"御請求書","tier":"title"},
 "total":{"printed":yen(D["total"])+" −","norm":str(D["total"]),"tier":"large"},
 "invoice_no":{"printed":D["invoice_no"],"norm":D["invoice_no"],"tier":"large"},
 "counterparty_name":{"printed":D["counterparty"],"norm":D["counterparty"],"tier":"body"},
 "issue_date":{"printed":D["issue"],"norm":D["issue_iso"],"tier":"body"},
 "due_date":{"printed":D["due"],"norm":D["due_iso"],"tier":"body"},
 "subtotal":{"printed":yen(D["subtotal"]),"norm":str(D["subtotal"]),"tier":"body"},
 "tax":{"printed":yen(D["tax"]),"norm":str(D["tax"]),"tier":"body"},
 "bank_name":{"printed":D["bank"],"norm":D["bank"],"tier":"fine"},
 "bank_branch":{"printed":D["branch"],"norm":D["branch"],"tier":"fine"},
 "account_number":{"printed":D["account"],"norm":D["account"],"tier":"fine"},
 "issuer_tel":{"printed":ISSUER["tel"],"norm":ISSUER["tel"].replace("-",""),"tier":"fine"},
 "issuer_name":{"printed":ISSUER["name"],"norm":ISSUER["name"],"tier":"body"},
}
json.dump({"fields":GTF,"stamp_text":SEAL,"meta":meta},
          open("hanko_ground_truth.json","w"),ensure_ascii=False,indent=1)
print("hanko_ground_truth.json written")
