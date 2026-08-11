# AnalyzeDoc Hanko-Occlusion Benchmark v2

Harness frozen 2026-07-18 — and run the same day. v2 answers [v1](../hanko-benchmark/)'s
three stated limitations, in two legs: **leg 1 (2026-07-18)**, on the same model catalog
as v1, settled the three open questions six days after the original run; **leg 2
(autumn 2026)**, on the next model generation with the harness byte-identical, adds the
longitudinal axis. Together the legs form a clean 2×2 — a material axis (v1 vs v2) at one
point in time, and a time axis (July vs autumn) on one fixed material.

## Leg-1 answers (2026-07-18)

| v1 open question | answer |
|---|---|
| Which arithmetic produced the derived subtotals — `total − tax`, or `total ÷ 1.1`? | **÷ 1.1.** The 5.5/5.6 `@low` variants return 1,235,000 (= total ÷ 1.1) for the subtotal and 123,500 (= total/11) for the tax at **every** occlusion level including zero, on every instance — they read the total and manufacture the rest. 71 of 270 deep-coverage reads carry the exact fingerprint. In v1, the round 10% made that manufacture value-identical to the printed numbers, so it scored as reading |
| Was claude-fable-5's 94% stamp read memory, or reading? | **Reading.** 111/120 (93%) on 納検済印, a phrase that cannot exist in training data. The catalog's dominant failure is not memory at all but traversal: 済納印検 ×966 — the 2×2 layout read left column first |
| Were the six "correct" branch cells coin-flips? | **Yes.** With the fictional 月芝支店, zero "correct" branch cells remain |

## What v2 changes

Exactly three deltas, one per "a future version…" note in the v1 README. Everything
else is verbatim v1.

| v1 limitation | v2 change | what the output now fingerprints |
|---|---|---|
| The tax is a round 10%, so `total − tax` and `total ÷ 1.1` give the same subtotal — the derivation route can't be told from the value | Mixed 8%/10% rates (per-rate 区分記載 box added bottom-left; the totals block keeps v1's geometry) | `total ÷ 1.1` = **1,235,000** — an exact integer that appears on no printed line. It also equals `total − total/11`, so every flat-10% algebra collapses onto this one number. A model that derives with the flat-10% prior signs its route in the answer |
| The seal text 検収済印 is a real, common phrase — a model reading it can't be separated from one recognizing it | Fictional seal **納検済印** (web 0-hit, checked 2026-07-18); same solid pad, same 2×2 right-to-left layout | Reading emits 納検済印. Completion-from-prior emits a real phrase — 検収済印 above all, v1's seal and the category mode. The mode becomes the trap |
| The printed branch 本店営業部 is the single most common branch name in Japan — six "correct" cells were, on co-occurrence evidence, coin-flips | Fictional branch **月芝支店** (web 0-hit; 芝支店, 月隈支店 and 初芝支店 exist — this one does not) | A correct branch read is now evidence of reading |

Two deliberate constants: the **subtotal keeps v1's exact value (¥1,237,500)**, so the
M-target bounding box and the achieved overlap percentages are identical to v1's — the
ladders are geometrically comparable across versions. And the 8% line item is bottled
office water (※-marked per 適格請求書 conventions): a little synthetic-invoice realism
traded for exact, rounding-free arithmetic.

## Unchanged from v1

The overlap ladder L0–L5, the 2×2 (translucent/opaque × name/subtotal), the extraction
prompt (it never mentions the stamp — how the model treats the occlusion is the
measurand), the scorer, the report, the canvas, the pinned fonts, and the stamp
mechanics. The generator's assertions now additionally include the L5 pixel checks
(opaque: no dark ink survives in the target box; translucent: the black ink underneath
does) and the route-fingerprint non-collision at every rounding granularity.

## Harnesses

| Script | Provenance |
|---|---|
| `hanko_gen_materials_v2.py` | **The only file that differs from v1** — the `_v2` suffix marks the diff surface. Asserts the arithmetic freeze, the route-fingerprint separation, and the L5 pixel checks |
| `hanko_run_benchmark.py` | Verbatim v1. **Refresh `MODELS`/`RATES` from the run-day catalog and billing before running** |
| `hanko_score_results.py` | Verbatim v1 (ground-truth-driven; no changes needed) |
| `hanko_report.py` | Verbatim v1 |
| `hanko_lowfield_analysis.py` | Shared with v1; pass `--newgen`/`--oldgen` patterns for the generations under test |
| `hanko_route_analysis.py` | New in v2: names the derivation route from the answer alone; flags flat-10% tax co-derivation (`tax = total/11` = 123,500) and real-phrase stamp completions. Fed v1 output, it reports the routes as non-separable — by design |

## Running

```bash
pip install requests pillow numpy
export LDXHUB_API_KEY="your-key"          # get one: https://gw.portal.ldxhub.io
python3 hanko_gen_materials_v2.py         # 24 materials + ground truth; all asserts must pass
python3 hanko_run_benchmark.py --dry-run --models all   # cost preflight (rates change — no fixed table here)
python3 hanko_run_benchmark.py --models pilot --yes
python3 hanko_score_results.py && python3 hanko_report.py
python3 hanko_lowfield_analysis.py --newgen "<pattern>" --oldgen "<pattern>"
python3 hanko_route_analysis.py
```

## results/

`results/2026-07/` holds the leg-1 point-in-time summaries (27 variants, 3,240 jobs, the
same catalog as v1's 2026-07-12 run): the per-model metric table, the four-panel heatmap,
the per-field and route analyses, and the model-catalog snapshot. Leg 2 lands beside it
when it happens. Provider vision pipelines change — re-run before trusting anything for
anything current.

## Write-ups

- [The cheap tier reads one number](https://dev.to/hidekimori/the-cheap-tier-reads-one-number-841) — leg 1: the ÷1.1 fingerprint, the seal resolved, the branch cured (2026-08-11)