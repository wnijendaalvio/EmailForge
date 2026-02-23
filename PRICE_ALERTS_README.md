# Price Alerts Email – Translations Workflow

## Overview

The Price Alerts email template uses a **CSV as the source of truth** for all translations. Edit the CSV, then regenerate the Liquid template.

## Files

| File | Purpose |
|------|---------|
| `price_alerts_translations.csv` | Source of translations. Edit this file or import from Google Sheets. |
| `csv_to_price_alerts_email.py` | Script that generates the Liquid template from the CSV. |
| `price_alerts_full_email.liquid` | Generated Customer.io email template (output). |

## Locale Structure

Same column order as `SHEET_STRUCTURE_TRANSLATIONS.md`:

`Key, en, ar, zh-cn, zh-tw, zh-hk, hr, cs, da, nl, en-gb, fil, fi, fr, fr-ca, de, el, he, hu, id, it, ja, ko, ms, no, pl, pt, pt-br, ro, ru, es, es-419, sv, th, tr, uk, vi`

## Content Keys

| Key | Description |
|-----|--------------|
| subject_line | Email subject / `<title>` |
| preheader | Preheader text (hidden preview) |
| headline | Main H1 above the hero image |
| body_1 | First body paragraph |
| body_2 | Second body paragraph |
| cta_text | CTA button label |

## Workflow

1. **Edit translations** in `price_alerts_translations.csv` (or export from Google Sheets with the same structure).
2. **Regenerate the template**:
   ```bash
   python3 csv_to_price_alerts_email.py price_alerts_translations.csv -o price_alerts_full_email.liquid
   ```
3. **Copy** the generated `price_alerts_full_email.liquid` into Customer.io.

## CSV Tips

- Use UTF-8 encoding.
- Values with commas must be quoted (e.g. `"Get price alerts, and know exactly when to book."`).
- Empty cells fall back to the English (en) value.
- Column order must match exactly; do not reorder columns.

## Locale Resolution (pt/pt-br, etc.)

The template includes country-based locale resolution. When `customer.language` is ambiguous (e.g. `pt` or `portuguese`), it uses `customer.country`, `customer.country_code`, or `customer.cio_iso_country` to pick the correct locale:

- **Brazil (BR)** → pt-br (Brazilian Portuguese)
- **Portugal (PT)** → pt (Portugal Portuguese)
- **Latin America Spanish** → es-419
- **UK English** → en-gb
- **Canadian French** → fr-ca
