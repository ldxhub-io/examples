# LDX hub Examples

Ready-to-run examples for the [LDX hub API](https://gw.portal.ldxhub.io).

| Example | Service | What it shows |
|---|---|---|
| [analyzedoc/qualified-invoice-ja](analyzedoc/qualified-invoice-ja/) | AnalyzeDoc | Japanese qualified invoice (適格請求書) → JSON. Mixed 8%/10% tax rates, schema-by-example. |
| [analyzedoc/low-detail-study](analyzedoc/low-detail-study) | AnalyzeDoc | Measurement harnesses: what low-detail image modes actually do — extraction fabrication vs. classification accuracy (July 2026 snapshot). |
| [analyzedoc/legibility-benchmark](analyzedoc/legibility-benchmark) | AnalyzeDoc | Legibility Frontier: one Japanese invoice degraded across 7 scan resolutions × 4 font tiers, 27 model variants — where each model stops reading, and whether it then blanks or fabricates. |
| [analyzedoc/hanko-benchmark](analyzedoc/hanko-benchmark) | AnalyzeDoc | Hanko Occlusion: a red seal covering one invoice field across 6 overlap levels × 2 opacities, 27 model variants — who reads through the ink, and who answers a destroyed field by deriving it. |
| [analyzedoc/hanko-benchmark-v2](analyzedoc/hanko-benchmark-v2) | AnalyzeDoc | Hanko Occlusion v2: same ladder, mixed tax rate + fictional seal + fictional branch — every wrong derivation route now yields a nameable answer. Leg 1 (2026-07) recorded; leg 2 (autumn) pending. |

Each example folder contains the input document, a complete `job.json`, and the verified expected output, so you can run it end-to-end with four `curl` commands. Study folders contain runnable measurement harnesses and their recorded results instead.

Get an API key and quickstart: see the [DevPortal](https://gw.portal.ldxhub.io/introduction).
