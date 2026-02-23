# Google Sheet structure for multi-language email (translations CSV)

Use one sheet where **each row is a content key** and **each column is a locale**. Download as CSV and run:

```bash
python3 csv_translations_to_email.py email_translations.csv > full_email_template.liquid
```

**Design tokens:** All colours, spacing, and layout use tokens from `design_tokens.liquid`. See [DESIGN_TOKENS.md](DESIGN_TOKENS.md).

---

## Supported formats

The script supports two CSV formats:

### Format A – Legacy (Key, en, ar, …)

Columns: **Key** (1), then locale columns at index 2+.

### Format B – Module-based (Key, Module, module_index, en, ar, …)

Columns: **Key** (1), **Module** (2), **module_index** (3), then locale columns at index 4+.

When the second column header is `Module` and the third is `module_index`, the script uses the module format. Row keys are mapped via `MODULE_KEY_MAP`:

| Module | Key | Mapped to |
|--------|-----|-----------|
| hero_module | subject_line, preheader, headline, body_1, body_2, cta_text | same |
| hero_module | image_url, image_url_mobile, image_deeplink, cta_link, cta_alias | same |
| hero_module_two_column | subject_line, preheader, headline, subheadline | subject_line, preheader, headline, secondary_headline |
| hero_module_two_column | body_1_h2, body_1_copy, body_2_h2, body_2_copy, body_3_h2, body_3_copy, body_4_h2, body_4_copy | hero_two_col_body_1_h2 … hero_two_col_body_4_copy |
| hero_module_two_column | image_1_URL, image_2_URL, image_3_URL, image_4_URL | hero_two_col_image_1_url … hero_two_col_image_4_url |
| hero_module_two_column | cta_text, hero_image_url, image_deeplink, cta_link, cta_alias | hero_two_col_cta_text, image_url, image_deeplink, cta_link, cta_alias |
| app_download_module | headline | app_download_title |
| app_download_module | feature_1, feature_2, feature_3 | app_download_feature_1/2/3 |
| app_download_module | colour, color | app_download_colour |

`app_download_colour` in CSV is deprecated; use the `app_download_colour_preset` toggle at the top (LIGHT/DARK) or `app_download_colour` merge field override.

**hero_module_two_column** – Optional two-column feature module. When present (e.g. when `body_1_h2` is filled), renders the hero image, then 4 alternating text/image blocks + CTA instead of the standard body paragraphs. Uses headline and subheadline for the header.

---

## Column headers (exact order)

The **first row** of your sheet must be the header row. The script uses **locale columns in this order** (they match Customer.io / Liquid `locale_key`):

| Column | Locale code | Language |
|--------|-------------|----------|
| 1 | Key | (row key) |
| 2 | en | English |
| 3 | ar | Arabic |
| 4 | zh-cn | Chinese Simplified |
| 5 | zh-tw | Chinese Traditional |
| 6 | zh-hk | Chinese Traditional, Hong Kong |
| 7 | hr | Croatian |
| 8 | cs | Czech |
| 9 | da | Danish |
| 10 | nl | Dutch |
| 11 | en-gb | English, United Kingdom |
| 12 | fil | Filipino |
| 13 | fi | Finnish |
| 14 | fr | French |
| 15 | fr-ca | French, Canada |
| 16 | de | German |
| 17 | el | Greek |
| 18 | he | Hebrew |
| 19 | hu | Hungarian |
| 20 | id | Indonesian |
| 21 | it | Italian |
| 22 | ja | Japanese |
| 23 | ko | Korean |
| 24 | ms | Malay |
| 25 | no | Norwegian |
| 26 | pl | Polish |
| 27 | pt | Portuguese |
| 28 | pt-br | Portuguese, Brazilian |
| 29 | ro | Romanian |
| 30 | ru | Russian |
| 31 | es | Spanish |
| 32 | es-419 | Spanish, Latin America |
| 33 | sv | Swedish |
| 34 | th | Thai |
| 35 | tr | Turkish |
| 36 | uk | Ukrainian |
| 37 | vi | Vietnamese |

---

## Row keys (content)

Use these **Key** values in the first column. Fill every locale column for translatable copy; for structure keys only one column (e.g. **en**) needs a value.

### Translatable (fill all locale columns)

| Key | Description |
|-----|-------------|
| subject_line | Email subject / `<title>` |
| preheader | Preheader text (hidden preview) |
| headline | Main H1 above the hero image |
| headline_2 | Optional second headline line |
| secondary_headline | Optional subheadline |
| body_1 | First body paragraph |
| body_2 | Second body paragraph |
| cta_text | CTA button label |
| app_download_title | **[Optional]** App download module title (e.g. "Stay in the loop on the Vio app"). If present, renders the purple app download card. |
| app_download_feature_1 | **[Optional]** First feature with checkmark (e.g. "Find extra savings") |
| app_download_feature_2 | **[Optional]** Second feature (e.g. "Manage your reservations") |
| app_download_feature_3 | **[Optional]** Third feature (e.g. "Track prices") |
| hero_two_col_body_1_h2 … hero_two_col_body_4_h2 | **[Optional]** Headings for feature blocks (when using `hero_module_two_column`) |
| hero_two_col_body_1_copy … hero_two_col_body_4_copy | **[Optional]** Body copy for feature blocks |
| hero_two_col_cta_text | **[Optional]** CTA button label for feature module (e.g. "Freeze a deal") |

