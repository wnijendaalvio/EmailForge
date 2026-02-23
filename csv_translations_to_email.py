#!/usr/bin/env python3
"""
Generate a single Customer.io email template with all locales from a translations CSV.
CSV: one row per content key (Key, en, ar, zh-cn, ...). See SHEET_STRUCTURE_TRANSLATIONS.md.
Usage:
  python3 csv_translations_to_email.py email_translations.csv > full_email_template.liquid
"""
import argparse
import csv
import re
import sys
import tempfile
from pathlib import Path

# Locale columns in sheet order (Key is column 0). Must match Liquid locale_key.
LOCALE_COLUMNS = [
    "en", "ar", "zh-cn", "zh-tw", "zh-hk", "hr", "cs", "da", "nl", "en-gb",
    "fil", "fi", "fr", "fr-ca", "de", "el", "he", "hu", "id", "it", "ja", "ko",
    "ms", "no", "pl", "pt", "pt-br", "ro", "ru", "es", "es-419", "sv", "th",
    "tr", "uk", "vi",
]

# Locale presets for "which languages to include"
LOCALE_PRESET_EN_ONLY = ["en"]
LOCALE_PRESET_TOP_5 = ["en", "es", "fr", "ja", "ar", "pt-br"]  # EN + Spanish, French, Japanese, Arabic, Portuguese
LOCALE_PRESET_GLOBAL = list(LOCALE_COLUMNS)


def resolve_include_locales(
    preset: str,
    custom: list[str] | None = None,
) -> list[str]:
    """Resolve include_locales from preset name or custom list. Always includes 'en' if custom."""
    if preset == "custom" and custom:
        result = list(dict.fromkeys(custom))  # preserve order, dedupe
        if "en" not in result:
            result = ["en"] + result
        return [l for l in result if l in LOCALE_COLUMNS]
    if preset == "en_only":
        return LOCALE_PRESET_EN_ONLY
    if preset == "top_5":
        return LOCALE_PRESET_TOP_5
    if preset == "global":
        return LOCALE_PRESET_GLOBAL
    return LOCALE_PRESET_EN_ONLY

TRANSLATABLE_KEYS = [
    "subject_line", "preheader", "headline", "headline_2", "secondary_headline",
    "body_1", "body_2", "cta_text",
    "app_download_title", "app_download_feature_1", "app_download_feature_2", "app_download_feature_3",
    "hero_two_col_body_1_h2", "hero_two_col_body_1_copy", "hero_two_col_body_2_h2", "hero_two_col_body_2_copy",
    "hero_two_col_body_3_h2", "hero_two_col_body_3_copy", "hero_two_col_body_4_h2", "hero_two_col_body_4_copy",
    "hero_two_col_cta_text",
    "terms_title", "terms_desc_text", "terms_label", "privacy_label",
    "usp_title", "usp_1_heading", "usp_1_copy", "usp_2_heading", "usp_2_copy",
    "usp_3_heading", "usp_3_copy",
    "usp_feature_title", "usp_feature_1_heading", "usp_feature_1_copy",
    "usp_feature_2_heading", "usp_feature_2_copy", "usp_feature_3_heading", "usp_feature_3_copy",
    "usp_ui_title", "usp_ui_1_heading", "usp_ui_1_copy",
    "usp_ui_2_heading", "usp_ui_2_copy", "usp_ui_3_heading", "usp_ui_3_copy",
]
STRUCTURE_KEYS = [
    "image_url", "image_url_mobile", "image_deeplink", "cta_link", "cta_alias",
    "app_store_rating", "google_play_rating", "app_download_colour",
    "hero_two_col_image_1_url", "hero_two_col_image_2_url", "hero_two_col_image_3_url", "hero_two_col_image_4_url",
    "usp_1_icon_url", "usp_2_icon_url", "usp_3_icon_url",
    "usp_feature_1_image_url", "usp_feature_2_image_url", "usp_feature_3_image_url",
    "usp_ui_1_image_url", "usp_ui_2_image_url", "usp_ui_3_image_url",
]

# Map (module, key) -> internal key for new CSV format with Module + module_index columns
MODULE_KEY_MAP = {
    ("hero_module", "subject_line"): "subject_line",
    ("hero_module", "preheader"): "preheader",
    ("hero_module", "headline"): "headline",
    ("hero_module", "body_1"): "body_1",
    ("hero_module", "body_2"): "body_2",
    ("hero_module", "cta_text"): "cta_text",
    ("hero_module", "image_url"): "image_url",
    ("hero_module", "image_url_mobile"): "image_url_mobile",
    ("hero_module", "image_deeplink"): "image_deeplink",
    ("hero_module", "cta_link"): "cta_link",
    ("hero_module", "cta_alias"): "cta_alias",
    ("hero_module_two_column", "subject_line"): "subject_line",
    ("hero_module_two_column", "preheader"): "preheader",
    ("hero_module_two_column", "headline"): "headline",
    ("hero_module_two_column", "subheadline"): "secondary_headline",
    ("hero_module_two_column", "body_1_h2"): "hero_two_col_body_1_h2",
    ("hero_module_two_column", "body_1_copy"): "hero_two_col_body_1_copy",
    ("hero_module_two_column", "image_1_url"): "hero_two_col_image_1_url",
    ("hero_module_two_column", "body_2_h2"): "hero_two_col_body_2_h2",
    ("hero_module_two_column", "body_2_copy"): "hero_two_col_body_2_copy",
    ("hero_module_two_column", "image_2_url"): "hero_two_col_image_2_url",
    ("hero_module_two_column", "body_3_h2"): "hero_two_col_body_3_h2",
    ("hero_module_two_column", "body_3_copy"): "hero_two_col_body_3_copy",
    ("hero_module_two_column", "image_3_url"): "hero_two_col_image_3_url",
    ("hero_module_two_column", "body_4_h2"): "hero_two_col_body_4_h2",
    ("hero_module_two_column", "body_4_copy"): "hero_two_col_body_4_copy",
    ("hero_module_two_column", "image_4_url"): "hero_two_col_image_4_url",
    ("hero_module_two_column", "cta_text"): "hero_two_col_cta_text",
    ("hero_module_two_column", "hero_image_url"): "image_url",
    ("hero_module_two_column", "image_deeplink"): "image_deeplink",
    ("hero_module_two_column", "cta_link"): "cta_link",
    ("hero_module_two_column", "cta_alias"): "cta_alias",
    ("app_download_module", "headline"): "app_download_title",
    ("app_download_module", "feature_1"): "app_download_feature_1",
    ("app_download_module", "feature_2"): "app_download_feature_2",
    ("app_download_module", "feature_3"): "app_download_feature_3",
    ("app_download_module", "colour"): "app_download_colour",
    ("app_download_module", "color"): "app_download_colour",
    ("disclaimer_module", "terms_title"): "terms_title",
    ("disclaimer_module", "terms_desc"): "terms_desc_text",
    ("disclaimer_module", "terms_desc_text"): "terms_desc_text",
    ("disclaimer_module", "terms_label"): "terms_label",
    ("disclaimer_module", "privacy_label"): "privacy_label",
    ("icon_left_text_right_module", "title"): "usp_title",
    ("icon_left_text_right_module", "usp_1_heading"): "usp_1_heading",
    ("icon_left_text_right_module", "usp_1_copy"): "usp_1_copy",
    ("icon_left_text_right_module", "usp_1_icon_url"): "usp_1_icon_url",
    ("icon_left_text_right_module", "usp_2_heading"): "usp_2_heading",
    ("icon_left_text_right_module", "usp_2_copy"): "usp_2_copy",
    ("icon_left_text_right_module", "usp_2_icon_url"): "usp_2_icon_url",
    ("icon_left_text_right_module", "usp_3_heading"): "usp_3_heading",
    ("icon_left_text_right_module", "usp_3_copy"): "usp_3_copy",
    ("icon_left_text_right_module", "usp_3_icon_url"): "usp_3_icon_url",
    ("text_left_image_right_module", "title"): "usp_feature_title",
    ("text_left_image_right_module", "usp_feature_1_heading"): "usp_feature_1_heading",
    ("text_left_image_right_module", "usp_feature_1_copy"): "usp_feature_1_copy",
    ("text_left_image_right_module", "usp_feature_1_image_url"): "usp_feature_1_image_url",
    ("text_left_image_right_module", "usp_feature_2_heading"): "usp_feature_2_heading",
    ("text_left_image_right_module", "usp_feature_2_copy"): "usp_feature_2_copy",
    ("text_left_image_right_module", "usp_feature_2_image_url"): "usp_feature_2_image_url",
    ("text_left_image_right_module", "usp_feature_3_heading"): "usp_feature_3_heading",
    ("text_left_image_right_module", "usp_feature_3_copy"): "usp_feature_3_copy",
    ("text_left_image_right_module", "usp_feature_3_image_url"): "usp_feature_3_image_url",
    ("alternating_text_image_module", "title"): "usp_ui_title",
    ("alternating_text_image_module", "usp_ui_1_heading"): "usp_ui_1_heading",
    ("alternating_text_image_module", "usp_ui_1_copy"): "usp_ui_1_copy",
    ("alternating_text_image_module", "usp_ui_1_image_url"): "usp_ui_1_image_url",
    ("alternating_text_image_module", "usp_ui_2_heading"): "usp_ui_2_heading",
    ("alternating_text_image_module", "usp_ui_2_copy"): "usp_ui_2_copy",
    ("alternating_text_image_module", "usp_ui_2_image_url"): "usp_ui_2_image_url",
    ("alternating_text_image_module", "usp_ui_3_heading"): "usp_ui_3_heading",
    ("alternating_text_image_module", "usp_ui_3_copy"): "usp_ui_3_copy",
    ("alternating_text_image_module", "usp_ui_3_image_url"): "usp_ui_3_image_url",
}

PLACEHOLDER_DESIGN_TOKENS = "{{ DESIGN_TOKENS }}"
PLACEHOLDER_APP_DOWNLOAD_SETTINGS = "{{ APP_DOWNLOAD_SETTINGS }}"
PLACEHOLDER_CONTENT_CAPTURES = "{{ CONTENT_CAPTURES }}"
PLACEHOLDER_ROWS_ABOVE_IMAGE = "{{ ROWS_ABOVE_IMAGE }}"
PLACEHOLDER_IMAGE_ROW = "{{ IMAGE_ROW }}"
PLACEHOLDER_ROWS_BELOW_IMAGE = "{{ ROWS_BELOW_IMAGE }}"
PLACEHOLDER_HERO_TWO_COLUMN_MODULE = "{{ HERO_TWO_COLUMN_MODULE }}"
PLACEHOLDER_APP_DOWNLOAD_MODULE = "{{ APP_DOWNLOAD_MODULE }}"
PLACEHOLDER_ICON_LEFT_TEXT_RIGHT_MODULE = "{{ ICON_LEFT_TEXT_RIGHT_MODULE }}"
PLACEHOLDER_TEXT_LEFT_IMAGE_RIGHT_MODULE = "{{ TEXT_LEFT_IMAGE_RIGHT_MODULE }}"
PLACEHOLDER_ALTERNATING_TEXT_IMAGE_MODULE = "{{ ALTERNATING_TEXT_IMAGE_MODULE }}"
PLACEHOLDER_CONFIG = "{{ CONFIG_BLOCK }}"
PLACEHOLDER_LINKS = "{{ LINKS_BLOCK }}"
PLACEHOLDER_TERMS_DEFAULTS = "{{ TERMS_DEFAULTS_BLOCK }}"

# Rows for each module in standard input template (csv_key, en_placeholder).
# Structure keys get link hints; translatable get empty or example.
MODULE_TEMPLATE_ROWS = {
    "hero_module": [
        ("subject_line", ""),
        ("preheader", ""),
        ("headline", ""),
        ("body_1", ""),
        ("body_2", ""),
        ("cta_text", ""),
        ("image_url", ""),
        ("image_url_mobile", ""),
        ("image_deeplink", ""),
        ("cta_link", ""),
        ("cta_alias", "hero-cta"),
    ],
    "hero_module_two_column": [
        ("subject_line", ""),
        ("preheader", ""),
        ("headline", ""),
        ("subheadline", ""),
        ("body_1_h2", ""),
        ("body_1_copy", ""),
        ("image_1_URL", ""),
        ("body_2_h2", ""),
        ("body_2_copy", ""),
        ("image_2_URL", ""),
        ("body_3_h2", ""),
        ("body_3_copy", ""),
        ("image_3_URL", ""),
        ("body_4_h2", ""),
        ("body_4_copy", ""),
        ("image_4_URL", ""),
        ("cta_text", ""),
        ("hero_image_url", ""),
        ("image_deeplink", ""),
        ("cta_link", ""),
        ("cta_alias", "hero-cta"),
    ],
    "app_download_module": [
        ("headline", ""),
        ("feature_1", ""),
        ("feature_2", ""),
        ("feature_3", ""),
        ("colour", "#fcf7f5"),
    ],
    "disclaimer_module": [
        ("terms_title", ""),
        ("terms_desc", ""),
        ("terms_label", ""),
        ("privacy_label", ""),
    ],
    "icon_left_text_right_module": [
        ("title", "How Vio helps you book like an insider"),
        ("usp_1_heading", "Compare prices across 100+ sites"),
        ("usp_1_copy", "See the full picture upfront. No guessing, no bouncing between tabs."),
        ("usp_1_icon_url", ""),
        ("usp_2_heading", "Know exactly when to book"),
        ("usp_2_copy", "Price insights show you the right moment to secure your deal."),
        ("usp_2_icon_url", ""),
        ("usp_3_heading", "Stay ahead of price changes"),
        ("usp_3_copy", "We track prices so you don't have to keep checking."),
        ("usp_3_icon_url", ""),
    ],
    "text_left_image_right_module": [
        ("title", "How Vio helps you book like an insider"),
        ("usp_feature_1_heading", "Compare prices across 100+ sites"),
        ("usp_feature_1_copy", "See the full picture upfront. No guessing, no bouncing between tabs."),
        ("usp_feature_1_image_url", ""),
        ("usp_feature_2_heading", "Know exactly when to book"),
        ("usp_feature_2_copy", "Price insights show you the right moment to secure your deal."),
        ("usp_feature_2_image_url", ""),
        ("usp_feature_3_heading", "Stay ahead of price changes"),
        ("usp_feature_3_copy", "We track prices so you don't have to keep checking."),
        ("usp_feature_3_image_url", ""),
    ],
    "alternating_text_image_module": [
        ("title", "How Vio helps you book like an insider"),
        ("usp_ui_1_heading", "Compare prices across 100+ sites"),
        ("usp_ui_1_copy", "See the full picture upfront. No guessing, no bouncing between tabs."),
        ("usp_ui_1_image_url", ""),
        ("usp_ui_2_heading", "Know exactly when to book"),
        ("usp_ui_2_copy", "Price insights show you the right moment to secure your deal."),
        ("usp_ui_2_image_url", ""),
        ("usp_ui_3_heading", "Stay ahead of price changes"),
        ("usp_ui_3_copy", "We track prices so you don't have to keep checking."),
        ("usp_ui_3_image_url", ""),
    ],
}


