# AnalyzeDoc: Japanese qualified invoice → JSON

Extracts a Japanese qualified invoice (適格請求書) — mixed 8%/10% tax rates, T+13-digit registration number, per-rate tax summary — into structured JSON. The schema is defined by example: `example_output.json` *is* the schema.

## Files

- `invoice-sample-ja.pdf` — fictional sample invoice (1 page)
- `job.json` — complete job request (replace `file_id` after upload)
- `system_prompt.txt` — the rules (dates, integer JPY, T+13, no leading `+` on phones)
- `example_output.json` — the schema-by-example
- `expected_output.json` — the verified result for this PDF

## Run it

```bash
# 1. Upload -> file_id
curl -s -X POST https://gw.ldxhub.io/files \
  -H "Authorization: Bearer $LDXHUB_API_KEY" \
  -F "file=@invoice-sample-ja.pdf"

# 2. Put the file_id into job.json, then create the job
curl -s -X POST https://gw.ldxhub.io/analyzedoc/jobs \
  -H "Authorization: Bearer $LDXHUB_API_KEY" \
  -H "Content-Type: application/json" \
  -d @job.json

# 3. Wait for completion (server-side wait, no polling loop)
curl -s "https://gw.ldxhub.io/analyzedoc/jobs/$JOB_ID?wait=30" \
  -H "Authorization: Bearer $LDXHUB_API_KEY"

# 4. Fetch the result
curl -s "https://gw.ldxhub.io/files/$OUTPUT_FILE_ID/content" \
  -H "Authorization: Bearer $LDXHUB_API_KEY"
```

Compare against `expected_output.json`. All amounts are integers (JPY has no decimals — the integer literals in the example are what declare that), 御中 is stripped from the customer name, and the ※ reduced-rate markers stay verbatim in the descriptions while `tax_rate` carries the meaning.

## Notes

- **Example values are type declarations.** `10000` → integer, `1234.56` → number. For USD invoices, write the example amounts with decimals.
- **Example values differ from the document** on purpose (otherwise you can't tell reading from copying).
- `tax_summary` is an array: one entry per tax rate on the invoice.

Write-ups: <!-- TODO: article links (Hatena / dev.to) -->
