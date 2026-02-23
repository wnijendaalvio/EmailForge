# Email Template Generator – Technical Documentation

Technical reference for developers maintaining or extending the Email Template Generator.

---

## Architecture overview

The system converts a **translations CSV** into a **Customer.io Liquid email template**. The main flow:

```
CSV (Key, Module?, module_index?, en, ar, ...)
    → load_translations() / parse
    → build Liquid captures ({% capture key %}{% case locale_key %}...)
    → inject into BASE_TEMPLATE
    → output .liquid file
```

**Components:**

| Component | Responsibility |
|-----------|----------------|
| `csv_translations_to_email.py` | Core generator, Liquid builder, CLI |
| `app.py` | Streamlit UI, preview, download |
| `design_tokens*.liquid` | Brand-specific colours, spacing, fonts |
| `standard_links.json` | Configurable URLs (terms, privacy, social, app) |

---

## File structure

```
Project_Email_Template/
├── app.py                          # Streamlit app entry point
├── csv_translations_to_email.py    # Main generator (~1750 lines)
├── csv_to_email_template.py         # Legacy module-based generator (separate flow)
├── csv_to_price_alerts_email.py    # Price alerts–specific generator
├── design_tokens.liquid             # Vio design tokens
├── design_tokens_holiday_pirates.liquid
├── design_tokens_kiwi.liquid
├── standard_links.json              # Default links (terms, privacy, social, app)
├── requirements.txt                # streamlit>=1.28.0
├── SHEET_STRUCTURE_TRANSLATIONS.md  # CSV schema
├── DESIGN_TOKENS.md
└── email_translations.csv           # Sample input (optional)
```

---

## Main modules and functions

### `csv_translations_to_email.py`

| Symbol | Type | Purpose |
|--------|------|---------|
| `LOCALE_COLUMNS` | list | Ordered locale codes (en, ar, zh-cn, …). Must match Liquid `locale_key`. |
| `TRANSLATABLE_KEYS` | list | Keys whose values change per locale |
| `STRUCTURE_KEYS` | list | Keys shared across locales (URLs, ratings, colours) |
| `MODULE_KEY_MAP` | dict | Maps (module, key) → internal key for module-based CSV |
| `DESIGN_TOKENS_BRANDS` | tuple | ("vio", "holiday_pirates", "kiwi") |
| `resolve_include_locales()` | fn | Resolves preset/custom → list of locale codes |
| `load_translations()` | fn | Parses CSV into `translations[key][locale]`, `structure[key]` |
| `generate_template()` | fn | Main entry: CSV path + options → Liquid string |
| `generate_standard_input_template()` | fn | Builds blank CSV for selected modules |
| `liquid_to_preview_html()` | fn | Renders Liquid to HTML for Streamlit preview |
| `get_module_preview_html()` | fn | Standalone module preview HTML |
| `_load_design_tokens()` | fn | Loads `design_tokens*.liquid` by brand |
| `_parse_design_tokens()` | fn | Extracts token_name → value for preview |
| `load_standard_links()` | fn | Loads `standard_links.json` (with defaults) |

### `app.py`

| Symbol | Purpose |
|--------|---------|
| `st` | Streamlit API |
| Imports from `csv_translations_to_email` | `generate_template`, `load_translations`, `liquid_to_preview_html`, etc. |
| Sidebar | Options: show_header_logo, show_footer, show_terms, app_download_colour, design_tokens_brand, locale_preset |
| Tabs | "Generate from CSV" (upload, generate, download, preview), "Standard input template" (module selection, CSV/links download) |

---

## CSV parsing

### Detected formats

1. **Legacy:** Columns `Key, en, ar, …` – locale columns start at index 1.  
2. **Module-based:** Columns `Key, Module, module_index, en, ar, …` – locale columns start at index 3. Detection: second header = "Module", third = "module_index".

### Locale inference

`get_csv_locales()` inspects headers and returns locales in `LOCALE_COLUMNS` order. If headers don’t match, it falls back to matching normalized header names (lowercase, dashes).

### Fallback behaviour

- Empty cell → fallback to `en`.  
- Missing key → omitted from template (no Liquid capture).

---

## Liquid template structure

### Placeholders

The base template uses placeholders replaced at generation time:

| Placeholder | Injected content |
|-------------|------------------|
| `{{ DESIGN_TOKENS_BLOCK }}` | Contents of `design_tokens*.liquid` |
| `{{ APP_DOWNLOAD_SETTINGS }}` | App download module config (title, features, colour, ratings, badge URLs) |
| `{{ LINKS_BLOCK }}` | Footer/prefs links from `standard_links.json` |
| `{{ CONTENT_CAPTURES }}` | `{% capture key %}...{% endcapture %}` blocks for each translatable key |

### Locale resolution (Liquid)

