#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hanko Occlusion — report. Derived metrics per design sheet §5:
frontier / chromatic gain / inference rate / collateral / stamp read rate."""
import json, collections, csv

BASE12 = {"doc_title","total","invoice_no","counterparty_name","issue_date","due_date",
          "subtotal","tax","bank_name","bank_branch","account_number","issuer_tel"}
TARGET = {"N":"issuer_name","M":"subtotal"}
LMAX = 5

acc  = collections.defaultdict(lambda: [0,0])   # (model,inst,L,'target'|'base'|'stamp') -> [hit,n]
for line in open("hanko_scores.jsonl", encoding="utf-8"):
    r = json.loads(line)
    if r.get("cls") in ("job_failed","bad_json") or "field" not in r: continue
    m, inst, L, f, c = r["model"], r["doc"], r["L"], r["field"], r["cls"]
    tg = TARGET[inst.split("_")[1]]
    hit = 1 if c in ("correct","near") else 0
    if f == tg:            k=(m,inst,L,"target")
    elif f in BASE12:      k=(m,inst,L,"base")
    elif f == "stamp_text":k=(m,inst,L,"stamp"); hit = 1 if c=="correct" else 0
    else: continue
    acc[k][0]+=hit; acc[k][1]+=1

def rate(m,inst,L,kind):
    h,n = acc.get((m,inst,L,kind),[0,0]); return (h/n if n else None), n

models = sorted({k[0] for k in acc})
rows=[]
for m in models:
    row={"model":m}
    for inst in ("A_N","B_N","A_M","B_M"):
        fr="×"
        for L in range(LMAX+1):
            v,_=rate(m,inst,L,"target")
            if v is not None and v>=0.9: fr=f"L{L}"
            elif v is not None: break
        row[f"frontier_{inst}"]=fr
    gains=[]
    for L in range(1,LMAX+1):
        a,_=rate(m,"A_N",L,"target"); b,_=rate(m,"B_N",L,"target")
        if a is not None and b is not None: gains.append(a-b)
    row["chromatic_gain"]=round(sum(gains)/len(gains),2) if gains else ""
    inf=[rate(m,"B_M",L,"target") for L in (4,5)]
    hs=[v for v,n in inf if v is not None]
    row["inference_rate"]=round(sum(hs)/len(hs),2) if hs else ""
    worst=0.0
    for inst in ("A_N","B_N","A_M","B_M"):
        b0,_=rate(m,inst,0,"base")
        if b0 is None: continue
        for L in range(1,LMAX+1):
            bl,_=rate(m,inst,L,"base")
            if bl is not None: worst=max(worst,b0-bl)
    row["collateral_worst_drop"]=round(worst,2)
    sh=sn=0
    for k,(h,n) in acc.items():
        if k[0]==m and k[3]=="stamp": sh+=h; sn+=n
    row["stamp_read_rate"]=round(sh/sn,2) if sn else ""
    rows.append(row)

cols=["model","frontier_A_N","frontier_B_N","frontier_A_M","frontier_B_M",
      "chromatic_gain","inference_rate","collateral_worst_drop","stamp_read_rate"]
with open("hanko_summary.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows)
with open("hanko_results_table.md","w") as f:
    f.write("| "+" | ".join(cols)+" |\n|"+"---|"*len(cols)+"\n")
    for r in rows: f.write("| "+" | ".join(str(r[c]) for c in cols)+" |\n")
print(f"report: {len(rows)} models -> hanko_summary.csv / hanko_results_table.md")
try:
    import numpy as np, matplotlib
    matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,4,figsize=(16,max(2,0.35*len(models))+1.2),sharey=True)
    for ax,inst in zip(axes,("A_N","B_N","A_M","B_M")):
        Z=np.array([[(rate(m,inst,L,"target")[0] if rate(m,inst,L,"target")[0] is not None else np.nan)
                     for L in range(LMAX+1)] for m in models])
        ax.imshow(1-Z,vmin=0,vmax=1,cmap="Reds",aspect="auto")
        ax.set_title(inst); ax.set_xticks(range(LMAX+1)); ax.set_xticklabels([f"L{i}" for i in range(LMAX+1)])
    axes[0].set_yticks(range(len(models))); axes[0].set_yticklabels(models,fontsize=6)
    fig.suptitle("target-field error rate (white=read, red=lost)"); fig.tight_layout()
    fig.savefig("hanko_heatmap.png",dpi=150); print("hanko_heatmap.png written")
except Exception as e:
    print("heatmap skipped:",e)