DESIGN_TOKENS_BRANDS = ("vio", "holiday_pirates", "kiwi")


def _get_design_tokens_path(brand: str) -> Path:
    """Return path to design tokens file for the given brand."""
    base = Path(__file__).parent
    if brand == "holiday_pirates":
        return base / "design_tokens_holiday_pirates.liquid"
    if brand == "kiwi":
        return base / "design_tokens_kiwi.liquid"
    return base / "design_tokens.liquid"


def _load_design_tokens(brand: str = "vio") -> str:
    """Load design tokens from brand-specific file to inject into template."""
    tokens_path = _get_design_tokens_path(brand)
    if tokens_path.exists():
        return tokens_path.read_text(encoding="utf-8").strip()
    return ""


def _escape_liquid_raw(s: str) -> str:
    """Escape text so it can be embedded in Liquid capture without breaking tags."""
    if not s:
        return ""
    s = s.replace("{%", "{{ '{%' }}")
    s = s.replace("%}", "{{ '%}' }}")
    return s


def _html_escape(s: str) -> str:
    s = (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    return s


def _normalise_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if "://" not in url:
        return "https://" + url
    return url


def get_csv_locales(csv_path: Path) -> list[str]:
    """Infer locale columns from CSV headers. Returns locale codes found, in LOCALE_COLUMNS order."""
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        if csv_path.suffix.lower() == ".tsv":
            reader = csv.DictReader(f, delimiter="\t")
        else:
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t")
            except csv.Error:
                dialect = csv.excel
            reader = csv.DictReader(f, dialect=dialect)
        fields = reader.fieldnames or []
    use_module_format = (
        len(fields) >= 3
        and (fields[1] or "").strip().lower() == "module"
        and (fields[2] or "").strip().lower().replace(" ", "") == "module_index"
    )
    locale_start = 3 if use_module_format else 1
    locale_headers = [h for h in fields[locale_start:] if (h or "").strip()]
    header_norms = {h.strip(): h for h in locale_headers}
    found: list[str] = []
    for loc in LOCALE_COLUMNS:
        norm = loc.replace("-", "_").lower()
        for key in header_norms:
            knorm = key.lower().replace("-", "_").replace(" ", "")
            if loc == key or norm == knorm:
                found.append(loc)
                break
    if not found and locale_headers:
        for i, h in enumerate(locale_headers):
            hc = (h or "").strip()
            if hc in LOCALE_COLUMNS:
                found.append(hc)
    return found if found else ["en"]


def load_translations(
    csv_path: Path,
    include_locales: list[str] | None = None,
) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    """
    Read CSV or TSV. Supports two formats:
    A) Legacy: Key, en, ar, ... (locale columns at index 1+)
    B) New: Key, Module, module_index, en, ar, ... (locale columns at index 3+)
    include_locales: if None, infers from CSV headers via get_csv_locales.
    Return (translations[key][locale] = value, structure[key] = single_value).
    """
    locales = include_locales or get_csv_locales(csv_path)
    translations: dict[str, dict[str, str]] = {}
    structure: dict[str, str] = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        if csv_path.suffix.lower() == ".tsv":
            reader = csv.DictReader(f, delimiter="\t")
        else:
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t")
            except csv.Error:
                dialect = csv.excel
            reader = csv.DictReader(f, dialect=dialect)
        if not reader.fieldnames:
            return translations, structure
        fields = reader.fieldnames
        use_module_format = (
            len(fields) >= 3
            and (fields[1] or "").strip().lower() == "module"
            and (fields[2] or "").strip().lower().replace(" ", "") == "module_index"
        )
        locale_start = 3 if use_module_format else 1
        locale_headers = fields[locale_start:]
        locale_to_header: dict[str, str] = {}
        for loc in locales:
            for h in locale_headers:
                if not h:
                    continue
                hnorm = h.strip().lower().replace(" ", "").replace("_", "-")
                if loc == hnorm or loc.replace("-", "_") == hnorm.replace("-", "_"):
                    locale_to_header[loc] = h
                    break
            if loc not in locale_to_header and loc in LOCALE_COLUMNS:
                idx = LOCALE_COLUMNS.index(loc)
                if idx < len(locale_headers) and (locale_headers[idx] or "").strip():
                    locale_to_header[loc] = locale_headers[idx].strip()
        key_col = fields[0]
        module_col = fields[1] if use_module_format and len(fields) >= 2 else None

        for row in reader:
            key_raw = (row.get(key_col) or "").strip().lower().replace(" ", "")
            if not key_raw:
                continue
            module_raw = (row.get(module_col, "") or "").strip().lower().replace(" ", "") if module_col else ""
            values_by_locale: dict[str, str] = {}
            for loc in locales:
                header = locale_to_header.get(loc)
                val = (row.get(header, "") if header else "").strip()
                values_by_locale[loc] = val

            if use_module_format and module_raw:
                internal_key = MODULE_KEY_MAP.get((module_raw, key_raw))
                if internal_key is None:
                    internal_key = MODULE_KEY_MAP.get((module_raw, key_raw.replace("_", "")))
                if internal_key is None:
                    continue
            else:
                internal_key = key_raw

            if internal_key in STRUCTURE_KEYS:
                for loc in locales:
                    v = values_by_locale.get(loc, "").strip()
                    if v:
                        structure[internal_key] = v
                        break
                if internal_key not in structure:
                    structure[internal_key] = values_by_locale.get("en", "").strip()
            else:
                en_val = values_by_locale.get("en", "").strip()
                for loc in locales:
                    if not values_by_locale.get(loc, "").strip():
                        values_by_locale[loc] = en_val
                translations[internal_key] = values_by_locale
    return translations, structure


def build_content_captures(
    translations: dict[str, dict[str, str]],
    include_locales: list[str] | None = None,
) -> str:
    """Generate Liquid {% capture key %} {% case locale_key %} ... {% endcapture %} for each key.
    include_locales: only output when clauses for these locales (default: all LOCALE_COLUMNS)."""
    locales = include_locales or LOCALE_COLUMNS
    lines = []
    for key in TRANSLATABLE_KEYS:
        if key not in translations:
            continue
        vals = translations[key]
        lines.append("{%- capture " + key + " -%}")
        lines.append("  {%- case locale_key -%}")
        for loc in locales:
            v = vals.get(loc, "").strip() or vals.get("en", "").strip()
            v_esc = _escape_liquid_raw(v)
            lines.append('    {%- when "' + loc + '" -%}' + v_esc)
        lines.append('    {%- else -%}' + _escape_liquid_raw(vals.get("en", "").strip()))
        lines.append("  {%- endcase -%}")
        lines.append("{%- endcapture -%}")
    return "\n".join(lines)


def build_rows_above_image(translations: dict[str, dict[str, str]]) -> str:
    """HTML rows for headline(s) using Liquid variables.
    When hero_module_two_column is used: subheadline above headline, centered, subheadline 30px bold."""
    has_headline = "headline" in translations
    has_h2 = "headline_2" in translations
    has_sh = "secondary_headline" in translations
    if not (has_headline or has_h2 or has_sh):
        return ""
    is_two_col = "hero_two_col_body_1_h2" in translations
    parts = ["<tr>"]
    if is_two_col:
        # hero_module_two_column: subheadline first (30px bold), then headline (48px, larger, no background)
        parts.append('  <td style="padding:{{ token_space_300 }} 0 {{ token_space_500 }};text-align:center;direction:{{ dir }};">')
        if has_sh:
            parts.append('    <p style="margin:0;font-family:{{ token_font_stack }};font-weight:700;font-size:30px;line-height:120%;letter-spacing:0;color:{{ token_neutral_c900 }};direction:{{ dir }};unicode-bidi:plaintext;">{{ secondary_headline | strip }}</p>')
        if has_headline:
            parts.append('    <table role="presentation" width="498" cellpadding="0" cellspacing="0" border="0" align="center" class="email-hero-two-col-headline-box" style="margin:{{ token_space_300 }} auto 0 auto;width:498px;max-width:100%;height:116px;border-collapse:collapse;"><tr><td align="center" valign="middle" style="padding:0;vertical-align:middle;height:116px;">')
            parts.append('      <h1 style="margin:0;font-family:{{ token_font_stack }};font-weight:700;font-size:48px;line-height:120%;letter-spacing:0;color:{{ token_accent }};text-align:center;direction:{{ dir }};unicode-bidi:plaintext;">{{ headline | strip }}</h1>')
            parts.append('    </td></tr></table>')
    else:
        parts.append('  <td style="padding: {{ token_space_300 }} 0 {{ token_space_500 }}; text-align: {{ headline_align }}; direction: {{ dir }};">')
        if has_headline:
            parts.append('    <h1 style="margin:0;font-family:{{ token_font_stack }};font-size:32px;line-height:38px;color:{{ token_accent }};font-weight:600;direction:{{ dir }};unicode-bidi:plaintext;">{{ headline | strip }}</h1>')
        if has_h2:
            parts.append('    <p style="margin:{{ token_space_500 }} 0 0 0;font-family:{{ token_font_stack }};font-size:22px;line-height:28px;font-weight:600;color:{{ token_accent }};direction:{{ dir }};unicode-bidi:plaintext;">{{ headline_2 | strip }}</p>')
        if has_sh:
            parts.append('    <p style="margin:{{ token_space_500 }} 0 0 0;font-family:{{ token_font_stack }};font-size:16px;line-height:22px;font-weight:450;color:{{ token_text_primary }};direction:{{ dir }};unicode-bidi:plaintext;">{{ secondary_headline | strip }}</p>')
    parts.append("  </td>")
    parts.append("</tr>")
    return "\n".join(parts)


def build_image_row(structure: dict[str, str]) -> str:
    """Hero image row; optional mobile image from structure. Falls back to regular image if no mobile URL."""
    img_url = (structure.get("image_url") or "").strip()
    if not img_url:
        return ""
    img_mobile = (structure.get("image_url_mobile") or "").strip() or img_url
    img_link = _normalise_url(structure.get("image_deeplink") or "")
    img_attrs = 'width="728" alt="" style="display:block;width:100%;max-width:728px;height:auto;border:0;outline:none;text-decoration:none;"'
    wrap_a = lambda url: ('<a href="' + _html_escape(img_link) + '" target="_blank" style="display:block;text-decoration:none;border:0;outline:none;">' if img_link else "") + '<img src="' + _html_escape(url) + '" ' + img_attrs + ' />' + ("</a>" if img_link else "")
    if img_mobile != img_url:
        return (
            '<span class="email-img-desktop">' + wrap_a(img_url) + '</span>'
            '<span class="email-img-mobile">' + wrap_a(img_mobile) + '</span>'
        )
    if img_link:
        return '<a href="' + _html_escape(img_link) + '" target="_blank" style="display:block;text-decoration:none;border:0;outline:none;"><img src="' + _html_escape(img_url) + '" ' + img_attrs + ' /></a>'
    return '<img src="' + _html_escape(img_url) + '" ' + img_attrs + ' />'


def build_rows_below_image(translations: dict[str, dict[str, str]], structure: dict[str, str]) -> str:
    """Body + CTA rows using Liquid variables and structure (cta_link, cta_alias).
    Returns empty when hero_module_two_column content exists (feature blocks rendered separately)."""
    if "hero_two_col_body_1_h2" in translations:
        return ""
    has_body1 = "body_1" in translations
    has_body2 = "body_2" in translations
    has_cta = "cta_text" in translations
    cta_link = _normalise_url(structure.get("cta_link") or "")
    cta_alias = (structure.get("cta_alias") or "hero-cta").strip()
    parts = []
    if has_body1 or has_body2:
        parts.append("<tr>")
        parts.append('  <td style="padding:{{ token_space_700 }} 0 0;direction:{{ dir }};text-align:{{ align }};">')
        if has_body1:
            parts.append('    <p style="margin:0 0 {{ token_space_600 }} 0;font-size:16px;line-height:24px;color:{{ token_text_body }};font-weight:400;letter-spacing:normal;font-family:{{ token_font_stack }};direction:{{ dir }};unicode-bidi:plaintext;">{{ body_1 | strip }}</p>')
        if has_body2:
            parts.append('    <p style="margin:0 0 {{ token_space_600 }} 0;font-size:16px;line-height:24px;color:{{ token_text_body }};font-weight:400;letter-spacing:normal;font-family:{{ token_font_stack }};direction:{{ dir }};unicode-bidi:plaintext;">{{ body_2 | strip }}</p>')
        parts.append("  </td>")
        parts.append("</tr>")
    if has_cta and cta_link:
        parts.append("<tr>")
        parts.append('  <td align="center" style="padding:0 0 {{ token_space_600 }};">')
        parts.append('    <a href="' + _html_escape(cta_link) + '" target="_blank" data-cio-tag="' + _html_escape(cta_alias) + '" style="display:block;width:100%;background:{{ token_cta_bg }};color:{{ token_text_on_brand }};text-align:center;font-weight:600;font-size:16px;line-height:20px;padding:{{ token_space_400 }} 0;border-radius:8px;letter-spacing:normal;font-family:{{ token_font_stack }};text-decoration:none;">{{ cta_text | strip }}</a>')
        parts.append("  </td>")
        parts.append("</tr>")
    return "\n".join(parts)


def build_app_download_settings(structure: dict[str, str]) -> str:
    """Build Liquid block for app download colour + auto text colour. Uses app_download_colour_toggle (LIGHT/DARK).
    LIGHT = token_neutral_c050, DARK = token_brand_c600. Text: light bg → token_text_primary (black), dark bg → token_text_on_brand (white)."""
    return '''{%- assign _preset = app_download_colour_preset | default: app_download_colour_toggle | upcase | strip -%}
{%- assign _preset_colour = token_neutral_c050 -%}
{%- if _preset == "DARK" -%}{%- assign _preset_colour = token_brand_c600 -%}{%- endif -%}
{%- assign app_download_colour = app_download_colour | default: _preset_colour | downcase | replace: " ", "" -%}
{%- assign _app_bg = app_download_colour -%}
{%- assign app_download_text_colour = token_text_on_brand -%}
{%- if _app_bg == "#fcf7f5" or _app_bg == "#ffffff" or _app_bg == "#f8f5ff" or _app_bg == "#eee9e7" or _app_bg == "#ddd7d5" -%}
  {%- assign app_download_text_colour = token_text_primary -%}
{%- endif -%}
'''


def build_app_download_module(translations: dict[str, dict[str, str]], structure: dict[str, str]) -> str:
    """Optional app download module: card with headline and two store buttons with ratings side-by-side.
    Rendered only when app_download_title exists. Colour from app_download_colour (set at top); text colour auto-adapts."""
    if "app_download_title" not in translations:
        return ""
    app_rating = (structure.get("app_store_rating") or "4.9/5 · 8,000+ reviews").strip()
    google_rating = (structure.get("google_play_rating") or "4.6/5 · 11,000+ reviews").strip()
    star_url = "https://price-watch-email-images-explicit-prod-master.s3.eu-west-1.amazonaws.com/199cd19b/images/star-yellow.png"
    star_row = f'''<img alt="★" height="12" src="{star_url}" style="display:inline-block;outline:none;border:none;text-decoration:none;padding-right:2px" width="12"/>''' * 5
    return f'''{{%- if app_download_title != blank -%}}
<tr><td style="padding:0;vertical-align:top;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-app-module-outer" style="width:100%;margin-top:{{{{ token_space_600 }}}};">
  <tbody>
    <tr>
      <td align="center" style="padding:0;">
        <table align="center" width="588" border="0" cellpadding="0" cellspacing="0" role="presentation" class="email-app-card" style="width:588px;max-width:100%;background-color:{{{{ app_download_colour }}}};padding:{{{{ token_space_600 }}}} {{{{ token_space_900 }}}};color:{{{{ app_download_text_colour }}}};border-radius:{{{{ token_radius_module }}}};margin:0 auto {{{{ token_space_600 }}}} auto;text-align:left;box-sizing:border-box">
          <tbody>
            <tr>
              <td style="font-family:Campton, Circular, Helvetica, Arial, sans-serif;">
                <a href="{{{{ app_deeplink_url }}}}" data-cio-tag="AppBanner-emailPriceAlertBannerTitle" style="text-decoration:none;color:{{{{ app_download_text_colour }}}}">
                  <p style="font-size:20px;line-height:28px;font-weight:600;letter-spacing:normal;font-family:{{{{ token_font_stack }}}};text-align:left;margin:0;color:{{{{ app_download_text_colour }}}};padding-top:0;padding-bottom:{{{{ token_space_400 }}}};padding-right:0;padding-left:0;direction:{{{{ dir }}}};unicode-bidi:plaintext;">
                    {{{{ app_download_title | strip }}}}
                  </p>
                </a>
                <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" class="email-app-stores" style="border-collapse:collapse;width:100%">
                  <tr>
                    <td valign="middle" class="email-app-store-cell" style="width:50%;padding:0;padding-right:20px;vertical-align:middle">
                      <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="border-collapse:collapse">
                        <tr>
                          <td valign="middle" style="padding:0;vertical-align:middle">
                            <a href="{{{{ app_deeplink_url }}}}" data-cio-tag="AppBanner-apple-store-img" style="display:inline-block;text-decoration:none">
                              <img alt="Download on App Store" src="{{ app_store_badge_url }}" style="display:block;outline:none;border:none;text-decoration:none;max-height:40px" height="40"/>
                            </a>
                          </td>
                          <td valign="middle" style="padding-left:12px;vertical-align:middle">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="border-collapse:collapse">
                              <tr><td style="padding:0">{star_row}</td></tr>
                              <tr><td style="padding:2px 0 0 0;font-size:12px;line-height:16px;font-weight:450;font-family:{{{{ token_font_stack }}}};color:{{{{ app_download_text_colour }}}};letter-spacing:normal;direction:{{{{ dir }}}};unicode-bidi:plaintext;">{_html_escape(app_rating)}</td></tr>
                            </table>
                          </td>
                        </tr>
                      </table>
                    </td>
                    <td valign="middle" class="email-app-store-cell" style="width:50%;padding:0;vertical-align:middle">
                      <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="border-collapse:collapse">
                        <tr>
                          <td valign="middle" style="padding:0;vertical-align:middle">
                            <a href="{{{{ app_deeplink_url }}}}" data-cio-tag="AppBanner-google-store-img" style="display:inline-block;text-decoration:none">
                              <img alt="Get it on Google Play" src="{{ google_play_badge_url }}" style="display:block;outline:none;border:none;text-decoration:none;max-height:40px" height="40"/>
                            </a>
                          </td>
                          <td valign="middle" style="padding-left:12px;vertical-align:middle">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="border-collapse:collapse">
                              <tr><td style="padding:0">{star_row}</td></tr>
                              <tr><td style="padding:2px 0 0 0;font-size:12px;line-height:16px;font-weight:450;font-family:{{{{ token_font_stack }}}};color:{{{{ app_download_text_colour }}}};letter-spacing:normal;direction:{{{{ dir }}}};unicode-bidi:plaintext;">{_html_escape(google_rating)}</td></tr>
                            </table>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </tbody>
        </table>
      </td>
    </tr>
  </tbody>
</table>
</td></tr>
{{%- endif -%}}'''


def build_hero_two_column_module(translations: dict[str, dict[str, str]], structure: dict[str, str]) -> str:
    """Optional two-column feature module: 4 alternating text/image blocks + CTA.
    Rendered only when hero_two_col_body_1_h2 exists. Uses design tokens for styling."""
    if "hero_two_col_body_1_h2" not in translations:
        return ""
    img1 = _normalise_url(structure.get("hero_two_col_image_1_url") or "")
    img2 = _normalise_url(structure.get("hero_two_col_image_2_url") or "")
    img3 = _normalise_url(structure.get("hero_two_col_image_3_url") or "")
    img4 = _normalise_url(structure.get("hero_two_col_image_4_url") or "")
    cta_link = _normalise_url(structure.get("cta_link") or "")
    cta_alias = (structure.get("cta_alias") or "hero-two-col-cta").strip()
    # Typography: Campton, 16px, line-height 24px, letter-spacing 0.01em, #0F0E0F; horizontal align (left/right for RTL), vertically centred via valign
    text_style = "margin:0 0 12px 0;font-family:{{ token_font_stack }};font-weight:700;font-size:16px;line-height:24px;letter-spacing:0.01em;color:{{ token_text_primary }};text-align:{{ align }};direction:{{ dir }};unicode-bidi:plaintext;"
    body_style = "margin:0;font-family:{{ token_font_stack }};font-weight:400;font-size:16px;line-height:24px;letter-spacing:0.01em;color:{{ token_text_primary }};text-align:{{ align }};direction:{{ dir }};unicode-bidi:plaintext;"
    cta_href = _html_escape(cta_link) if cta_link else "#"
    cta_tag = _html_escape(cta_alias)
    return f'''{{%- if hero_two_col_body_1_h2 != blank -%}}
<tr><td style="padding:0;vertical-align:top;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-feature-module-outer" style="width:100%;margin-top:{{{{ token_space_900 }}}}">
  <tbody>
    <tr>
      <td>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;border-collapse:collapse;">
          <tr class="email-feature-row">
            <td width="50%" valign="middle" class="email-feature-col" style="padding:0 20px 32px 0;vertical-align:middle;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr><td>
                  <h2 style="{text_style}">{{{{ hero_two_col_body_1_h2 | strip }}}}</h2>
                  <p style="{body_style}">{{{{ hero_two_col_body_1_copy | strip }}}}</p>
                </td></tr>
              </table>
            </td>
            <td width="50%" valign="middle" class="email-feature-col" style="padding:0 0 32px 20px;vertical-align:middle;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr><td align="center">
                  <img src="{_html_escape(img1)}" alt="{{{{ hero_two_col_body_1_h2 | strip }}}}" width="260" height="180" style="display:block;max-width:100%;height:auto;" />
                </td></tr>
              </table>
            </td>
          </tr>
          <tr class="email-feature-row">
            <td width="50%" valign="middle" class="email-feature-col" style="padding:0 20px 32px 0;vertical-align:middle;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr><td align="center">
                  <img src="{_html_escape(img2)}" alt="{{{{ hero_two_col_body_2_h2 | strip }}}}" width="260" height="180" style="display:block;max-width:100%;height:auto;" />
                </td></tr>
              </table>
            </td>
            <td width="50%" valign="middle" class="email-feature-col" style="padding:0 0 32px 20px;vertical-align:middle;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr><td>
                  <h2 style="{text_style}">{{{{ hero_two_col_body_2_h2 | strip }}}}</h2>
                  <p style="{body_style}">{{{{ hero_two_col_body_2_copy | strip }}}}</p>
                </td></tr>
              </table>
            </td>
          </tr>
          <tr class="email-feature-row">
            <td width="50%" valign="middle" class="email-feature-col" style="padding:0 20px 32px 0;vertical-align:middle;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr><td>
                  <h2 style="{text_style}">{{{{ hero_two_col_body_3_h2 | strip }}}}</h2>
                  <p style="{body_style}">{{{{ hero_two_col_body_3_copy | strip }}}}</p>
                </td></tr>
              </table>
            </td>
            <td width="50%" valign="middle" class="email-feature-col" style="padding:0 0 32px 20px;vertical-align:middle;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr><td align="center">
                  <img src="{_html_escape(img3)}" alt="{{{{ hero_two_col_body_3_h2 | strip }}}}" width="260" height="180" style="display:block;max-width:100%;height:auto;" />
                </td></tr>
              </table>
            </td>
          </tr>
          <tr class="email-feature-row">
            <td width="50%" valign="middle" class="email-feature-col" style="padding:0 20px 0 0;vertical-align:middle;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr><td align="center">
                  <img src="{_html_escape(img4)}" alt="{{{{ hero_two_col_body_4_h2 | strip }}}}" width="260" height="180" style="display:block;max-width:100%;height:auto;" />
                </td></tr>
              </table>
            </td>
            <td width="50%" valign="middle" class="email-feature-col" style="padding:0 0 0 20px;vertical-align:middle;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr><td>
                  <h2 style="{text_style}">{{{{ hero_two_col_body_4_h2 | strip }}}}</h2>
                  <p style="{body_style}">{{{{ hero_two_col_body_4_copy | strip }}}}</p>
                </td></tr>
              </table>
            </td>
          </tr>
        </table>
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" class="email-hero-two-col-cta-wrap" style="width:600px;max-width:100%;margin-top:{{{{ token_space_900 }}}};">
          <tr>
            <td class="email-hero-two-col-cta-cell" style="padding:{{{{ token_space_600 }}}} 0 0 0;width:600px;">
              <a href="{cta_href}" target="_blank" data-cio-tag="{cta_tag}" class="email-hero-two-col-cta" style="display:block;width:600px;max-width:100%;min-height:52px;box-sizing:border-box;background:{{{{ token_cta_bg }}}};color:{{{{ token_text_on_brand }}}};text-align:center;font-weight:600;font-size:16px;line-height:20px;padding:{{{{ token_space_400 }}}} 0;border-radius:8px;border-top:1.5px solid #000000;font-family:{{{{ token_font_stack }}}};text-decoration:none;">{{{{ hero_two_col_cta_text | strip }}}}</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </tbody>
</table>
</td></tr>
{{%- endif -%}}'''


def build_usp_module(translations: dict[str, dict[str, str]], structure: dict[str, str]) -> str:
    """USP module: title + 3 feature rows (icon, heading, copy). width 600, padding s800, gap 24, border-radius lg."""
    if "usp_title" not in translations:
        return ""
    icon1 = _normalise_url(structure.get("usp_1_icon_url") or "")
    icon2 = _normalise_url(structure.get("usp_2_icon_url") or "")
    icon3 = _normalise_url(structure.get("usp_3_icon_url") or "")
    # Placeholder icons when none provided (80x80 frame, light purple bg)
    placeholder = "https://placehold.co/80/f2e5ff/7130c9?text=•"
    icon1 = icon1 or placeholder
    icon2 = icon2 or placeholder
    icon3 = icon3 or placeholder

    def _usp_row(icon_url: str, heading_var: str, copy_var: str) -> str:
        return f'''            <tr>
              <td valign="top" style="padding:0 {{{{ token_space_600 }}}} {{{{ token_space_600 }}}} 0;vertical-align:top;width:80px;">
                <img src="{_html_escape(icon_url)}" alt="" width="80" height="80" style="display:block;max-width:80px;max-height:80px;object-fit:contain;" />
              </td>
              <td valign="top" style="padding:0 0 {{{{ token_space_600 }}}} 0;vertical-align:top;">
                <p style="margin:0;font-family:{{{{ token_font_stack }}}};font-weight:700;font-size:{{{{ token_font_size_md }}}};line-height:{{{{ token_line_height_lg }}}};letter-spacing:{{{{ token_letter_spacing_md }}}};color:{{{{ token_text_primary }}}};text-align:{{{{ align }}}};direction:{{{{ dir }}}};unicode-bidi:plaintext;">{{{{ {heading_var} | strip }}}}</p>
                <p style="margin:4px 0 0 0;font-family:{{{{ token_font_stack }}}};font-weight:400;font-size:{{{{ token_font_size_md }}}};line-height:{{{{ token_line_height_lg }}}};letter-spacing:{{{{ token_letter_spacing_md }}}};color:{{{{ token_text_body }}}};text-align:{{{{ align }}}};direction:{{{{ dir }}}};unicode-bidi:plaintext;">{{{{ {copy_var} | strip }}}}</p>
              </td>
            </tr>'''

    return f'''{{%- if usp_title != blank -%}}
<tr><td style="padding:0;vertical-align:top;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" class="email-usp-module" style="width:600px;max-width:100%;margin-top:{{{{ token_space_600 }}}};background-color:{{{{ token_neutral_c050 }}}};padding:{{{{ token_space_800 }}}};border-radius:{{{{ token_radius_module }}}};box-sizing:border-box;">
  <tbody>
    <tr>
      <td align="center" style="padding:0 0 {{{{ token_space_600 }}}} 0;">
        <p style="margin:0;font-family:{{{{ token_font_stack }}}};font-weight:700;font-size:24px;line-height:32px;letter-spacing:{{{{ token_letter_spacing_md }}}};color:{{{{ token_accent }}}};text-align:center;direction:{{{{ dir }}}};unicode-bidi:plaintext;">{{{{ usp_title | strip }}}}</p>
      </td>
    </tr>
    <tr>
      <td style="padding:0;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;border-collapse:collapse;">
          <tbody>
{_usp_row(icon1, "usp_1_heading", "usp_1_copy")}
{_usp_row(icon2, "usp_2_heading", "usp_2_copy")}
{_usp_row(icon3, "usp_3_heading", "usp_3_copy")}
          </tbody>
        </table>
      </td>
    </tr>
  </tbody>
</table>
</td></tr>
{{%- endif -%}}'''


def build_usp_feature_module(translations: dict[str, dict[str, str]], structure: dict[str, str]) -> str:
    """USP feature module: header + 3 two-column rows (text left, image right). Same content as USP but with larger illustrative images."""
    if "usp_feature_title" not in translations:
        return ""
    img1 = _normalise_url(structure.get("usp_feature_1_image_url") or "")
    img2 = _normalise_url(structure.get("usp_feature_2_image_url") or "")
    img3 = _normalise_url(structure.get("usp_feature_3_image_url") or "")
    placeholder = "https://placehold.co/280x200/fcf7f5/615a56?text=Feature"
    img1 = img1 or placeholder
    img2 = img2 or placeholder
    img3 = img3 or placeholder

    def _feature_row(img_url: str, heading_var: str, copy_var: str) -> str:
        return f'''          <tr class="email-usp-feature-row">
            <td width="50%" valign="middle" style="padding:0 20px 32px 0;vertical-align:middle;">
              <p style="margin:0;font-family:{{{{ token_font_stack }}}};font-weight:700;font-size:{{{{ token_font_size_md }}}};line-height:{{{{ token_line_height_lg }}}};letter-spacing:{{{{ token_letter_spacing_md }}}};color:{{{{ token_text_primary }}}};text-align:{{{{ align }}}};direction:{{{{ dir }}}};unicode-bidi:plaintext;">{{{{ {heading_var} | strip }}}}</p>
              <p style="margin:8px 0 0 0;font-family:{{{{ token_font_stack }}}};font-weight:400;font-size:{{{{ token_font_size_md }}}};line-height:{{{{ token_line_height_lg }}}};letter-spacing:{{{{ token_letter_spacing_md }}}};color:{{{{ token_text_body }}}};text-align:{{{{ align }}}};direction:{{{{ dir }}}};unicode-bidi:plaintext;">{{{{ {copy_var} | strip }}}}</p>
            </td>
            <td width="50%" valign="middle" style="padding:0 0 32px 20px;vertical-align:middle;">
              <img src="{_html_escape(img_url)}" alt="" width="280" height="200" style="display:block;max-width:100%;height:auto;border-radius:{{{{ token_radius_module }}}};" />
            </td>
          </tr>'''

    return f'''{{%- if usp_feature_title != blank -%}}
<tr><td style="padding:0;vertical-align:top;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" class="email-usp-feature-module" style="width:600px;max-width:100%;margin-top:{{{{ token_space_600 }}}};background-color:{{{{ token_neutral_c050 }}}};padding:{{{{ token_space_800 }}}};border-radius:{{{{ token_radius_module }}}};box-sizing:border-box;">
  <tbody>
    <tr>
      <td align="center" colspan="2" style="padding:0 0 {{{{ token_space_600 }}}} 0;">
        <p style="margin:0;font-family:{{{{ token_font_stack }}}};font-weight:700;font-size:24px;line-height:32px;letter-spacing:{{{{ token_letter_spacing_md }}}};color:{{{{ token_accent }}}};text-align:center;direction:{{{{ dir }}}};unicode-bidi:plaintext;">{{{{ usp_feature_title | strip }}}}</p>
      </td>
    </tr>
{_feature_row(img1, "usp_feature_1_heading", "usp_feature_1_copy")}
{_feature_row(img2, "usp_feature_2_heading", "usp_feature_2_copy")}
{_feature_row(img3, "usp_feature_3_heading", "usp_feature_3_copy")}
  </tbody>
</table>
</td></tr>
{{%- endif -%}}'''


def build_usp_ui_module(translations: dict[str, dict[str, str]], structure: dict[str, str]) -> str:
    """USP alternating module: header + 3 rows with alternating layout. Row 1: text left, image right. Row 2: image left, text right. Row 3: text left, image right.
    Images are displayed as-is (no outer container; design is in the image)."""
    if "usp_ui_title" not in translations:
        return ""
    img1 = _normalise_url(structure.get("usp_ui_1_image_url") or "")
    img2 = _normalise_url(structure.get("usp_ui_2_image_url") or "")
    img3 = _normalise_url(structure.get("usp_ui_3_image_url") or "")
    placeholder = "https://placehold.co/280x200/fcf7f5/615a56?text=Image"
    img1 = img1 or placeholder
    img2 = img2 or placeholder
    img3 = img3 or placeholder

    def _ui_row(img_url: str, heading_var: str, copy_var: str, image_first: bool) -> str:
        img_cell = f'<td width="50%" valign="middle" style="padding:0 0 32px 20px;vertical-align:middle;"><img src="{_html_escape(img_url)}" alt="" width="280" height="200" style="display:block;max-width:100%;height:auto;" /></td>'
        text_cell = f'''<td width="50%" valign="middle" style="padding:0 20px 32px 0;vertical-align:middle;">
              <p style="margin:0;font-family:{{{{ token_font_stack }}}};font-weight:700;font-size:{{{{ token_font_size_md }}}};line-height:{{{{ token_line_height_lg }}}};letter-spacing:{{{{ token_letter_spacing_md }}}};color:{{{{ token_text_primary }}}};text-align:{{{{ align }}}};direction:{{{{ dir }}}};unicode-bidi:plaintext;">{{{{ {heading_var} | strip }}}}</p>
              <p style="margin:8px 0 0 0;font-family:{{{{ token_font_stack }}}};font-weight:400;font-size:{{{{ token_font_size_md }}}};line-height:{{{{ token_line_height_lg }}}};letter-spacing:{{{{ token_letter_spacing_md }}}};color:{{{{ token_text_body }}}};text-align:{{{{ align }}}};direction:{{{{ dir }}}};unicode-bidi:plaintext;">{{{{ {copy_var} | strip }}}}</p>
            </td>'''
        if image_first:
            return f'''          <tr class="email-usp-ui-row">
            <td width="50%" valign="middle" style="padding:0 20px 32px 0;vertical-align:middle;">
              <img src="{_html_escape(img_url)}" alt="" width="280" height="200" style="display:block;max-width:100%;height:auto;" />
            </td>
            {text_cell}
          </tr>'''
        return f'''          <tr class="email-usp-ui-row">
            {text_cell}
            <td width="50%" valign="middle" style="padding:0 0 32px 20px;vertical-align:middle;">
              <img src="{_html_escape(img_url)}" alt="" width="280" height="200" style="display:block;max-width:100%;height:auto;" />
            </td>
          </tr>'''

    return f'''{{%- if usp_ui_title != blank -%}}
<tr><td style="padding:0;vertical-align:top;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" class="email-alternating-text-image-module" style="width:600px;max-width:100%;margin-top:{{{{ token_space_600 }}}};box-sizing:border-box;">
  <tbody>
    <tr>
      <td align="center" colspan="2" style="padding:0 0 {{{{ token_space_600 }}}} 0;">
        <p style="margin:0;font-family:{{{{ token_font_stack }}}};font-weight:700;font-size:24px;line-height:32px;letter-spacing:{{{{ token_letter_spacing_md }}}};color:{{{{ token_accent }}}};text-align:center;direction:{{{{ dir }}}};unicode-bidi:plaintext;">{{{{ usp_ui_title | strip }}}}</p>
      </td>
    </tr>
{_ui_row(img1, "usp_ui_1_heading", "usp_ui_1_copy", False)}
{_ui_row(img2, "usp_ui_2_heading", "usp_ui_2_copy", True)}
{_ui_row(img3, "usp_ui_3_heading", "usp_ui_3_copy", False)}
  </tbody>
</table>
</td></tr>
{{%- endif -%}}'''


def build_config_block(
    show_header_logo: str = "TRUE",
    show_footer: str = "TRUE",
    show_terms: str = "TRUE",
    app_download_colour_preset: str = "LIGHT",
) -> str:
    def norm(val: str) -> str:
        val = (val or "TRUE").upper()
        return "TRUE" if val not in ("TRUE", "FALSE") else val

    def norm_preset(val: str) -> str:
        val = (val or "LIGHT").upper().strip()
        return "DARK" if val == "DARK" else "LIGHT"

    return f'''{{%- assign show_header_logo = "{norm(show_header_logo)}" -%}}
{{%- assign show_footer = "{norm(show_footer)}" -%}}
{{%- assign show_terms = "{norm(show_terms)}" -%}}
{{%- comment -%}} App download colour toggle: write LIGHT or DARK (or override via app_download_colour_preset merge field) {{%- endcomment -%}}
{{%- assign app_download_colour_toggle = "{norm_preset(app_download_colour_preset)}" -%}}
{{%- assign app_download_colour_preset = app_download_colour_preset | default: app_download_colour_toggle | upcase | strip -%}}'''


DEFAULT_LINKS = {
    "app_download_page": "https://app.vio.com/v0HW",
    "homepage": "https://www.vio.com",
    "terms_of_use": "https://www.vio.com/terms-of-use",
    "privacy_policy": "https://www.vio.com/privacy-policy",
    "booking_page": "https://app.vio.com",
    "notification_preferences": "{{snippets.vio_notification_preferences}}",
    "notification_preferences_unsubscribe": "{{snippets.vio_notification_preferences_unsubscribe}}",
    "instagram": "https://www.instagram.com/vio.com.travel",
    "facebook": "https://www.facebook.com/viodotcom",
    "linkedin": "https://www.linkedin.com/company/viodotcom/",
}


def load_standard_links(config_path: Path | None = None) -> dict[str, str]:
    """Load links from standard_links.json. Returns DEFAULT_LINKS if file missing or invalid."""
    import json
    path = config_path or Path(__file__).parent / "standard_links.json"
    if not path.exists():
        return dict(DEFAULT_LINKS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data.get("links"), dict):
            return {k: v.get("url", v) if isinstance(v, dict) else v for k, v in data["links"].items()}
        return dict(DEFAULT_LINKS) | {k: v for k, v in data.items() if isinstance(v, str)}
    except (json.JSONDecodeError, TypeError):
        return dict(DEFAULT_LINKS)


def build_terms_defaults_block() -> str:
    """Build Liquid block with conditional defaults for terms_title, terms_label, privacy_label, terms_desc_text.
    Only applies when variable is blank (i.e. user did not provide custom text in CSV)."""
    liquid_path = Path(__file__).parent / "full_email_template.liquid"
    if not liquid_path.exists():
        # Minimal fallback when full_email_template not yet generated
        return """{%- if terms_title == blank -%}{%- capture terms_title -%}Terms and Privacy Policy{%- endcapture -%}{%- endif -%}
{%- if terms_label == blank -%}{%- capture terms_label -%}Terms{%- endcapture -%}{%- endif -%}
{%- if privacy_label == blank -%}{%- capture privacy_label -%}Privacy Policy{%- endcapture -%}{%- endif -%}
{%- if terms_desc_text == blank -%}{%- capture terms_desc_text -%}This booking is covered by our {terms} and {privacyPolicy}.{%- endcapture -%}{%- endif -%}"""
    text = liquid_path.read_text(encoding="utf-8")
    # Extract the 4 captures (excl. terms_link, privacy_link which we add separately)
    blocks = re.findall(
        r'(\{%- capture (terms_title|terms_label|privacy_label|terms_desc_text) -%\}.+?\{%- endcapture -%\})',
        text,
        re.DOTALL,
    )
    if len(blocks) != 4:
        return "{%- comment -%}terms defaults fallback{%- endcomment -%}"
    out = []
    for block, name in blocks:
        var = name.strip()
        out.append(f'{{%- if {var} == blank -%}}{block}{{%- endif -%}}')
    return "\n".join(out)


def build_links_block(links: dict[str, str] | None = None) -> str:
    """Build Liquid assigns for standard links. Uses DEFAULT_LINKS for any missing keys."""
    import json
    merged = dict(DEFAULT_LINKS)
    if links:
        merged.update(links)
    elif (path := Path(__file__).parent / "standard_links.json").exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data.get("links"), dict):
                merged.update({k: v.get("url", v) if isinstance(v, dict) else v for k, v in data["links"].items()})
            else:
                merged.update({k: v for k, v in data.items() if isinstance(v, str)})
        except (json.JSONDecodeError, TypeError):
            pass
    lines = []
    for key, url in merged.items():
        if not isinstance(url, str):
            continue
        # Liquid: escape double quotes in URL
        escaped = url.replace('\\', '\\\\').replace('"', '\\"')
        var_name = key.replace(".", "_").replace("-", "_")
        lines.append(f'{{%- assign link_{var_name} = "{escaped}" -%}}')
    return "\n".join(lines)


