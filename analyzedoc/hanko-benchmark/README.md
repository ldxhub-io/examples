# AnalyzeDoc Hanko-Occlusion Benchmark

Measurement harnesses behind the blog post [*"Reading under the stamp"*](https://dev.to/hidekimori/reading-under-the-stamp-57bi), plus the recorded results from the July 12, 2026 run.

**Question:** when a red company seal (判子) sits on top of a field in an otherwise perfectly sharp invoice, do vision models read through it, leave the field blank, or fill it some other way?

**Answer (as of 2026-07-12):** it depends on the seal, and on the model — in ways that sort models into types.

| Condition | What it isolates | Result |
|---|---|---|
| Translucent seal over the issuer name, 100% coverage | Can the model see through red ink to the black underneath? | `@high` variants: **60 / 60 correct** |
| Opaque seal over the issuer name, 100% coverage | Same field, information physically destroyed | same `@high` variants: **0 / 60** |
| Opaque seal over the **subtotal**, 80–100% coverage | The subtotal equals total − tax, both left visible — so a correct answer here is *derived, not read* | Anthropic models: **0 / 30** (blank). OpenAI/Azure `@low`: **80 / 100** (derived) |

Two findings fall out. **The chromatic channel:** strong readers strip the vermilion and read the surviving black ink, the way an OCR red-drop preprocessor does — a 0.56–0.76 accuracy advantage of translucent over opaque. **The inversion:** on a field whose pixels are gone, the models that *can* read it fall silent, while a class of weaker models quietly reconstructs it from the visible neighbors and returns it with no sign it was never seen. A derived value reconciles by definition, so it passes every "do the numbers add up?" validation.

## Design

One variable: how much of a target field's ink the stamp covers, L0 (0%, a control) through L5 (100%), in six steps. A 2×2 crosses **opacity** (translucent multiply-blend vs. opaque pad) with **target** (issuer name, which has no arithmetic relation to anything; subtotal, which is derivable from total − tax). The base document is a synthetic Japanese invoice at 300 dpi — every value fictional, `subtotal + tax = total`. The seal is a solid-pad 検収済印 (a receiving-side inspection stamp, carrying no issuer information). The extraction prompt never mentions the stamp: how the model treats the occlusion is the measurand, so instructing any behavior would destroy it.

The generator asserts, pixel by pixel, that no dark ink survives inside the target box under the opaque seal at L5, and that it *does* survive under the translucent seal — so "information destroyed" and "information present but red-covered" are guaranteed, not assumed.

## Harnesses

| Script | What it does |
|---|---|
| `hanko_gen_materials.py` | Generates the 24 materials (2 opacities × 2 targets × 6 overlap levels), byte-reproducible; downloads and checksums the pinned Noto Sans CJK JP font |
| `hanko_run_benchmark.py` | Runs N repeats per (model × instance × level) through the AnalyzeDoc API; resume-safe |
| `hanko_score_results.py` | Classifies each field as correct / near / blank / fabricated against frozen ground truth; adds a stamp-text reference class |
| `hanko_report.py` | Derives the metrics (occlusion frontier, chromatic gain, inference rate, collateral, stamp-read rate) and the heatmap |

All materials are generated on the fly into `materials_hanko/` — fully synthetic, every name fictional. Ground truth is frozen in `hanko_ground_truth.json`; field classification is copied verbatim from the [legibility benchmark](https://github.com/ldxhub-io/examples/tree/main/analyzedoc/legibility-benchmark) scorer, so numbers are comparable across the two benchmarks.

## Running

```bash
pip install requests pillow numpy
export LDXHUB_API_KEY="your-key"     # get one: https://gw.portal.ldxhub.io
python3 hanko_gen_materials.py       # writes materials_hanko/ (deterministic)
python3 hanko_run_benchmark.py --dry-run --models all        # cost preflight
python3 hanko_run_benchmark.py --models pilot --yes          # 3 models × full grid
python3 hanko_score_results.py && python3 hanko_report.py
```

| Scope | Command | Jobs | List cost (dry-run) |
|---|---|---|---|
| Full (27 variants) | `--models all` | 3,240 | ≈ $144.84 |
| Name target only | `--models all --instances A_N,B_N` | 1,620 | ≈ $72.42 |
| Pilot (3 models) | `--models pilot` | 360 | ≈ $36.63 |
| Free-tier repro | `--models ume --instances A_N --t1-reps 3` | 54 | ≈ 11,649 credits |

Notes:

- `hanko_run_benchmark.py` has `PROVIDER_LIMITS = {}` — the gateway rate-shapes provider file APIs server-side, so no client-side concurrency cap is needed. If you're hitting a self-hosted quota, the dict is there to set one.
- The tax in this invoice is a round 10%, so `total − tax` and `total ÷ 1.1` yield the same subtotal and can't be told apart from the value alone. A future version with a mixed rate would fingerprint the route.
- The seal text 検収済印 is a real, common phrase, so a model reading it can't be separated from one recognizing it. A future version needs a fictional seal.
- Six `bank_branch` cells scored *correct* for 5.5/5.6-generation `@low` variants at L0 are, on co-occurrence evidence, inventions that collide with the truth: the bank name in each of those same responses is fabricated, and the printed branch — 本店営業部 — is the most common branch name in Japan. Fictional ground truth doesn't protect a field whose true value is the category's mode; a future version uses a fictional branch name too.

## results/

`results/2026-07/` holds the point-in-time summaries from the 2026-07-12 full run (27 variants, 3,240 jobs) that back the blog post: the per-model metric table (`summary.csv`, `results_table.md`), the four-panel error-rate heatmap (`heatmap.png`), and the model-catalog snapshot (`models_snapshot.json`, captured 2026-07-16 and ID-verified against the run). Provider vision pipelines change — re-run the harnesses before trusting the numbers for anything current.

## Write-ups

- [Reading under the stamp](https://dev.to/hidekimori/reading-under-the-stamp-57bi) — the two findings: the chromatic channel, and the readers going silent while the non-readers answer (2026-07-28)
- [The cheap tier doesn't go blank — it writes](https://dev.to/hidekimori/the-cheap-tier-doesnt-go-blank-it-writes-5aoo) — the L0 slice: what @low actually reads on a razor-sharp invoice, and what fills the rest (2026-08-04)