```liquid
{%- assign lang = customer.language | default: "en" | downcase | replace: "_", "-" -%}
{%- assign lang2 = lang | slice: 0, 2 -%}
{%- assign locale_key = lang2 -%}
{%- if lang contains "zh-hk" -%}{%- assign locale_key = "zh-hk" -%}
{%- elsif lang contains "zh-tw" -%}{%- assign locale_key = "zh-tw" -%}
{%- elsif lang contains "zh-cn" -%}{%- assign locale_key = "zh-cn" -%}
{%- elsif lang contains "fr-ca" -%}{%- assign locale_key = "fr-ca" -%}
{%- elsif lang contains "pt-br" -%}{%- assign locale_key = "pt-br" -%}
{%- elsif lang contains "es-419" -%}{%- assign locale_key = "es-419" -%}
{%- elsif lang contains "en-gb" -%}{%- assign locale_key = "en-gb" -%}
{%- endif -%}
```

Special cases: `iw` → `he`, `tl` → `fil`, `nb`/`nn` → `no`.

### RTL support

`rtl_locales = "ar,he"` – `dir`, `align`, `headline_align` set accordingly.

---

## Design tokens and brands

### Token files

| Brand | File |
|-------|------|
| vio | `design_tokens.liquid` |
| holiday_pirates | `design_tokens_holiday_pirates.liquid` |
| kiwi | `design_tokens_kiwi.liquid` |

Tokens use `{%- assign token_xyz = "value" -%}`. Semantic aliases reference primitives (e.g. `token_bg_page = token_neutral_c050`).

### Adding a new brand

1. Create `design_tokens_<brand>.liquid` with `token_*` assignments.  
2. Add brand to `DESIGN_TOKENS_BRANDS` in `csv_translations_to_email.py`.  
3. Extend `_get_design_tokens_path()` to return the new file path.  
4. Add label in `app.py` `format_func` for the brand selector.

---

## App store & Play store badges

### Google Play

`{% capture google_play_badge_url %}` with `{% case locale_key %}` – localized badge URLs per locale (ar, zh-cn, zh-tw, zh-hk, hr, cs, da, nl, en, en-gb, fil, fi, fr, fr-ca, de, el, he, hu, id, it, ja, ko, ms, no, pl, pt, pt-br, ro, ru, es, es-419, sv, th, tr, uk, vi).

### App Store

Same pattern: `{% capture app_store_badge_url %}` with per-locale URLs. Fallback (`{% else %}`) uses the generic English badge URL.

### Preview replacement

`liquid_to_preview_html()` replaces `{{ app_store_badge_url }}` and `{{ google_play_badge_url }}` with static URLs for HTML preview.

---

## CLI reference

```bash
python3 csv_translations_to_email.py <csv_path> [options] > output.liquid
```

| Option | Default | Description |
|--------|---------|-------------|
| `--show-header-logo` | TRUE | Show header logo |
| `--show-footer` | TRUE | Show footer |
| `--show-terms` | TRUE | Show terms & privacy block |
| `--app-download-colour-preset` | LIGHT | LIGHT or DARK for app download banner |
| `--design-tokens-brand` | vio | vio, holiday_pirates, kiwi |
| `--locale-preset` | (all from CSV) | en_only, top_5, global |
| `--include-locales` | (from CSV) | Comma-separated: en,es,fr |

---

## Data flow

### Generate from CSV

1. User uploads CSV → saved to temp file.  
2. `load_translations(csv_path)` → `(translations, structure)`.  
3. `generate_template(csv_path, ...)`:
   - Loads design tokens by brand.  
   - Loads standard links.  
   - Builds content captures (per-key `{% case locale_key %}`).  
   - Builds app download settings.  
   - Injects into `BASE_TEMPLATE`.  
4. Returns Liquid string → download or preview.

### Preview

1. `liquid_to_preview_html(liquid_content, translations, structure, ...)`:
   - Replaces `{{ token_* }}` with parsed values.  
   - Replaces `{{ key }}` with `translations[key]["en"]`.  
   - Replaces badge URLs, links, etc.  
   - Wraps in minimal HTML for display.

---

## Dependencies

- **Python:** 3.10+  
- **Streamlit:** >= 1.28.0 (for `app.py`)  
- **Standard library:** argparse, csv, re, sys, tempfile, pathlib, json  

No external Liquid renderer; output is raw Liquid for Customer.io.

---

## Extending the tool

### New translatable key

1. Add key to `TRANSLATABLE_KEYS` in `csv_translations_to_email.py`.  
2. Add usage in `BASE_TEMPLATE` (or a module template) where the content is rendered.  
3. Update `SHEET_STRUCTURE_TRANSLATIONS.md`.

### New module

1. Add module to `MODULE_KEY_MAP` with (module_name, sheet_key) → internal_key.  
2. Add module template block in `build_*` / `BASE_TEMPLATE`.  
3. Wire module inclusion in `generate_standard_input_template()` and Streamlit module checkboxes.

### New locale

1. Add locale code to `LOCALE_COLUMNS` (in correct order).  
2. Add badge URLs for Google Play and App Store in the respective `{% case %}` blocks.  
3. Add footer/prefs translations if needed.

---

## Related scripts

| Script | Purpose |
|--------|---------|
| `csv_to_email_template.py` | Older module-based generator (different CSV format). |
| `csv_to_price_alerts_email.py` | Price alerts–specific template; simpler key set. |

These are separate pipelines; changes to `csv_translations_to_email.py` do not affect them.