# Placeholder content for module preview (sample text + placeholder images)
_PREVIEW_PLACEHOLDERS = {
    "hero_module": {
        "subject_line": "Preview",
        "preheader": "Preview text",
        "headline": "Your headline here",
        "body_1": "Body copy goes here. Replace with your message.",
        "body_2": "Second paragraph of body text.",
        "cta_text": "Call to action",
        "image_url": "https://placehold.co/728x400/fcf7f5/615a56?text=Hero+image",
        "image_deeplink": "#",
        "cta_link": "#",
        "cta_alias": "hero-cta",
    },
    "hero_module_two_column": {
        "subject_line": "Preview",
        "preheader": "Preview",
        "headline": "Your main headline",
        "subheadline": "Subheadline",
        "body_1_h2": "Feature one",
        "body_1_copy": "Description for this feature block.",
        "image_1_URL": "https://placehold.co/260x180/fcf7f5/615a56?text=1",
        "body_2_h2": "Feature two",
        "body_2_copy": "Description for the second block.",
        "image_2_URL": "https://placehold.co/260x180/fcf7f5/615a56?text=2",
        "body_3_h2": "Feature three",
        "body_3_copy": "Description for the third block.",
        "image_3_URL": "https://placehold.co/260x180/fcf7f5/615a56?text=3",
        "body_4_h2": "Feature four",
        "body_4_copy": "Description for the fourth block.",
        "image_4_URL": "https://placehold.co/260x180/fcf7f5/615a56?text=4",
        "cta_text": "Call to action",
        "hero_image_url": "https://placehold.co/728x400/fcf7f5/615a56?text=Hero",
        "image_deeplink": "#",
        "cta_link": "#",
        "cta_alias": "hero-cta",
    },
    "app_download_module": {
        "headline": "<b>Stay in the loop</b> on the app",
        "feature_1": "Find extra savings",
        "feature_2": "Manage your reservations",
        "feature_3": "Track prices",
        "colour": "#fcf7f5",
    },
    "disclaimer_module": {
        "terms_title": "Terms and Privacy Policy",
        "terms_desc": "This booking is covered by our {terms} and {privacyPolicy}.",
        "terms_label": "Terms",
        "privacy_label": "Privacy Policy",
    },
    "icon_left_text_right_module": {
        "title": "How Vio helps you book like an insider",
        "usp_1_heading": "Compare prices across 100+ sites",
        "usp_1_copy": "See the full picture upfront. No guessing, no bouncing between tabs.",
        "usp_1_icon_url": "https://placehold.co/80/f2e5ff/7130c9?text=1",
        "usp_2_heading": "Know exactly when to book",
        "usp_2_copy": "Price insights show you the right moment to secure your deal.",
        "usp_2_icon_url": "https://placehold.co/80/f2e5ff/7130c9?text=2",
        "usp_3_heading": "Stay ahead of price changes",
        "usp_3_copy": "We track prices so you don't have to keep checking.",
        "usp_3_icon_url": "https://placehold.co/80/f2e5ff/7130c9?text=3",
    },
    "text_left_image_right_module": {
        "title": "How Vio helps you book like an insider",
        "usp_feature_1_heading": "Compare prices across 100+ sites",
        "usp_feature_1_copy": "See the full picture upfront. No guessing, no bouncing between tabs.",
        "usp_feature_1_image_url": "https://placehold.co/280x200/fcf7f5/615a56?text=Compare",
        "usp_feature_2_heading": "Know exactly when to book",
        "usp_feature_2_copy": "Price insights show you the right moment to secure your deal.",
        "usp_feature_2_image_url": "https://placehold.co/280x200/fcf7f5/615a56?text=When",
        "usp_feature_3_heading": "Stay ahead of price changes",
        "usp_feature_3_copy": "We track prices so you don't have to keep checking.",
        "usp_feature_3_image_url": "https://placehold.co/280x200/fcf7f5/615a56?text=Track",
    },
    "alternating_text_image_module": {
        "title": "How Vio helps you book like an insider",
        "usp_ui_1_heading": "Compare prices across 100+ sites",
        "usp_ui_1_copy": "See the full picture upfront. No guessing, no bouncing between tabs.",
        "usp_ui_1_image_url": "https://placehold.co/280x200/e1ceff/7130c9?text=Compare",
        "usp_ui_2_heading": "Know exactly when to book",
        "usp_ui_2_copy": "Price insights show you the right moment to secure your deal.",
        "usp_ui_2_image_url": "https://placehold.co/280x200/e1ceff/7130c9?text=When",
        "usp_ui_3_heading": "Stay ahead of price changes",
        "usp_ui_3_copy": "We track prices so you don't have to keep checking.",
        "usp_ui_3_image_url": "https://placehold.co/280x200/e1ceff/7130c9?text=Track",
    },
}