### Structure (same for all languages – fill only one column, e.g. **en**)

| Key | Description |
|-----|-------------|
| image_url | Hero image URL (used on desktop and as fallback on mobile) |
| image_url_mobile | Optional: different image for mobile screens. If empty, uses `image_url` |
| image_deeplink | URL when clicking the hero image |
| cta_link | CTA button URL |
| cta_alias | `data-cio-tag` for the CTA (e.g. `hero-cta`) |
| app_store_rating | **[Optional]** App Store rating text (e.g. "4.9 · 9,319 reviews"). Default: 4.9 · 9,319 reviews |
| google_play_rating | **[Optional]** Google Play rating text (e.g. "4.7 · 6,308 reviews"). Default: 4.7 · 6,308 reviews |
| app_download_colour_preset | **Toggle** `LIGHT` (#fcf7f5) or `DARK` (#7130c9). Set via `--app-download-colour-preset` or merge field. |
| app_download_colour | **[Optional]** Override via merge field (hex, e.g. `#5700a9`) to bypass preset. |
| hero_two_col_image_1_url … hero_two_col_image_4_url | **[Optional]** Image URLs for feature blocks (when using `hero_module_two_column`). CSV keys: `image_1_URL`, `image_2_URL`, etc. |

---

## Example (minimal)

```csv
Key,en,ar,zh-cn,zh-tw,zh-hk,hr,cs,da,nl,en-gb,fil,fi,fr,fr-ca,de,el,he,hu,id,it,ja,ko,ms,no,pl,pt,pt-br,ro,ru,es,es-419,sv,th,tr,uk,vi
subject_line,See the full picture,عرض الصورة الكاملة,全景比价 一目了然,查看完整價格資訊,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...
preheader,Up front with no hidden fees.,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...
headline,Compare prices across 100+ sites,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...
body_1,With Vio's transparent pricing you can see the full picture...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...
body_2,Don't book hoping you got a good deal – know that you did.,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...
cta_text,Explore deals,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...,...
image_url,https://example.com/hero.jpg,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
image_deeplink,https://app.vio.com/,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
cta_link,https://app.vio.com/,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
cta_alias,hero-cta,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
```

---

## Example (module format)

```csv
Key,Module,module_index,en,ar,zh-cn,...
subject_line,hero_module,1,Price frozen, pressure off.,تم تثبيت السعر،...
preheader,hero_module,1,Lock in today's price for free,...
headline,hero_module,1,Freeze deals for free,...
body_1,hero_module,1,With Vio, you can lock in...,...
cta_text,hero_module,1,Freeze a deal,...
image_url,hero_module,1,https://example.com/hero.jpg,,,...
cta_link,hero_module,1,https://app.vio.com/,...
headline,app_download_module,2,<b>Stay in the loop</b> on the Vio app,...
colour,app_download_module,2,#7130c9,#7130c9,#7130c9,...
```

## Example (hero_module_two_column)

```csv
Key,Module,module_index,en
subject_line,hero_module_two_column,1,Welcome to Vio
preheader,hero_module_two_column,1,You're in. Time to book like an insider.
headline,hero_module_two_column,1,Time to start booking like an insider.
subheadline,hero_module_two_column,1,Welcome to Vio
body_1_h2,hero_module_two_column,1,Compare prices across 100+ sites
body_1_copy,hero_module_two_column,1,See the full picture upfront.
image_1_URL,hero_module_two_column,1,https://example.com/price-comparison.jpg
body_2_h2,hero_module_two_column,1,Know exactly when to book
body_2_copy,hero_module_two_column,1,Price insights show you the right moment.
image_2_URL,hero_module_two_column,1,https://example.com/price-insights.jpg
body_3_h2,hero_module_two_column,1,Stay ahead of price changes
body_3_copy,hero_module_two_column,1,We track prices so you don't have to.
image_3_URL,hero_module_two_column,1,https://example.com/price-alerts.jpg
body_4_h2,hero_module_two_column,1,Freeze deals for free
body_4_copy,hero_module_two_column,1,Lock in today's price while you decide.
image_4_URL,hero_module_two_column,1,https://example.com/deal-freeze.jpg
cta_text,hero_module_two_column,1,Freeze a deal
hero_image_url,hero_module_two_column,1,https://example.com/hero.jpg
image_deeplink,hero_module_two_column,1,https://app.vio.com/
cta_link,hero_module_two_column,1,https://app.vio.com/
cta_alias,hero_module_two_column,1,hero-cta
headline,app_download_module,2,Stay in the loop on the Vio app
```

---

## Tips

- **Google Sheets:** Use the first row for headers. Freeze the Key column so you can scroll locale columns.
- **Missing locale:** If a cell is empty, the script falls back to **en** for that key.
- **Optional rows:** Omit `headline_2` or `secondary_headline` if you don’t use them; the template will skip them.
- **CSV export:** File → Download → Comma-separated values (.csv). Use UTF-8 if you have non-ASCII characters.
