#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legibility Frontier — aggregation + heatmap + README table + paste-back SUMMARY."""
import csv, json, os
from collections import defaultdict

LADDER = [300,150,100,70,50,35,25]
TIERS = ["title","large","body","fine"]
DEFAULT_ORDER = [
 "openai/gpt-5.6-sol@high",
 "openai/gpt-5.6-sol@low",
 "openai/gpt-5.6-terra@high",
 "openai/gpt-5.6-terra@low",
 "openai/gpt-5.6-luna@high",
 "openai/gpt-5.6-luna@low",
 "openai/gpt-5.5@high",
 "openai/gpt-5.5@low",
 "openai/gpt-5.4@high",
 "openai/gpt-5.4-mini@high",
 "azure/gpt-5.6-sol@high",
 "azure/gpt-5.6-sol@low",
 "azure/gpt-5.6-terra@high",
 "azure/gpt-5.6-terra@low",
 "azure/gpt-5.6-luna@high",
 "azure/gpt-5.6-luna@low",
 "azure/gpt-5.4@high",
 "azure/gpt-5.4@low",
 "azure/gpt-5.4-mini@high",
 "azure/gpt-5.4-mini@low",
 "google/gemini-3.5-flash@high",
 "google/gemini-3.5-flash@medium",
 "google/gemini-3.5-flash@low",
 "anthropic/claude-fable-5",
 "anthropic/claude-sonnet-5",
 "anthropic/claude-opus-4-8",
 "bedrock/global.amazon.nova-2-lite-v1:0"
]
MODEL_ORDER = [m.strip() for m in open("model_order.txt")] if os.path.exists("model_order.txt") else DEFAULT_ORDER

def main():
    rows = [json.loads(l) for l in open("scores.jsonl", encoding="utf-8")]
    t1 = [r for r in rows if r["task"]=="t1" and r.get("field")]
    t2 = [r for r in rows if r["task"]=="t2" and r.get("field")]
    present = {r["model"] for r in rows}
    models = [m for m in MODEL_ORDER if m in present] + sorted(present - set(MODEL_ORDER))

    # --- per model×L×tier aggregation ---
    agg = defaultdict(lambda: defaultdict(int))
    for r in t1:
        k = (r["model"], r["L"], r["tier"]); agg[k][r["cls"]] += 1; agg[k]["n"] += 1
    with open("summary.csv","w",newline="") as f:
        w = csv.writer(f); w.writerow(["model","L","dpi","tier","n","correct","near","blank","fabricated","acc","fab_rate"])
        for (m,L,tier),c in sorted(agg.items(), key=lambda x:(models.index(x[0][0]),x[0][1],TIERS.index(x[0][2]))):
            n=c["n"]; acc=(c["correct"]+c["near"])/n; fab=c["fabricated"]/n
            w.writerow([m,L,LADDER[L],tier,n,c["correct"],c["near"],c["blank"],c["fabricated"],f"{acc:.3f}",f"{fab:.3f}"])

    # --- frontier: max L with acc>=0.9 (contiguous from L0) ---
    frontier = {}
    for m in models:
        for tier in TIERS:
            fr = -1
            for L in range(len(LADDER)):
                c = agg.get((m,L,tier))
                if not c or c["n"]==0: break
                if (c["correct"]+c["near"])/c["n"] >= 0.9: fr = L
                else: break
            frontier[(m,tier)] = fr
    with open("frontier.csv","w",newline="") as f:
        w=csv.writer(f); w.writerow(["model"]+TIERS)
        for m in models: w.writerow([m]+[frontier[(m,t)] for t in TIERS])

    # --- T2 ---
    t2agg = defaultdict(lambda: defaultdict(int))
    for r in t2:
        t2agg[(r["model"],r["L"])][r["cls"]] += 1; t2agg[(r["model"],r["L"])]["n"] += 1
    t2model = {m: (sum(t2agg[(m,L)]["correct"] for L in range(7)),
                   sum(t2agg[(m,L)]["n"] for L in range(7))) for m in models}

    # --- heatmap: body-tier fabrication rate ---
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        M = np.full((len(models), len(LADDER)), np.nan)
        for i,m in enumerate(models):
            for L in range(len(LADDER)):
                c = agg.get((m,L,"body"))
                if c and c["n"]: M[i,L] = c["fabricated"]/c["n"]
        fig,ax = plt.subplots(figsize=(9, 0.42*len(models)+1.6))
        im = ax.imshow(M, cmap="Reds", vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(range(len(LADDER))); ax.set_xticklabels([f"L{i}\n{d}dpi" for i,d in enumerate(LADDER)], fontsize=8)
        ax.set_yticks(range(len(models))); ax.set_yticklabels(models, fontsize=7)
        for i in range(len(models)):
            for j in range(len(LADDER)):
                if not np.isnan(M[i,j]): ax.text(j,i,f"{M[i,j]*100:.0f}",ha="center",va="center",fontsize=6,
                                                 color="white" if M[i,j]>0.5 else "black")
        ax.set_title("Body-tier fabrication rate (%) — Japanese invoice, simulated scan dpi")
        fig.colorbar(im, shrink=0.6); fig.tight_layout(); fig.savefig("heatmap.png", dpi=160)
        print("heatmap.png written")
    except ImportError:
        print("matplotlib not installed — skipped heatmap (pip install matplotlib)")

    # --- README table ---
    def frs(m): return " / ".join(("L%d"%frontier[(m,t)]) if frontier[(m,t)]>=0 else "×" for t in TIERS)
    with open("results_table.md","w") as f:
        f.write("| model | frontier (title/large/body/fine) | body fab@L6 | T2 acc |\n|---|---|---|---|\n")
        for m in models:
            c = agg.get((m,6,"body")); fab = f"{c['fabricated']/c['n']*100:.0f}%" if c and c["n"] else "—"
            ok,n = t2model[m]; f.write(f"| {m} | {frs(m)} | {fab} | {ok}/{n} |\n")

    # --- paste-back SUMMARY ---
    print("\n===== LEGIBILITY FRONTIER SUMMARY =====")
    print(f"models={len(models)} t1_records={len(t1)} t2_records={len(t2)}")
    for m in models:
        c = agg.get((m,6,"body")); fab = f"{c['fabricated']/c['n']*100:3.0f}%" if c and c["n"] else "  —"
        ok,n = t2model[m]
        print(f"{m:44s} frontier {frs(m):22s} bodyFab@L6 {fab}  T2 {ok}/{n}")
    print("files: summary.csv frontier.csv results_table.md heatmap.png")

if __name__ == "__main__":
    main()