def get_module_preview_html(
    modules: list[str],
    *,
    app_download_colour_preset: str = "LIGHT",
    design_tokens_brand: str = "vio",
) -> str:
    """
    Generate HTML preview of selected modules with placeholder content.
    Used in Streamlit to show users what their template will look like.
    """
    if not modules:
        return "<p style='padding:20px;color:#615a56;'>Select modules to see a preview.</p>"
    # Build CSV with placeholder content for selected modules
    rows: list[tuple[str, str, int, str]] = []  # (Key, Module, module_index, en)
    module_indices: dict[str, int] = {}
    for mod in modules:
        if mod not in MODULE_TEMPLATE_ROWS or mod not in _PREVIEW_PLACEHOLDERS:
            continue
        idx = module_indices.get(mod, len(module_indices) + 1)
        module_indices[mod] = idx
        placeholders = _PREVIEW_PLACEHOLDERS[mod]
        for csv_key, _ in MODULE_TEMPLATE_ROWS[mod]:
            val = placeholders.get(csv_key, placeholders.get(csv_key.replace("_", ""), ""))
            rows.append((csv_key, mod, str(idx), val))
    if not rows:
        return "<p style='padding:20px;color:#615a56;'>Select modules to see a preview.</p>"
    headers = ["Key", "Module", "module_index", "en"]
    out = [headers] + [[r[0], r[1], r[2], r[3]] for r in rows]
    writer = csv.StringIO()
    csv.writer(writer).writerows(out)
    csv_content = writer.getvalue()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        tmp_path = Path(f.name)
    try:
        show_terms = "disclaimer_module" in modules
        result = generate_template(
            tmp_path,
            show_header_logo="FALSE",
            show_footer="FALSE",
            show_terms="TRUE" if show_terms else "FALSE",
            app_download_colour_preset=app_download_colour_preset,
            design_tokens_brand=design_tokens_brand,
        )
        translations, structure = load_translations(tmp_path)
        html = liquid_to_preview_html(
            result,
            translations,
            structure,
            show_header_logo=False,
            show_footer=False,
            show_terms=show_terms,
        )
        return html
    finally:
        tmp_path.unlink(missing_ok=True)


