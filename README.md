# LDX hub Examples

Ready-to-run examples for the [LDX hub API](https://gw.portal.ldxhub.io).

| Example | Service | What it shows |
|---|---|---|
| [analyzedoc/qualified-invoice-ja](analyzedoc/qualified-invoice-ja/) | AnalyzeDoc | Japanese qualified invoice (適格請求書) → JSON. Mixed 8%/10% tax rates, schema-by-example. |
| [analyzedoc/low-detail-study](analyzedoc/low-detail-study) | AnalyzeDoc | Measurement harnesses: what low-detail image modes actually do — extraction fabrication vs. classification accuracy (July 2026 snapshot). |

Each example folder contains the input document, a complete `job.json`, and the verified expected output, so you can run it end-to-end with four `curl` commands. Study folders contain runnable measurement harnesses and their recorded results instead.

Get an API key and quickstart: see the [DevPortal](https://gw.portal.ldxhub.io/introduction).
