# Email Template Generator – User Guide

This guide helps content editors, marketers, and translators use the Email Template Generator to create multi-language Customer.io email templates from a spreadsheet.

---

## What is this tool?

The **Email Template Generator** turns a translations spreadsheet (CSV) into a ready-to-use Customer.io Liquid email template. You enter your content in one language per column, and the tool produces a single template that shows the right translation based on each recipient’s language.

**Benefits:**
- One spreadsheet as the single source of truth for all translations  
- Preview before downloading  
- Support for 37+ languages  
- Brand presets: Vio, Holiday Pirates, KIWI  

---

## How to run it

### Option 1: Web app (recommended)

1. Open a terminal and go to the project folder.  
2. Run:
   ```bash
   streamlit run app.py
   ```
3. Your browser opens at `http://localhost:8501`.  
4. Use the app to upload CSVs, preview templates, and download.

### Option 2: Command line

If you prefer the command line:

```bash
python3 csv_translations_to_email.py email_translations.csv > full_email_template.liquid
```

You can also host the app on **Streamlit Community Cloud** – push to GitHub and deploy from [share.streamlit.io](https://share.streamlit.io).

---

## Workflow

### 1. Prepare your translations spreadsheet

Use one of these formats:

- **Legacy:** `Key, en, ar, zh-cn, zh-tw, ...` – one row per content key, one column per locale  
- **Module-based:** `Key, Module, module_index, en, ar, ...` – same idea, with module grouping  

Column order must match the expected locale order. See [CSV format](#csv-format) below.

### 2. Choose modules

In the **Standard input template** tab you can:

- Select **Hero module** – simple (headline + body + CTA) or two-column (4 feature blocks + CTA)  
- Include **App download module** – app store / Play store badges with features  
- Include **USP modules** – icon left, text/image right, or alternating layout  
- Include **Disclaimer/terms** module  

### 3. Set options (sidebar)

| Option | What it does |
|--------|--------------|
| **Show header logo** | Show or hide the logo at the top |
| **Show footer** | Show or hide the footer |
| **Show terms** | Show or hide terms & privacy links |
| **App download banner colour** | LIGHT (cream) or DARK (purple) |
| **Colour scheme / brand** | Vio, Holiday Pirates, or KIWI |
| **Target languages** | English only, Top 5, Global, or custom selection |

### 4. Generate and download

1. Upload your CSV in the **Generate from CSV** tab.  
2. The template generates automatically.  
3. Click **Download full_email_template.liquid**.  
4. Copy the file into Customer.io.

### 5. Preview

- **HTML preview** – see how the email looks (English locale).  
- **Liquid source** – inspect the generated template code.

---

## CSV format

### Column order

The first row must be headers. Locale columns follow this order:

| Column | Locale | Language |
|--------|--------|----------|
| 1 | Key | (row identifier) |
| 2 | en | English |
| 3 | ar | Arabic |
| 4 | zh-cn | Chinese (Simplified) |
| 5 | zh-tw | Chinese (Traditional) |
| … | … | … |
| 37 | vi | Vietnamese |

Full list: en, ar, zh-cn, zh-tw, zh-hk, hr, cs, da, nl, en-gb, fil, fi, fr, fr-ca, de, el, he, hu, id, it, ja, ko, ms, no, pl, pt, pt-br, ro, ru, es, es-419, sv, th, tr, uk, vi.

### Content keys (translatable)

| Key | Description |
|-----|-------------|
| subject_line | Email subject / `<title>` |
| preheader | Hidden preview text |
| headline | Main H1 above hero image |
| body_1, body_2 | Body paragraphs |
| cta_text | CTA button label |
| app_download_title | App download section title |
| app_download_feature_1, 2, 3 | App download feature bullets |

### Structure keys (same for all languages)

| Key | Description |
|-----|-------------|
| image_url | Hero image URL |
| image_url_mobile | Optional different mobile hero image |
| cta_link | CTA button URL |
| cta_alias | Tracking alias for the CTA |

### Tips

- **Empty cells** fall back to English (en).  
- Use **UTF-8** when exporting from Excel or Google Sheets.  
- Values with **commas** must be in quotes, e.g. `"Get price alerts, and know when to book."`  
- Do **not reorder** locale columns.  
- Optional rows (e.g. `headline_2`) can be omitted if not used.

---

## Standard links

In the **Standard input template** tab you can configure:

- **Terms of use** – URL for terms  
- **Privacy policy** – URL for privacy policy  
- **App download page** – App store / Play store landing  
- **Social links** – Instagram, Facebook, LinkedIn  

Save as `standard_links.json` in your project folder to reuse your settings.

---

## Locale resolution

The template selects the right translation based on `customer.language` and, where needed, `customer.country`:

- **Brazil (BR)** → pt-br (Brazilian Portuguese)  
- **Portugal (PT)** → pt (European Portuguese)  
- **Latin America** → es-419  
- **United Kingdom** → en-gb  
- **Canada (French)** → fr-ca  

---

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| Preview looks wrong | Check that all required keys have values in at least one locale (usually en). |
| Wrong language shown | Confirm locale column headers match the expected order exactly. |
| Missing translations | Empty cells fall back to English; fill en first, then other locales. |
| CSV not loading | Ensure UTF-8 encoding and valid CSV (commas in quotes). |
| App won’t start | Install dependencies: `pip install -r requirements.txt` |

---

## Need more detail?

- [SHEET_STRUCTURE_TRANSLATIONS.md](SHEET_STRUCTURE_TRANSLATIONS.md) – Full CSV structure and module mappings  
- [DESIGN_TOKENS.md](DESIGN_TOKENS.md) – Colours, spacing, and layout tokens  