def generate_standard_input_template(
    modules: list[str],
    *,
    include_locales: list[str] | None = None,
) -> tuple[str, dict[str, str]]:
    """
    Generate a blank CSV template and links config for the selected modules.
    modules: e.g. ["hero_module_two_column", "app_download_module"] or ["hero_module"]
    include_locales: locale columns to add (default: ["en"] only for minimal template)
    Returns (csv_content, links_dict).
    """
    import json
    locales = include_locales or ["en"]
    rows: list[tuple[str, str, int, list[str]]] = []  # (Key, Module, module_index, [en, ...])
    module_indices: dict[str, int] = {}
    for mod in modules:
        if mod not in MODULE_TEMPLATE_ROWS:
            continue
        idx = module_indices.get(mod, len(module_indices) + 1)
        module_indices[mod] = idx
        for csv_key, placeholder in MODULE_TEMPLATE_ROWS[mod]:
            vals = [placeholder if i == 0 else "" for i in range(len(locales))]
            rows.append((csv_key, mod, idx, vals))
    headers = ["Key", "Module", "module_index"] + locales
    out = [headers]
    for key, mod, idx, vals in rows:
        out.append([key, mod, str(idx)] + vals)
    writer = csv.StringIO()
    csv_writer = csv.writer(writer)
    csv_writer.writerows(out)
    links = load_standard_links()
    return writer.getvalue(), links


