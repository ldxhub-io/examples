# AnalyzeDoc Low-Detail Study

Measurement harnesses behind the blog post [*"When AI can't read, it invents — but it still sees the shape"*](https://dev.to/hidekimori/when-ai-cant-read-it-invents-but-it-still-sees-the-shape-18ac), plus the recorded results from the July 10, 2026 runs.

**Question:** at low image-detail settings (roughly 300 tokens per page), what do vision models actually do with document images?

**Answer (as of 2026-07-10):**

| Task | GPT-5.5 / 5.6-gen low modes | Controls* |
|---|---|---|
| Extract an invoice (strict 4-field match) | **0 / 70 correct** — arithmetic often right, identities invented | 38 / 40 (2 near-misses: a dropped space — misreads, never fabrication) |
| Classify document type, 5 layout-distinct docs | **105 / 105** | 30 / 30 |
| Classify look-alike Japanese docs + degraded scans | **147 / 147** | 42 / 42 |

\* Controls: GPT-5.4 / GPT-5.4 mini at the same low detail, Gemini 3.5 Flash at a *smaller* token budget, and GPT-5.6 Sol at high detail.

The capability boundary this draws: **title-tier text is read reliably; body-tier text is not — and where reading fails, the 5.5+ generations fill the gap with internally consistent fiction** (correct totals, invented counterparty, an invoice year shifted from 2026 to 2025 with the date field shifted to match).

## Harnesses

| Script | What it does | Jobs (defaults) |
|---|---|---|
| `fab_test.py` | Generates a synthetic invoice, runs N extraction repeats per configuration, scores 4 fields against frozen ground truth | 110 |
| `sort_test.py` | Generates 5 layout-distinct documents (invoice / receipt / business card / contract / blank), tests 6-way classification | 135 |
| `sort_lookalike_test.py` | Generates 3 near-identical Japanese documents (請求書 / 御見積書 / 注文書) plus degraded variants (scan noise, 2° tilt, JPEG q25), tests title-level reading | 189 |

All materials are generated on the fly into `images/` — fully synthetic, every name fictional. Pass/fail criteria are frozen in code (`verdict()`), so runs are comparable across time and machines.

## Running

```bash
pip install requests pillow
export LDXHUB_API_KEY="your-key"     # get one: https://gw.portal.ldxhub.io
python3 fab_test.py                  # or: REPEATS=3 python3 fab_test.py
```

Notes:

- `sort_lookalike_test.py` needs a Japanese font (Hiragino on macOS, Noto Sans CJK on Linux). Edit `ja_font()` if yours lives elsewhere.
- A default `fab_test.py` run costs roughly 40–50k credits at current AnalyzeDoc rates; the classification runs are cheaper.
- `example_output` uses non-`X.0` decimals (e.g. `12.34`) on purpose: values like `10.0` collapse to integers in JSON round-trips, which silently turns the inferred schema into integer fields and produces a convincing false positive. If you modify the harness, keep the decimals non-trivial.

## results/

Unmodified summary files from the 2026-07-10 runs that back the blog post. These are a point-in-time snapshot — provider vision pipelines change, so re-run the harnesses before trusting the numbers for anything current.