BASE_TEMPLATE = r'''{%- comment -%}
FULL EMAIL HTML (multi-locale from translations CSV)
- Requires CSV with Key + locale columns. Run: python3 csv_translations_to_email.py email_translations.csv
{%- endcomment -%}

{%- assign lang = customer.language | default: "en" | downcase | replace: "_", "-" -%}
{%- assign lang2 = lang | slice: 0, 2 -%}
{%- assign locale_key = lang2 -%}
{%- assign country = customer.country_code | default: customer.country | default: customer.cio_iso_country | default: "" | upcase | slice: 0, 2 -%}
{%- if lang2 == "iw" -%}{%- assign locale_key = "he" -%}{%- endif -%}
{%- if lang contains "zh-hk" or lang contains "zh-hant-hk" -%}{%- assign locale_key = "zh-hk" -%}
{%- elsif lang contains "zh-tw" or lang contains "zh-hant" -%}{%- assign locale_key = "zh-tw" -%}
{%- elsif lang contains "zh-cn" or lang contains "zh-sg" or lang contains "zh-hans" -%}{%- assign locale_key = "zh-cn" -%}
{%- elsif lang contains "fr-ca" -%}{%- assign locale_key = "fr-ca" -%}
{%- elsif lang contains "pt-br" -%}{%- assign locale_key = "pt-br" -%}
{%- elsif lang contains "pt-pt" -%}{%- assign locale_key = "pt" -%}
{%- elsif lang contains "en-gb" -%}{%- assign locale_key = "en-gb" -%}
{%- elsif lang2 == "es" and lang contains "-" and lang != "es-es" -%}{%- assign locale_key = "es-419" -%}
{%- elsif lang2 == "tl" or lang contains "fil" -%}{%- assign locale_key = "fil" -%}
{%- elsif lang2 == "nb" or lang2 == "nn" -%}{%- assign locale_key = "no" -%}
{%- endif -%}
{%- assign is_portuguese = false -%}
{%- if lang2 == "pt" or lang contains "portuguese" -%}{%- assign is_portuguese = true -%}{%- endif -%}
{%- if is_portuguese -%}
  {%- if country == "BR" -%}{%- assign locale_key = "pt-br" -%}
  {%- elsif country == "PT" -%}{%- assign locale_key = "pt" -%}
  {%- elsif lang contains "pt-pt" -%}{%- assign locale_key = "pt" -%}
  {%- elsif lang contains "pt-br" -%}{%- assign locale_key = "pt-br" -%}
  {%- else -%}{%- assign locale_key = "pt-br" -%}
  {%- endif -%}
{%- elsif lang2 == "es" and locale_key == "es" -%}
  {%- assign latam_countries = "MX,AR,CO,CL,PE,VE,EC,GT,HN,SV,NI,PA,PR,DO,CR,BO,PY,UY,CU" | split: "," -%}
  {%- assign is_latam = false -%}
  {%- for cc in latam_countries -%}{%- if country == cc -%}{%- assign is_latam = true -%}{%- break -%}{%- endif -%}{%- endfor -%}
  {%- if is_latam -%}{%- assign locale_key = "es-419" -%}{%- endif -%}
{%- elsif lang2 == "en" and locale_key == "en" and country == "GB" -%}{%- assign locale_key = "en-gb" -%}
{%- elsif lang2 == "fr" and locale_key == "fr" and country == "CA" -%}{%- assign locale_key = "fr-ca" -%}
{%- endif -%}

{%- assign rtl_locales = "ar,he,fa,ur" | split: "," -%}
{%- assign dir = "ltr" -%}
{%- if rtl_locales contains locale_key -%}{%- assign dir = "rtl" -%}{%- endif -%}
{%- assign headline_align = "center" -%}
{%- if locale_key == "ar" or locale_key == "he" -%}{%- assign headline_align = "right" -%}{%- endif -%}
{%- assign align = "left" -%}
{%- if locale_key == "ar" or locale_key == "he" -%}{%- assign align = "right" -%}{%- endif -%}
''' + PLACEHOLDER_LINKS + '''
{%- assign app_deeplink_url = app_deeplink_url | default: link_app_download_page -%}
''' + PLACEHOLDER_DESIGN_TOKENS + '''

''' + PLACEHOLDER_CONFIG + '''
''' + PLACEHOLDER_APP_DOWNLOAD_SETTINGS + '''

''' + PLACEHOLDER_CONTENT_CAPTURES + '''

{%- capture footer_app_line -%}
  {%- case locale_key -%}
    {%- when "ar" -%}احجز كأهل البلد. حمّل التطبيق.
    {%- when "zh-cn" -%}订房有一套。 下载应用。
    {%- when "zh-tw" -%}懂玩的人，都這樣訂房 下載應用程式
    {%- when "zh-hk" -%}訂得安心。 下載應用程式。
    {%- when "hr" -%}Rezervirajte pametnije. Preuzmite aplikaciju.
    {%- when "cs" -%}Rezervujte levou zadní. Stáhněte si aplikaci.
    {%- when "da" -%}Book med overblik. Download appen.
    {%- when "nl" -%}Boeken zonder poespas. Download de app.
    {%- when "en-gb" -%}Book like an insider. Download the app.
    {%- when "en" -%}Book like an insider. Download the app.
    {%- when "fil" -%}Mag-book nang may kumpyansa. I-download ang app.
    {%- when "fi" -%}Varaa fiksusti. Lataa sovellus.
    {%- when "fr" -%}Réserver sans se tromper. Télécharger l'application.
    {%- when "fr-ca" -%}Réservez en toute confiance. Télécharger l'application.
    {%- when "de" -%}Buchen mit klarem Blick. App herunterladen.
    {%- when "el" -%}Κάνε τώρα τις πιο έξυπνες κρατήσεις. Κατεβάστε την εφαρμογή.
    {%- when "he" -%}להזמין חכם זה פשוט. הורידו את האפליקציה.
    {%- when "hu" -%}Foglaljon magabiztosan. Töltse le az alkalmazást.
    {%- when "id" -%}Pesan tanpa cemas. Unduh aplikasi.
    {%- when "it" -%}Prenotare senza pensieri. Scarica l'app.
    {%- when "ja" -%}納得して予約する。アプリをダウンロード。
    {%- when "ko" -%}예약에 확신을 더하다. 앱을 다운로드하세요.
    {%- when "ms" -%}Kejelasan diutamakan. Tempah tanpa ragu. Muat turun aplikasi.
    {%- when "no" -%}Book som en insider. Last ned appen.
    {%- when "pl" -%}Rezerwuj jak zawodowiec. Pobierz aplikację.
    {%- when "pt" -%}Reserve com confiança. Descarregue a app.
    {%- when "pt-br" -%}Reserve sem erro. Baixe o app.
    {%- when "ro" -%}Rezervă cu toată încrederea. Descarcă aplicația.
    {%- when "ru" -%}Бронируйте с умом. Скачайте приложение.
    {%- when "es" -%}Reservar sin equivocarse. Descarga la app.
    {%- when "es-419" -%}Reservar sin equivocarse. Descarga la aplicación.
    {%- when "sv" -%}Boka som en insider. Ladda ner appen.
    {%- when "th" -%}จองคุ้มว่า ราคาแบบคนวงใน ดาวน์โหลดแอป
    {%- when "tr" -%}Daha akıllıca rezervasyon yap. Uygulamayı indirin.
    {%- when "uk" -%}Бронюй як місцевий. Завантажте застосунок.
    {%- when "vi" -%}Đặt chỗ thông minh hơn. Tải ứng dụng.
    {%- else -%}Book like an insider. Download the app.
  {%- endcase -%}
{%- endcapture -%}
{%- capture google_play_badge_url -%}
  {%- case locale_key -%}
    {%- when "ar" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236962918_GetItOnGooglePlay_Badge_Web_color_Arabic-Saudi-Arabia_01KHJZ6CN2JBA5CF1HGYEBR0ZB.png
    {%- when "zh-cn" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236931782_GetItOnGooglePlay_Badge_Web_color_Chinese-China_01KHJZ5E80BKM74N929XGVH73W.png
    {%- when "zh-tw" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236963430_GetItOnGooglePlay_Badge_Web_color_Chinese-Taiwan_01KHJZ6D52KGDWFZ3EJ7J4TDJN.png
    {%- when "zh-hk" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236963430_GetItOnGooglePlay_Badge_Web_color_Chinese-Taiwan_01KHJZ6D52KGDWFZ3EJ7J4TDJN.png
    {%- when "hr" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236932327_GetItOnGooglePlay_Badge_Web_color_Croatian_01KHJZ5ES2WZRCQFG9ZT55XRMA.png
    {%- when "cs" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236932827_GetItOnGooglePlay_Badge_Web_color_Czech_01KHJZ5F8P40FN1391523NZBTQ.png
    {%- when "da" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236933422_GetItOnGooglePlay_Badge_Web_color_Danish_01KHJZ5FV9HWT6ER9P2ZEH9NZY.png
    {%- when "nl" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236964032_GetItOnGooglePlay_Badge_Web_color_Dutch_01KHJZ6DQV8BRNCRR44WVV9JYS.png
    {%- when "en-gb" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236964477_GetItOnGooglePlay_Badge_Web_color_English_01KHJZ6E5TKNXTSE65NBZACEG9.png
    {%- when "fil" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236934541_GetItOnGooglePlay_Badge_Web_color_Filipino_01KHJZ5GY847JWJVR418R4WK1T.png
    {%- when "fi" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236935210_GetItOnGooglePlay_Badge_Web_color_Finnish_01KHJZ5HK62QMPTTZNBTC8EHCH.png
    {%- when "fr" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236936588_GetItOnGooglePlay_Badge_Web_color_French_01KHJZ5JYMQHPQA5VVP2ZCN0FA.png
    {%- when "fr-ca" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236936009_GetItOnGooglePlay_Badge_Web_color_French-CA_01KHJZ5JC4KYCZ34HD5KJFVZ3H.png
    {%- when "de" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236938791_GetItOnGooglePlay_Badge_Web_color_German_01KHJZ5N3480FF9T2GTERH7534.png
    {%- when "el" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236939293_GetItOnGooglePlay_Badge_Web_color_Greek_01KHJZ5NJR3KV5ZC3AF5SARHXW.png
    {%- when "he" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236940388_GetItOnGooglePlay_Badge_Web_color_Hebrew_01KHJZ5PMZF104ACAMQJ5Z8396.png
    {%- when "hu" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236964964_GetItOnGooglePlay_Badge_Web_color_Hungarian_01KHJZ6EMYMAG43FESGKQASR44.png
    {%- when "id" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236942023_GetItOnGooglePlay_Badge_Web_color_Indonesian_01KHJZ5R8PD23W9WMQ8ABBF8QC.png
    {%- when "it" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236962404_GetItOnGooglePlay_Badge_Web_color_Italian_01KHJZ6C4YX4G22A9BRHN69B2F.png
    {%- when "ja" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236965469_GetItOnGooglePlay_Badge_Web_color_Japanese_01KHJZ6F4VNH8AR4QXVZSS90BW.png
    {%- when "ko" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236944212_GetItOnGooglePlay_Badge_Web_color_Korean_01KHJZ5TCF1X80Z85634GAFP61.png
    {%- when "ms" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236965960_GetItOnGooglePlay_Badge_Web_color_Malaysian_01KHJZ6FM6RA8F0JNY949JBBXY.png
    {%- when "no" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236949497_GetItOnGooglePlay_Badge_Web_color_Norwegian_01KHJZ5ZHP2XN0RGJEFMFEFNTK.png
    {%- when "pl" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236950533_GetItOnGooglePlay_Badge_Web_color_Polish_01KHJZ60J36RPY7WBGC5NNW11P.png
    {%- when "pt-br" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236951142_GetItOnGooglePlay_Badge_Web_color_Portuguese-Brazil_01KHJZ6153VXSST3S40SBWX090.png
    {%- when "pt" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236951743_GetItOnGooglePlay_Badge_Web_color_Portuguese-Portugal_01KHJZ61QVYB2YKSSMX5R287F6.png
    {%- when "ro" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236952981_GetItOnGooglePlay_Badge_Web_color_Romanian_01KHJZ62YK9KCWXZEFH95TV1R2.png
    {%- when "ru" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236953514_GetItOnGooglePlay_Badge_Web_color_Russian_01KHJZ63F49G1EJ7WS0W7EX5HM.png
    {%- when "es" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236956142_GetItOnGooglePlay_Badge_Web_color_Spanish_01KHJZ6619WRKFWSFZXYRTKB0N.png
    {%- when "es-419" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236955633_GetItOnGooglePlay_Badge_Web_color_Spanish-LATAM_01KHJZ65HBRWHVJCBWQGJPV593.png
    {%- when "sv" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236957489_GetItOnGooglePlay_Badge_Web_color_Swedish_01KHJZ67BFDYGZGRH618PGKNJT.png
    {%- when "th" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236959210_GetItOnGooglePlay_Badge_Web_color_Thai_01KHJZ6915Q1KWZ8CDE54VYKKM.png
    {%- when "tr" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236959859_GetItOnGooglePlay_Badge_Web_color_Turkish_01KHJZ69NEWQKTAMK75AZSTBRQ.png
    {%- when "uk" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236960351_GetItOnGooglePlay_Badge_Web_color_Ukranian_01KHJZ6A4VF3Y47BT01A234Z4C.png
    {%- when "vi" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236961907_GetItOnGooglePlay_Badge_Web_color_Vietnamese_01KHJZ6BNENBQ0X5YT386JYYSX.png
    {%- else -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771236964477_GetItOnGooglePlay_Badge_Web_color_English_01KHJZ6E5TKNXTSE65NBZACEG9.png
  {%- endcase -%}
{%- endcapture -%}
{%- assign google_play_badge_url = google_play_badge_url | strip -%}
{%- capture app_store_badge_url -%}
  {%- case locale_key -%}
    {%- when "ar" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861173599_ar_01KJ5JFSJE01ZPHHNDPS8HB6DF.png
    {%- when "zh-cn" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861197369_zh-CN_01KJ5JGGKHGKGQ72R8Z3Q06S41.png
    {%- when "zh-tw" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861197949_zh-TW_01KJ5JGH5PCMBQMYPB5P67TAWE.png
    {%- when "zh-hk" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861198507_zh_01KJ5JGHQ68EB3R6W6DCX8CEN0.png
    {%- when "hr" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861184696_hr_01KJ5JG47GKS3NZV378J31D0HZ.png
    {%- when "cs" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861175533_cs_01KJ5JFV95YKZVN00V47EVNJDH.png
    {%- when "da" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861176073_da_01KJ5JFVT5Q47NXQEAXNDKB61J.png
    {%- when "en" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861742970_en_01KJ5K15DG7W6K6VRFV8G3ZN6D.png
    {%- when "en-gb" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861741874_en-GB_01KJ5K14BHNDBZ9FARS47Y8KBA.png
    {%- when "nl" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861188893_nl_01KJ5JG8APQZX5JHFCEXNWSSBM.png
    {%- when "fil" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861180586_fil_01KJ5JG0742DQ6XW1SG4DHAZFB.png
    {%- when "fi" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861180045_fi_01KJ5JFZP7DEECV2FBN1Z8MY84.png
    {%- when "fr" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861182728_fr_01KJ5JG2A17F4C9CV4S9BBDY9M.png
    {%- when "fr-ca" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861181505_fr-CA_01KJ5JG17KPVR3GTZN4GNX787W.png
    {%- when "de" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861176692_de_01KJ5JFWDD70S544M1MM3TTVHJ.png
    {%- when "el" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861177220_el_01KJ5JFWXWFRTPE6Y0KSQPW0CZ.png
    {%- when "he" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861183342_he_01KJ5JG2XDMXP7A0T255541GP1.png
    {%- when "hu" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861185226_hu_01KJ5JG4R4Z9VCY2ZWW80PTTSG.png
    {%- when "id" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861185770_id_01KJ5JG59573P3PYV8653PGM5A.png
    {%- when "it" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861684618_it_01KJ5JZCE7MR6PN0Y523KY3FAF.png
    {%- when "ja" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861633879_ja_01KJ5JXTWTSPV5TKTB7QGXFYWN.png
    {%- when "ko" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861193949_ko_01KJ5JGD8NY8TRT8H5A8GNQPHD.png
    {%- when "ms" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861187851_ms_01KJ5JG7A5ZZ7PPWYPYXTHHDFN.png
    {%- when "no" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861189491_no_01KJ5JG8XDBAQNJ6FAMEVRDR8M.png
    {%- when "pl" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861190048_pl_01KJ5JG9EVMH4GB6EC5RE7GGA5.png
    {%- when "pt-br" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861190611_pt-BR_01KJ5JGA0DM860HS0K3HA29APX.png
    {%- when "pt" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861191742_pt_01KJ5JGB3Q1Y1X03FMWV77CDPE.png
    {%- when "ro" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861192285_ro_01KJ5JGBMPFTAWXA32Z8HZQSXJ.png
    {%- when "ru" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861192867_ru_01KJ5JGC6XKWKFQ0CWA5AJJDTF.png
    {%- when "es" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861178931_es_01KJ5JFYKBRTEQKCRKZ867FSZZ.png
    {%- when "es-419" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861177816_es-419_01KJ5JFXGHCETGJ6NMJ1E24XS6.png
    {%- when "sv" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861195074_sv_01KJ5JGEBVABEJG2P1KEBEMG3Z.png
    {%- when "th" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861195630_th_01KJ5JGEX74T830TFMVKHQVHVR.png
    {%- when "tr" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861196165_tr_01KJ5JGFDY7AB5EFAJQZJ8E2G9.png
    {%- when "vi" -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861196752_vi_01KJ5JGG0ATCDFKBEMQKRTGZW1.png
    {%- else -%}https://userimg-assets.customeriomail.com/images/client-env-124967/1771861742970_en_01KJ5K15DG7W6K6VRFV8G3ZN6D.png
  {%- endcase -%}
{%- endcapture -%}
{%- assign app_store_badge_url = app_store_badge_url | strip -%}
{%- capture footer_address -%}FindHotel B.V. Nieuwe Looiersdwarsstraat 17, 1017 TZ, Amsterdam, The Netherlands.{%- endcapture -%}
{%- capture footer_prefs_text -%}
  {%- case locale_key -%}
    {%- when "ar" -%}قم بتحديث <emailPreferences>تفضيلات بريدك الإلكتروني</emailPreferences> لاختيار رسائل البريد الإلكتروني التي تتلقاها أو <unsubscribe>إلغاء الاشتراك</unsubscribe> من كل رسائل البريد الإلكتروني.
    {%- when "zh-cn" -%}更新 <emailPreferences>电子邮件偏好设置</emailPreferences>，选择接收哪些邮件或 <unsubscribe>退订</unsubscribe>所有邮件。
    {%- when "zh-tw" -%}更新 <emailPreferences>電子郵件偏好</emailPreferences>，選擇要收到哪些電子郵件，或是 <unsubscribe>取消訂閱</unsubscribe>所有電子郵件。
    {%- when "zh-hk" -%}更新 <emailPreferences>電郵偏好設定</emailPreferences>以選擇接收哪些電郵或 <unsubscribe>取消訂閱</unsubscribe>所有電郵。
    {%- when "hr" -%}Ažurirajte svoje <emailPreferences>postavke za e-mail</emailPreferences> kako biste odabrali koje e-poruke želite primati ili se u potpunosti <unsubscribe>odjavite</unsubscribe>.
    {%- when "cs" -%}Upravte si <emailPreferences>předvolby e-mailů</emailPreferences> a vyberte sdělení, která chcete dostávat. Můžete si také <unsubscribe>odhlásit odběr</unsubscribe> veškerých e-mailů.
    {%- when "da" -%}Opdater <emailPreferences>indstillinger for e-mail</emailPreferences> for at vælge, hvilke e-mails du får, eller <unsubscribe>afmeld</unsubscribe> alle e-mails.
    {%- when "nl" -%}Werk je <emailPreferences>e-mailvoorkeuren</emailPreferences> bij om te kiezen welke e-mails je wilt ontvangen of om je <unsubscribe>af te melden</unsubscribe> voor alle e-mails.
    {%- when "en-gb" -%}Update your <emailPreferences>email preferences</emailPreferences> to choose which emails you get or <unsubscribe>unsubscribe</unsubscribe> from all emails.
    {%- when "en" -%}Update your <emailPreferences>email preferences</emailPreferences> to choose which emails you get or <unsubscribe>unsubscribe</unsubscribe> from all emails.
    {%- when "fil" -%}I-update ang <emailPreferences>mga preference mo sa email</emailPreferences> para piliin kung anong mga email ang matatanggap mo o <unsubscribe>mag-unsubscribe</unsubscribe> sa lahat ng email.
    {%- when "fi" -%}Päivitä <emailPreferences>sähköpostiasetukset</emailPreferences> ja valitse saamasi sähköpostiviestit tai <unsubscribe>peruuta</unsubscribe> kaikkien sähköpostiviestien tilaus.
    {%- when "fr" -%}Mettez à jour vos <emailPreferences>préférences en matière d'e-mails</emailPreferences> pour choisir ce que vous souhaitez recevoir ou pour vous <unsubscribe>désabonner</unsubscribe> de tous les e-mails.
    {%- when "fr-ca" -%}Mettez à jour vos <emailPreferences>préférences de courriel</emailPreferences> pour choisir les courriels que vous recevez ou vous <unsubscribe>désabonner</unsubscribe> de tous les courriels.
    {%- when "de" -%}Aktualisieren Sie Ihre <emailPreferences>E-Mail-Einstellungen</emailPreferences>, um auszuwählen, welche E-Mails Sie erhalten möchten, oder um sich von allen E-Mails <unsubscribe>abzumelden</unsubscribe>.
    {%- when "el" -%}Ενημερώστε τις <emailPreferences>προτιμήσεις email</emailPreferences> σας για να επιλέξετε ποια email θα λαμβάνετε ή να <unsubscribe>καταργήσετε την εγγραφή σας</unsubscribe> από όλα τα email.
    {%- when "he" -%}יש לעדכן את <emailPreferences>העדפות האימייל</emailPreferences> שלכם כדי לבחור אילו אימיילים לקבל, או <unsubscribe>לבטל את המינוי</unsubscribe> על כל האימיילים.
    {%- when "hu" -%}Frissítse <emailPreferences>e-mail-beállításait</emailPreferences>, hogy kiválaszthassa, mely e-maileket szeretné megkapni, vagy <unsubscribe>leiratkozhat</unsubscribe> az összes e-mailről.
    {%- when "id" -%}Perbarui <emailPreferences>preferensi email</emailPreferences> Anda untuk memilih email mana yang Anda dapatkan atau <unsubscribe>berhenti berlangganan</unsubscribe> dari semua email.
    {%- when "it" -%}Aggiorna le <emailPreferences>preferenze delle email</emailPreferences> per scegliere quali email ricevere o per <unsubscribe>cancellare l'iscrizione</unsubscribe> a tutte le email.
    {%- when "ja" -%}<emailPreferences>メール設定</emailPreferences>を更新して、受信するメールを選択したり、すべてのメールの<unsubscribe>登録を解除</unsubscribe>したりできます。
    {%- when "ko" -%}<emailPreferences>이메일 환경 설정</emailPreferences>을 업데이트하여 받을 이메일을 선택하거나 모든 이메일을 <unsubscribe>구독 해제</unsubscribe>할 수 있어요.
    {%- when "ms" -%}Kemas kini <emailPreferences>keutamaan e-mel</emailPreferences> anda untuk memilih e-mel yang anda terima atau <unsubscribe>nyahlanggan</unsubscribe> semua e-mel.
    {%- when "no" -%}Oppdater <emailPreferences>e-postpreferansene</emailPreferences> dine for å velge hvilke e-poster du får, eller <unsubscribe>avslutt abonnementet</unsubscribe> på alle e-poster.
    {%- when "pl" -%}Aktualizacja <emailPreferences>preferencji dotyczących e-maili</emailPreferences> pozwala wybrać, które wiadomości chcesz otrzymywać, lub <unsubscribe>zrezygnować</unsubscribe> ze wszystkich wiadomości.
    {%- when "pt" -%}Atualize as suas <emailPreferences>preferências de e-mail</emailPreferences> para escolher os e-mails que recebe ou <unsubscribe>cancele a subscrição</unsubscribe> de todos os e-mails.
    {%- when "pt-br" -%}Atualize suas <emailPreferences>preferências de e-mail</emailPreferences> para escolher quais e-mails você deseja receber ou <unsubscribe>cancele a inscrição</unsubscribe> de todos os e-mails.
    {%- when "ro" -%}Actualizează-ți <emailPreferences>preferințele de e-mail</emailPreferences> pentru a alege ce e-mailuri primești sau pentru a te <unsubscribe>dezabona</unsubscribe> de la toate e-mailurile.
    {%- when "ru" -%}Обновите <emailPreferences>настройки электронной почты</emailPreferences>, чтобы выбрать, какие письма получать, или <unsubscribe>отмените подписку</unsubscribe> на все рассылки.
    {%- when "es" -%}Actualiza tus <emailPreferences>preferencias de correo electrónico</emailPreferences> para elegir qué correos electrónicos deseas recibir o para <unsubscribe>cancelar la suscripción</unsubscribe> a todos los correos electrónicos.
    {%- when "es-419" -%}Actualiza tus <emailPreferences>preferencias de correo electrónico</emailPreferences> para elegir qué mensajes quieres recibir o <unsubscribe>cancelar tu suscripción</unsubscribe> de todos los correos.
    {%- when "sv" -%}Uppdatera dina <emailPreferences>e-postinställningar</emailPreferences> för att välja vilka e-postmeddelanden du får eller <unsubscribe>avsluta</unsubscribe> alla prenumerationer.
    {%- when "th" -%}อัปเดต <emailPreferences>การตั้งค่าอีเมล</emailPreferences>เพื่อเลือกอีเมลที่คุณต้องการรับหรือ <unsubscribe>ยกเลิกการสมัคร</unsubscribe>รับอีเมลทั้งหมด
    {%- when "tr" -%}<emailPreferences>E-posta tercihlerinizi</emailPreferences> güncelleyerek hangi e-postaları alacağınızı belirleyebilir ya da tüm e-posta <unsubscribe>aboneliklerinden çıkabilirsiniz</unsubscribe>.
    {%- when "uk" -%}Оновіть <emailPreferences>налаштування електронних листів</emailPreferences>, щоб вибрати, які електронні листи отримувати, або <unsubscribe>відмовитися від підписки</unsubscribe> на всі електронні листи.
    {%- when "vi" -%}Cập nhật <emailPreferences>tùy chọn email</emailPreferences> của bạn để chọn email bạn nhận được hoặc <unsubscribe>hủy đăng ký</unsubscribe> khỏi tất cả email.
    {%- else -%}Update your <emailPreferences>email preferences</emailPreferences> to choose which emails you get or <unsubscribe>unsubscribe</unsubscribe> from all emails.
  {%- endcase -%}
{%- endcapture -%}
{%- capture email_prefs_open -%}<a href="{{snippets.vio_notification_preferences}}" style="color:inherit;text-decoration:underline !important" target="_blank">{%- endcapture -%}
{%- capture email_prefs_close -%}</a>{%- endcapture -%}
{%- capture unsub_open -%}<a href="{{snippets.vio_notification_preferences_unsubscribe}}" class="untracked" style="color:inherit;text-decoration:underline !important" target="_blank">{%- endcapture -%}
{%- capture unsub_close -%}</a>{%- endcapture -%}
{%- assign footer_prefs_html = footer_prefs_text | replace: "<emailPreferences>", email_prefs_open | replace: "</emailPreferences>", email_prefs_close | replace: "<unsubscribe>", unsub_open | replace: "</unsubscribe>", unsub_close -%}
''' + PLACEHOLDER_TERMS_DEFAULTS + '''
{%- capture terms_link -%}<a href="{{ link_terms_of_use }}" target="_blank" style="color:{{ token_text_muted }};text-decoration:underline !important">{{ terms_label | strip }}</a>{%- endcapture -%}
{%- capture privacy_link -%}<a href="{{ link_privacy_policy }}" target="_blank" style="color:{{ token_text_muted }};text-decoration:underline !important">{{ privacy_label | strip }}</a>{%- endcapture -%}
{%- assign terms_desc_html = terms_desc_text | replace: "{terms}", terms_link | replace: "{privacyPolicy}", privacy_link -%}

<!doctype html>
<html lang="{{ locale_key }}" dir="{{ dir }}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <meta name="x-apple-disable-message-reformatting" />
    <title>{{ subject_line | strip | default: "Email" }}</title>
    <style type="text/css">
      .email-img-desktop { display: block !important; }
      .email-img-mobile { display: none !important; }
      @media only screen and (max-width: 600px) {
        .email-app-card { width: 100% !important; max-width: 100% !important; padding: 16px 20px !important; }
        .email-app-stores .email-app-store-cell { display: block !important; width: 100% !important; padding-right: 0 !important; padding-bottom: 16px !important; }
        .email-app-stores .email-app-store-cell:last-child { padding-bottom: 0 !important; }
        .email-img-desktop { display: none !important; }
        .email-img-mobile { display: block !important; }
        .email-outer-pad { padding: 16px 10px !important; }
        .email-card { width: 100% !important; max-width: 100% !important; border-radius: 12px !important; }
        .email-content-above { padding: 20px 20px 0 20px !important; }
        .email-content-below { padding: 0 20px 24px 20px !important; }
        .email-inner-content { width: 100% !important; max-width: 100% !important; }
        .email-footer-pad { padding: 0 20px !important; }
        .email-app-module-outer td { padding-left: 20px !important; padding-right: 20px !important; }
        .email-feature-col { display: block !important; width: 100% !important; padding-left: 0 !important; padding-right: 0 !important; }
        .email-feature-row { display: block !important; }
        .email-feature-row td { display: block !important; width: 100% !important; padding: 0 0 24px 0 !important; }
        .email-feature-row td:first-child { padding-bottom: 16px !important; }
        .email-usp-feature-row td { display: block !important; width: 100% !important; padding: 0 0 24px 0 !important; }
        .email-usp-feature-row td:first-child { padding-bottom: 16px !important; }
        .email-usp-ui-row td { display: block !important; width: 100% !important; padding: 0 0 24px 0 !important; }
        .email-usp-ui-row td:first-child { padding-bottom: 16px !important; }
        .email-hero-two-col-headline-box { width: 100% !important; max-width: 100% !important; }
        .email-hero-two-col-cta-wrap { width: 100% !important; }
        .email-hero-two-col-cta-cell { width: 100% !important; }
        .email-hero-two-col-cta { width: 100% !important; }
        .email-header-pad { width: 100% !important; max-width: 520px !important; height: 32px !important; padding: 1px 0 !important; }
        .email-terms-outer { padding: 0 10px 20px !important; }
        .email-terms-inner { padding-left: 16px !important; padding-right: 16px !important; }
      }
    </style>
  </head>
  <body style="margin:0;padding:0;background:{{ token_bg_page }};">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;visibility:hidden;mso-hide:all;">{{ preheader | strip }}</div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{{ token_bg_page }}" style="width:100%;background:{{ token_bg_page }};">
      <tr>
        <td align="center" class="email-outer-pad" style="padding:{{ token_space_800 }} {{ token_space_300 }};">
          <table role="presentation" width="{{ token_width_page }}" cellpadding="0" cellspacing="0" border="0" class="email-card" style="width:{{ token_width_page }}px;max-width:{{ token_width_page }}px;background:{{ token_bg_card }};border-radius:{{ token_radius_card }};">
            <tr>
              <td class="email-content-above" style="padding:{{ token_space_900 }} {{ token_space_1200 }} 0 {{ token_space_1200 }};">
                <table role="presentation" width="{{ token_width_content }}" cellpadding="0" cellspacing="0" border="0" class="email-inner-content" style="width:{{ token_width_content }}px;max-width:{{ token_width_content }}px;margin:0 auto;border-collapse:collapse;">
                  <tbody>
                    {%- assign _show_header_logo_raw = show_header_logo | default: "TRUE" | downcase | strip -%}
                    {%- assign _show_header_logo = true -%}
                    {%- if _show_header_logo_raw == "false" or _show_header_logo_raw == "0" or _show_header_logo_raw == "" -%}{%- assign _show_header_logo = false -%}{%- endif -%}
                    {%- if _show_header_logo -%}
                    <tr>
                      <td align="center" class="email-header-pad" style="width:520px;height:32px;max-width:100%;padding:1px 0;opacity:1;line-height:0;">
                        <img src="{{ token_header_logo_url }}" width="89" height="30" alt="{{ token_header_logo_alt }}" style="width:89px;height:30px;max-width:520px;max-height:32px;display:block;margin:0 auto;object-fit:contain;" />
                      </td>
                    </tr>
                    {%- endif -%}
''' + PLACEHOLDER_ROWS_ABOVE_IMAGE + '''
                  </tbody>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:0;line-height:0;font-size:0;">
''' + PLACEHOLDER_IMAGE_ROW + '''
              </td>
            </tr>
            <tr>
              <td class="email-content-below" style="padding:0 {{ token_space_1200 }} {{ token_space_900 }} {{ token_space_1200 }};">
                <table role="presentation" width="{{ token_width_content }}" cellpadding="0" cellspacing="0" border="0" class="email-inner-content" style="width:{{ token_width_content }}px;max-width:{{ token_width_content }}px;margin:0 auto;border-collapse:collapse;">
                  <tbody>
''' + PLACEHOLDER_ROWS_BELOW_IMAGE + '''
''' + PLACEHOLDER_HERO_TWO_COLUMN_MODULE + '''
''' + PLACEHOLDER_ICON_LEFT_TEXT_RIGHT_MODULE + '''
''' + PLACEHOLDER_TEXT_LEFT_IMAGE_RIGHT_MODULE + '''
''' + PLACEHOLDER_ALTERNATING_TEXT_IMAGE_MODULE + '''
''' + PLACEHOLDER_APP_DOWNLOAD_MODULE + '''
                  </tbody>
                </table>
                {%- if show_footer == "TRUE" -%}
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;">
                  <tbody>
                    <tr><td class="email-footer-pad" style="padding:0;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:{{ token_space_900 }} 0;"><tr><td style="height:1px;background-color:{{ token_border }};font-size:1px;line-height:1px">&nbsp;</td></tr></table></td></tr>
                    <tr>
                      <td class="email-footer-pad" style="padding:0;text-align:center;">
                        <img alt="Vio.com" src="https://userimg-assets.customeriomail.com/images/client-env-124967/1770377276677_Vector_HighDef_01KGSBAVCB07TGMTGYZBMPCWD9.png" style="display:block;outline:none;border:none;text-decoration:none;margin:0 auto;" width="90" />
                        <p style="font-size:20px;line-height:28px;font-weight:600;font-family:{{ token_font_stack }};text-align:center;margin:0;color:{{ token_accent }};padding-top:{{ token_space_300 }};padding-bottom:0;direction:{{ dir }};unicode-bidi:plaintext;">
                          {%- assign footer_app_line_html = footer_app_line | replace: ". ", "<br />" | replace: ".", "" -%}
                          {{ footer_app_line_html | strip }}
                        </p>
                        <div style="height:14px;line-height:14px;font-size:1px;">&nbsp;</div>
                        <a href="{{ app_deeplink_url }}" style="padding-right:6px;display:inline-block;text-decoration:none;">
                          <img alt="Download on App Store" src="https://userimg-assets.customeriomail.com/images/client-env-124967/1756808278001_Appstore_Button_01K44YXW18QJ1S6H2NN0EKBNR2.png" style="display:block;outline:none;border:none;text-decoration:none;max-height:40px" height="40">
                        </a>
                        <a href="{{ app_deeplink_url }}" style="padding-left:6px;display:inline-block;text-decoration:none;">
                          <img alt="Get it on Google Play" src="https://userimg-assets.customeriomail.com/images/client-env-124967/1756808171416_GooglePlaystore_Button_01K44YTKYFR6XPYK6S73Q4WZ44.png" style="display:block;outline:none;border:none;text-decoration:none;max-height:40px" height="40">
                        </a>
                        <p style="font-size:12px;line-height:16px;font-weight:450;font-family:{{ token_font_stack }};text-align:center;margin:0;color:{{ token_text_muted }};padding-top:{{ token_space_600 }};padding-bottom:{{ token_space_300 }};direction:{{ dir }};unicode-bidi:plaintext;">{{ footer_address | strip }}</p>
                        <p style="font-size:12px;line-height:16px;font-weight:450;font-family:{{ token_font_stack }};text-align:center;margin:0;color:{{ token_text_muted }};padding-top:0;padding-bottom:0;direction:{{ dir }};unicode-bidi:plaintext;">{{ footer_prefs_html }}</p>
                        <div style="height:40px;line-height:40px;font-size:1px;">&nbsp;</div>
                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="margin:0 auto;">
                          <tr>
                            <td style="padding:0 6px;"><a href="{{ link_instagram }}" target="_blank" style="text-decoration:none;border:none;outline:none;display:inline-block"><img alt="Instagram" src="https://price-watch-email-images-explicit-prod-master.s3.eu-west-1.amazonaws.com/c59fe658/images/vio/vio-instagram.png" style="display:block;outline:none;border:none;text-decoration:none" width="32"></a></td>
                            <td style="padding:0 6px;"><a href="{{ link_facebook }}" target="_blank" style="text-decoration:none;border:none;outline:none;display:inline-block"><img alt="Facebook" src="https://price-watch-email-images-explicit-prod-master.s3.eu-west-1.amazonaws.com/c59fe658/images/vio/vio-facebook.png" style="display:block;outline:none;border:none;text-decoration:none" width="32"></a></td>
                            <td style="padding:0 6px;"><a href="{{ link_linkedin }}" target="_blank" style="text-decoration:none;border:none;outline:none;display:inline-block"><img alt="LinkedIn" src="https://price-watch-email-images-explicit-prod-master.s3.eu-west-1.amazonaws.com/c59fe658/images/vio/vio-linkedin.png" style="display:block;outline:none;border:none;text-decoration:none" width="32"></a></td>
                          </tr>
                        </table>
                        <div style="height:40px;line-height:40px;font-size:1px;">&nbsp;</div>
                      </td>
                    </tr>
                  </tbody>
                </table>
                {%- endif -%}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
    {%- if show_terms == "TRUE" -%}
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{{ token_bg_page }}" style="width:100%;background:{{ token_bg_page }};">
      <tr>
        <td align="center" class="email-terms-outer" style="padding:0 12px 28px;">
          <table align="center" width="{{ token_width_page }}" border="0" cellpadding="0" cellspacing="0" role="presentation" class="email-terms-inner" style="max-width:{{ token_width_page }}px;width:100%;padding-left:{{ token_space_500 }};padding-right:{{ token_space_500 }};">
            <tr>
              <td>
                <p style="font-size:12px;line-height:16px;font-weight:500;font-family:{{ token_font_stack }};text-align:center;margin:0;color:{{ token_text_muted }};padding-top:{{ token_space_800 }};padding-bottom:0;direction:{{ dir }};unicode-bidi:plaintext;">{{ terms_title | strip }}</p>
                <p style="font-size:12px;line-height:16px;font-weight:450;font-family:{{ token_font_stack }};text-align:center;margin:0;color:{{ token_text_muted }};padding-top:0;padding-bottom:{{ token_space_800 }};padding-left:{{ token_space_100 }};direction:{{ dir }};unicode-bidi:plaintext;">{{ terms_desc_html }}</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
    {%- endif -%}
  </body>
</html>
'''


def generate_template(
    csv_path: Path | str,
    *,
    show_header_logo: str = "TRUE",
    show_footer: str = "TRUE",
    show_terms: str = "TRUE",
    app_download_colour_preset: str = "LIGHT",
    design_tokens_brand: str = "vio",
    links_config: dict[str, str] | None = None,
    include_locales: list[str] | None = None,
) -> str:
    """Generate the Liquid email template from a translations CSV. Returns the template string.
    include_locales: locales to include in output (when clauses). If None, inferred from CSV headers."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    locales = include_locales or get_csv_locales(csv_path)
    translations, structure = load_translations(csv_path, include_locales=locales)
    if not translations and not structure:
        sys.exit("No rows found in CSV. Expected column 'Key' and locale columns: en, ar, zh-cn, ...")
    content_captures = build_content_captures(translations, include_locales=locales)
    rows_above = build_rows_above_image(translations)
    image_row = build_image_row(structure)
    rows_below = build_rows_below_image(translations, structure)
    hero_two_col = build_hero_two_column_module(translations, structure)
    icon_left_text_right_module = build_usp_module(translations, structure)
    text_left_image_right_module = build_usp_feature_module(translations, structure)
    alternating_text_image_module = build_usp_ui_module(translations, structure)
    app_download = build_app_download_module(translations, structure)
    config = build_config_block(
        show_header_logo,
        show_footer,
        show_terms,
        app_download_colour_preset,
    )
    design_tokens = _load_design_tokens(brand=design_tokens_brand)
    app_settings = build_app_download_settings(structure)
    links_block = build_links_block(links_config)
    result = (
        BASE_TEMPLATE.replace(PLACEHOLDER_LINKS, links_block)
        .replace(PLACEHOLDER_DESIGN_TOKENS, design_tokens)
        .replace(PLACEHOLDER_APP_DOWNLOAD_SETTINGS, app_settings)
        .replace(PLACEHOLDER_CONTENT_CAPTURES, content_captures)
        .replace(PLACEHOLDER_ROWS_ABOVE_IMAGE, rows_above)
        .replace(PLACEHOLDER_IMAGE_ROW, image_row)
        .replace(PLACEHOLDER_ROWS_BELOW_IMAGE, rows_below)
        .replace(PLACEHOLDER_HERO_TWO_COLUMN_MODULE, hero_two_col)
        .replace(PLACEHOLDER_ICON_LEFT_TEXT_RIGHT_MODULE, icon_left_text_right_module)
        .replace(PLACEHOLDER_TEXT_LEFT_IMAGE_RIGHT_MODULE, text_left_image_right_module)
        .replace(PLACEHOLDER_ALTERNATING_TEXT_IMAGE_MODULE, alternating_text_image_module)
        .replace(PLACEHOLDER_APP_DOWNLOAD_MODULE, app_download)
        .replace(PLACEHOLDER_TERMS_DEFAULTS, build_terms_defaults_block())
        .replace(PLACEHOLDER_CONFIG, config)
    )
    return result


def main():
    parser = argparse.ArgumentParser(description="Generate multi-locale email template from translations CSV (Key + locale columns).")
    parser.add_argument("csv_path", help="Path to translations CSV (see SHEET_STRUCTURE_TRANSLATIONS.md)")
    parser.add_argument("--show-header-logo", dest="show_header_logo", default="TRUE")
    parser.add_argument("--show-footer", dest="show_footer", default="TRUE")
    parser.add_argument("--show-terms", dest="show_terms", default="TRUE")
    parser.add_argument(
        "--app-download-colour-preset",
        dest="app_download_colour_preset",
        default="LIGHT",
        help='App download banner colour preset: LIGHT (#fcf7f5) or DARK (#7130c9). Override per campaign via app_download_colour_preset merge field.',
    )
    parser.add_argument(
        "--design-tokens-brand",
        dest="design_tokens_brand",
        choices=DESIGN_TOKENS_BRANDS,
        default="vio",
        help="Design token set: vio (default) or holiday_pirates.",
    )
    parser.add_argument(
        "--locale-preset",
        dest="locale_preset",
        choices=["en_only", "top_5", "global"],
        default=None,
        help="Limit output to: en_only, top_5 (EN+ES+FR+JA+AR+PT), or global (all). Default: use all locales in CSV.",
    )
    parser.add_argument(
        "--include-locales",
        dest="include_locales",
        default=None,
        help="Comma-separated locale codes, e.g. en,es,fr. Overrides --locale-preset.",
    )
    args = parser.parse_args()
    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        sys.exit(f"CSV file not found: {csv_path}")
    include_locales = None
    if args.include_locales:
        include_locales = [x.strip() for x in args.include_locales.split(",") if x.strip()]
    elif args.locale_preset:
        include_locales = resolve_include_locales(args.locale_preset)
    result = generate_template(
        csv_path,
        show_header_logo=args.show_header_logo,
        show_footer=args.show_footer,
        show_terms=args.show_terms,
        app_download_colour_preset=args.app_download_colour_preset,
        design_tokens_brand=args.design_tokens_brand,
        include_locales=include_locales,
    )
    sys.stdout.write(result)


def _parse_design_tokens(brand: str = "vio") -> dict[str, str]:
    """Parse design tokens for the given brand and return token_name -> value map."""
    import re
    tokens_path = _get_design_tokens_path(brand)
    if not tokens_path.exists():
        return {}
    text = tokens_path.read_text(encoding="utf-8")
    # Match {%- assign token_xyz = "value" -%} or = number -%}
    pattern = r"assign\s+(token_\w+)\s*=\s*\"([^\"]*)\""
    tokens = dict(re.findall(pattern, text))
    # Resolve token refs (e.g. token_bg_page = token_neutral_c050)
    for _ in range(3):
        for k, v in list(tokens.items()):
            if v.startswith("token_") and v in tokens:
                tokens[k] = tokens[v]
    return tokens


def liquid_to_preview_html(
    liquid_content: str,
    translations: dict[str, dict[str, str]],
    structure: dict[str, str],
    *,
    show_header_logo: bool = True,
    show_footer: bool = True,
    show_terms: bool = True,
    design_tokens_brand: str = "vio",
) -> str:
    """
    Convert Liquid template to static HTML for preview (English locale).
    Does regex substitution of tokens and content; strips Liquid control flow.
    """
    import re
    tokens = _parse_design_tokens(brand=design_tokens_brand)
    en = "en"
    # Content replacements from translations (en locale)
    content_vars = [
        "subject_line", "preheader", "headline", "headline_2", "secondary_headline",
        "body_1", "body_2", "cta_text", "app_download_title",
        "app_download_feature_1", "app_download_feature_2", "app_download_feature_3",
        "hero_two_col_body_1_h2", "hero_two_col_body_1_copy", "hero_two_col_body_2_h2",
        "hero_two_col_body_2_copy", "hero_two_col_body_3_h2", "hero_two_col_body_3_copy",
        "hero_two_col_body_4_h2", "hero_two_col_body_4_copy", "hero_two_col_cta_text",
        "terms_title", "terms_desc_text", "terms_label", "privacy_label",
        "usp_title", "usp_1_heading", "usp_1_copy", "usp_2_heading", "usp_2_copy",
        "usp_3_heading", "usp_3_copy",
        "usp_feature_title",         "usp_feature_1_heading", "usp_feature_1_copy",
        "usp_feature_2_heading", "usp_feature_2_copy", "usp_feature_3_heading", "usp_feature_3_copy",
        "usp_ui_title", "usp_ui_1_heading", "usp_ui_1_copy",
        "usp_ui_2_heading", "usp_ui_2_copy", "usp_ui_3_heading", "usp_ui_3_copy",
    ]
    replacements: dict[str, str] = {}
    for k in content_vars:
        v = (translations.get(k) or {}).get(en, "")
        replacements[f"{{{{ {k} | strip }}}}"] = v
        replacements[f"{{{{ {k} }}}}"] = v
    # Token replacements
    for name, val in tokens.items():
        replacements[f"{{{{ {name} }}}}"] = val
    # Simple vars
    replacements["{{ dir }}"] = "ltr"
    replacements["{{ align }}"] = "left"
    replacements["{{ headline_align }}"] = "center"
    replacements["{{ locale_key }}"] = "en"
    replacements["{{ app_deeplink_url }}"] = structure.get("image_deeplink") or DEFAULT_LINKS["app_download_page"]
    replacements["{{ app_download_colour }}"] = tokens.get("token_neutral_c050", "#fcf7f5")
    replacements["{{ google_play_badge_url }}"] = "https://userimg-assets.customeriomail.com/images/client-env-124967/1771236964477_GetItOnGooglePlay_Badge_Web_color_English_01KHJZ6E5TKNXTSE65NBZACEG9.png"
    replacements["{{ app_store_badge_url }}"] = "https://userimg-assets.customeriomail.com/images/client-env-124967/1771861742970_en_01KJ5K15DG7W6K6VRFV8G3ZN6D.png"
    # Link variables (from standard_links)
    for key, url in DEFAULT_LINKS.items():
        var = "link_" + key.replace(".", "_").replace("-", "_")
        replacements[f"{{{{ {var} }}}}"] = url if "snippets" not in url else "#"
    replacements["{{ app_download_text_colour }}"] = tokens.get("token_text_primary", "#180c06")
    # Footer/terms placeholders
    replacements["{{ footer_app_line }}"] = "Book like an insider. Download the app."
    replacements["{{ footer_address | strip }}"] = "FindHotel B.V. Nieuwe Looiersdwarsstraat 17, 1017 TZ, Amsterdam, The Netherlands."
    replacements["{{ terms_title | strip }}"] = (translations.get("terms_title") or {}).get(en, "Terms and Privacy Policy")
    replacements["{{ footer_prefs_html }}"] = "Update your email preferences or unsubscribe."
    terms_desc = (translations.get("terms_desc_text") or {}).get(en, "This booking is covered by our {terms} and {privacyPolicy}.")
    terms_lbl = (translations.get("terms_label") or {}).get(en, "Terms")
    privacy_lbl = (translations.get("privacy_label") or {}).get(en, "Privacy Policy")
    link_terms = DEFAULT_LINKS.get("terms_of_use", "#")
    link_privacy = DEFAULT_LINKS.get("privacy_policy", "#")
    muted = tokens.get("token_text_muted", "#615a56")
    terms_a = f'<a href="{link_terms}" target="_blank" style="color:{muted};text-decoration:underline !important">{terms_lbl}</a>'
    privacy_a = f'<a href="{link_privacy}" target="_blank" style="color:{muted};text-decoration:underline !important">{privacy_lbl}</a>'
    replacements["{{ terms_desc_html }}"] = terms_desc.replace("{terms}", terms_a).replace("{privacyPolicy}", privacy_a)

    html = liquid_content
    for k, v in replacements.items():
        html = html.replace(k, v)

    # Strip {%- if show_header_logo -%}...{%- endif -%} based on flags
    def _replace_conditional(prefix: str, keep: bool):
        nonlocal html
        pattern = rf'({{%-?\s*if\s+{prefix}[^%]+-?%}})(.*?)({{%-?\s*endif\s+-?%}})'
        if keep:
            html = re.sub(pattern, r"\2", html, flags=re.DOTALL)
        else:
            html = re.sub(pattern, "", html, flags=re.DOTALL)

    _replace_conditional("_show_header_logo", show_header_logo)
    _replace_conditional("show_header_logo", show_header_logo)
    _replace_conditional("show_footer", show_footer)
    _replace_conditional("show_terms", show_terms)
    _replace_conditional("app_download_title != blank", "app_download_title" in translations)
    _replace_conditional("hero_two_col_body_1_h2 != blank", "hero_two_col_body_1_h2" in translations)
    _replace_conditional("usp_title != blank", "usp_title" in translations)
    _replace_conditional("usp_feature_title != blank", "usp_feature_title" in translations)
    _replace_conditional("usp_ui_title != blank", "usp_ui_title" in translations)

    # Remove remaining Liquid: comments, assigns, captures, case/when, for
    html = re.sub(r"{%-?\s*comment\s+-?%}.*?{%-?\s*endcomment\s+-?%}", "", html, flags=re.DOTALL)
    html = re.sub(r"{%-?\s*assign\s+[^%]+-?%}", "", html)
    html = re.sub(r"{%-?\s*capture\s+\w+\s+-?%}.*?{%-?\s*endcapture\s+-?%}", "", html, flags=re.DOTALL)
    html = re.sub(r"{%-?\s*case\s+[^%]+-?%}.*?{%-?\s*endcase\s+-?%}", "", html, flags=re.DOTALL)
    html = re.sub(r"{%-?\s*(?:if|elsif|else|endif|when|for|endfor|break)\s+[^%]*-?%}", "", html)
    # Replace any remaining {{ var }} with empty string to avoid broken output
    html = re.sub(r"{{[^}]*}}", "", html)
    return html


if __name__ == "__main__":
    main()
