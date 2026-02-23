#!/usr/bin/env python3
"""
Generate a single Customer.io email template with all locales from a translations CSV.
CSV: one row per content key (Key, en, ar, zh-cn, ...). See SHEET_STRUCTURE_TRANSLATIONS.md.
Usage:
  python3 csv_translations_to_email.py email_translations.csv > full_email_template.liquid
"""
import argparse
import csv
import sys
from pathlib import Path

# Locale columns in sheet order (Key is column 0). Must match Liquid locale_key.
LOCALE_COLUMNS = [
    "en", "ar", "zh-cn", "zh-tw", "zh-hk", "hr", "cs", "da", "nl", "en-gb",
    "fil", "fi", "fr", "fr-ca", "de", "el", "he", "hu", "id", "it", "ja", "ko",
    "ms", "no", "pl", "pt", "pt-br", "ro", "ru", "es", "es-419", "sv", "th",
    "tr", "uk", "vi",
]

TRANSLATABLE_KEYS = [
    "subject_line", "preheader", "headline", "headline_2", "secondary_headline",
    "body_1", "body_2", "cta_text",
    "app_download_title", "app_download_feature_1", "app_download_feature_2", "app_download_feature_3",
    "hero_two_col_body_1_h2", "hero_two_col_body_1_copy", "hero_two_col_body_2_h2", "hero_two_col_body_2_copy",
    "hero_two_col_body_3_h2", "hero_two_col_body_3_copy", "hero_two_col_body_4_h2", "hero_two_col_body_4_copy",
    "hero_two_col_cta_text",
]
STRUCTURE_KEYS = [
    "image_url", "image_url_mobile", "image_deeplink", "cta_link", "cta_alias",
    "app_store_rating", "google_play_rating", "app_download_colour",
    "hero_two_col_image_1_url", "hero_two_col_image_2_url", "hero_two_col_image_3_url", "hero_two_col_image_4_url",
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
}

PLACEHOLDER_DESIGN_TOKENS = "{{ DESIGN_TOKENS }}"
PLACEHOLDER_APP_DOWNLOAD_SETTINGS = "{{ APP_DOWNLOAD_SETTINGS }}"
PLACEHOLDER_CONTENT_CAPTURES = "{{ CONTENT_CAPTURES }}"
PLACEHOLDER_ROWS_ABOVE_IMAGE = "{{ ROWS_ABOVE_IMAGE }}"
PLACEHOLDER_IMAGE_ROW = "{{ IMAGE_ROW }}"
PLACEHOLDER_ROWS_BELOW_IMAGE = "{{ ROWS_BELOW_IMAGE }}"
PLACEHOLDER_HERO_TWO_COLUMN_MODULE = "{{ HERO_TWO_COLUMN_MODULE }}"
PLACEHOLDER_APP_DOWNLOAD_MODULE = "{{ APP_DOWNLOAD_MODULE }}"
PLACEHOLDER_CONFIG = "{{ CONFIG_BLOCK }}"


def _load_design_tokens() -> str:
    """Load design tokens from design_tokens.liquid to inject into template."""
    tokens_path = Path(__file__).parent / "design_tokens.liquid"
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


def load_translations(csv_path: Path) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    """
    Read CSV or TSV. Supports two formats:
    A) Legacy: Key, en, ar, ... (locale columns at index 1+)
    B) New: Key, Module, module_index, en, ar, ... (locale columns at index 3+)
    Return (translations[key][locale] = value, structure[key] = single_value).
    """
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
        # Detect format: new format has Module and module_index as columns 1 and 2
        use_module_format = (
            len(fields) >= 3
            and (fields[1] or "").strip().lower() == "module"
            and (fields[2] or "").strip().lower().replace(" ", "") == "module_index"
        )
        locale_start = 3 if use_module_format else 1
        locale_to_header: dict[str, str] = {}
        for i, loc in enumerate(LOCALE_COLUMNS):
            idx = locale_start + i
            if idx < len(fields):
                locale_to_header[loc] = fields[idx]

        key_col = fields[0]
        module_col = fields[1] if use_module_format and len(fields) >= 2 else None

        for row in reader:
            key_raw = (row.get(key_col) or "").strip().lower().replace(" ", "")
            if not key_raw:
                continue
            module_raw = (row.get(module_col, "") or "").strip().lower().replace(" ", "") if module_col else ""
            values_by_locale: dict[str, str] = {}
            for loc in LOCALE_COLUMNS:
                header = locale_to_header.get(loc)
                val = (row.get(header, "") if header else "").strip()
                values_by_locale[loc] = val

            # Resolve internal key
            if use_module_format and module_raw:
                internal_key = MODULE_KEY_MAP.get((module_raw, key_raw))
                if internal_key is None:
                    internal_key = MODULE_KEY_MAP.get((module_raw, key_raw.replace("_", "")))
                if internal_key is None:
                    continue  # Skip unmapped rows
            else:
                internal_key = key_raw

            if internal_key in STRUCTURE_KEYS:
                for loc in LOCALE_COLUMNS:
                    v = values_by_locale.get(loc, "").strip()
                    if v:
                        structure[internal_key] = v
                        break
                if internal_key not in structure:
                    structure[internal_key] = values_by_locale.get("en", "").strip()
            else:
                en_val = values_by_locale.get("en", "").strip()
                for loc in LOCALE_COLUMNS:
                    if not values_by_locale.get(loc, "").strip():
                        values_by_locale[loc] = en_val
                translations[internal_key] = values_by_locale
    return translations, structure


def build_content_captures(translations: dict[str, dict[str, str]]) -> str:
    """Generate Liquid {% capture key %} {% case locale_key %} ... {% endcapture %} for each key."""
    lines = []
    for key in TRANSLATABLE_KEYS:
        if key not in translations:
            continue
        vals = translations[key]
        lines.append("{%- capture " + key + " -%}")
        lines.append("  {%- case locale_key -%}")
        for loc in LOCALE_COLUMNS:
            v = vals.get(loc, "").strip()
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
    apple_btn = "https://price-watch-email-images-explicit-prod-master.s3.eu-west-1.amazonaws.com/199cd19b/apple-store/en.png"
    google_btn = "https://price-watch-email-images-explicit-prod-master.s3.eu-west-1.amazonaws.com/199cd19b/google-play/en.png"
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
                              <img alt="Download on App Store" src="{apple_btn}" style="display:block;outline:none;border:none;text-decoration:none;max-height:40px" height="40"/>
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
                              <img alt="Get it on Google Play" src="{google_btn}" style="display:block;outline:none;border:none;text-decoration:none;max-height:40px" height="40"/>
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
{%- assign app_deeplink_url = app_deeplink_url | default: "https://www.vio.com/app" -%}
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
{%- capture terms_title -%}
  {%- case locale_key -%}
    {%- when "ar" -%}الشروط وسياسة الخصوصية
    {%- when "zh-cn" -%}条款和隐私政策
    {%- when "zh-tw" -%}條款和私隱政策
    {%- when "zh-hk" -%}條款及私隱政策
    {%- when "hr" -%}Uvjeti i politika privatnosti
    {%- when "cs" -%}Podmínky a zásady ochrany osobních údajů
    {%- when "da" -%}Vilkår og Privatlivspolitik
    {%- when "nl" -%}Algemene voorwaarden en privacybeleid
    {%- when "en-gb" -%}Terms and Privacy Policy
    {%- when "en" -%}Terms and Privacy Policy
    {%- when "fil" -%}Mga Tuntunin at Patakaran sa Privacy
    {%- when "fi" -%}Ehdot ja tietosuojakäytäntö
    {%- when "fr" -%}Conditions générales et Politique de confidentialité
    {%- when "fr-ca" -%}Conditions et politique de confidentialité
    {%- when "de" -%}Bedingungen und Richtlinien
    {%- when "el" -%}Όρους και Πολιτική απορρήτου
    {%- when "he" -%}התנאים ומדיניות הפרטיות
    {%- when "hu" -%}Felhasználási feltételek és adatvédelmi szabályzat
    {%- when "id" -%}Ketentuan dan Kebijakan Privasi
    {%- when "it" -%}Termini e Policy
    {%- when "ja" -%}規約とプライバシーポリシー
    {%- when "ko" -%}이용 약관 및 개인정보 보호정책
    {%- when "ms" -%}Terma dan Dasar Privasi
    {%- when "no" -%}Vilkår og personvernpolicy
    {%- when "pl" -%}Warunki i Polityka prywatności
    {%- when "pt" -%}Termos e Política de Privacidade
    {%- when "pt-br" -%}Termos e Política de Privacidade
    {%- when "ro" -%}Termeni și politica de confidențialitate
    {%- when "ru" -%}Условия и политика конфиденциальности
    {%- when "es" -%}Términos y política de privacidad
    {%- when "es-419" -%}Términos y Política de privacidad
    {%- when "sv" -%}Villkor och Integritetspolicy
    {%- when "th" -%}ข้อกำหนดและนโยบายความเป็นส่วนตัว
    {%- when "tr" -%}Koşullar ve Gizlilik Politikası
    {%- when "uk" -%}Умови та політика конфіденційності
    {%- when "vi" -%}Điều khoản và Chính sách bảo mật
    {%- else -%}Terms and Privacy Policy
  {%- endcase -%}
{%- endcapture -%}
{%- capture terms_label -%}
  {%- case locale_key -%}
    {%- when "ar" -%}الشروط
    {%- when "zh-cn" -%}条款
    {%- when "zh-tw" -%}條款
    {%- when "zh-hk" -%}條款
    {%- when "hr" -%}Uvjeti
    {%- when "cs" -%}Podmínky
    {%- when "da" -%}Vilkår
    {%- when "nl" -%}voorwaarden
    {%- when "en-gb" -%}Terms
    {%- when "en" -%}Terms
    {%- when "fil" -%}Mga Tuntunin
    {%- when "fi" -%}Ehdot
    {%- when "fr" -%}Conditions
    {%- when "fr-ca" -%}Conditions
    {%- when "de" -%}Bedingungen
    {%- when "el" -%}Όρους
    {%- when "he" -%}התנאים
    {%- when "hu" -%}Feltételek
    {%- when "id" -%}Ketentuan
    {%- when "it" -%}Termini
    {%- when "ja" -%}規約
    {%- when "ko" -%}이용 약관
    {%- when "ms" -%}Terma
    {%- when "no" -%}Vilkår
    {%- when "pl" -%}Warunki
    {%- when "pt" -%}Termos
    {%- when "pt-br" -%}Termos
    {%- when "ro" -%}Termeni
    {%- when "ru" -%}Условия
    {%- when "es" -%}Términos
    {%- when "es-419" -%}Términos
    {%- when "sv" -%}Villkor
    {%- when "th" -%}ข้อกำหนด
    {%- when "tr" -%}Koşullar
    {%- when "uk" -%}Умови
    {%- when "vi" -%}Điều khoản
    {%- else -%}Terms
  {%- endcase -%}
{%- endcapture -%}
{%- capture privacy_label -%}
  {%- case locale_key -%}
    {%- when "ar" -%}سياسة الخصوصية
    {%- when "zh-cn" -%}隐私政策
    {%- when "zh-tw" -%}私隱政策
    {%- when "zh-hk" -%}私隱政策
    {%- when "hr" -%}politika privatnosti
    {%- when "cs" -%}zásady ochrany osobních údajů
    {%- when "da" -%}Privatlivspolitik
    {%- when "nl" -%}privacybeleid
    {%- when "en-gb" -%}Privacy Policy
    {%- when "en" -%}Privacy Policy
    {%- when "fil" -%}Patakaran sa Privacy
    {%- when "fi" -%}tietosuojakäytäntö
    {%- when "fr" -%}Politique de confidentialité
    {%- when "fr-ca" -%}politique de confidentialité
    {%- when "de" -%}Datenschutzrichtlinie
    {%- when "el" -%}Πολιτική απορρήτου
    {%- when "he" -%}מדיניות הפרטיות
    {%- when "hu" -%}adatvédelmi szabályzat
    {%- when "id" -%}Kebijakan Privasi
    {%- when "it" -%}Informativa sulla privacy
    {%- when "ja" -%}プライバシーポリシー
    {%- when "ko" -%}개인정보 보호정책
    {%- when "ms" -%}Dasar Privasi
    {%- when "no" -%}personvernpolicy
    {%- when "pl" -%}Polityka prywatności
    {%- when "pt" -%}Política de Privacidade
    {%- when "pt-br" -%}Política de Privacidade
    {%- when "ro" -%}politica de confidențialitate
    {%- when "ru" -%}политика конфиденциальности
    {%- when "es" -%}política de privacidad
    {%- when "es-419" -%}Política de privacidad
    {%- when "sv" -%}Integritetspolicy
    {%- when "th" -%}นโยบายความเป็นส่วนตัว
    {%- when "tr" -%}Gizlilik Politikası
    {%- when "uk" -%}політика конфіденційності
    {%- when "vi" -%}Chính sách bảo mật
    {%- else -%}Privacy Policy
  {%- endcase -%}
{%- endcapture -%}
{%- capture terms_link -%}<a href="https://www.vio.com/terms-of-use" target="_blank" style="color:{{ token_text_muted }};text-decoration:underline !important">{{ terms_label | strip }}</a>{%- endcapture -%}
{%- capture privacy_link -%}<a href="https://www.vio.com/privacy-policy" target="_blank" style="color:{{ token_text_muted }};text-decoration:underline !important">{{ privacy_label | strip }}</a>{%- endcapture -%}
{%- capture terms_desc_text -%}
  {%- case locale_key -%}
    {%- when "ar" -%}يعالج Vio.com حجزك ويساعدك فيه. يخضع هذا الحجز لـ {terms} و {privacyPolicy} الخاصة بنا.
    {%- when "zh-cn" -%}Vio.com 会处理预订并协助您完成。此预订适用我们的{terms}和{privacyPolicy}。
    {%- when "zh-tw" -%}Vio.com 處理並協助您完成預訂。我們的 {terms} 和 {privacyPolicy} 承保此預訂。
    {%- when "zh-hk" -%}Vio.com 處理並協助您完成預訂。此預訂由我們的 {terms} 和 {privacyPolicy} 承保。
    {%- when "hr" -%}Vio.com obrađuje i pomaže s vašom rezervacijom. Ova rezervacija pokrivena je našim {terms} i {privacyPolicy}.
    {%- when "cs" -%}Vio.com zpracovává a vyřizuje vaši rezervaci, na kterou se vztahují naše {terms} a {privacyPolicy}.
    {%- when "da" -%}Vio.com behandler og hjælper med din booking. Denne booking er dækket af vores {terms} og {privacyPolicy}.
    {%- when "nl" -%}Vio.com verwerkt je boeking en helpt je daarbij. Onze {terms} en ons {privacyPolicy} zijn van toepassing op deze boeking.
    {%- when "en-gb" -%}Vio.com processes and assists with your booking. This booking is covered by our {terms} and {privacyPolicy}.
    {%- when "en" -%}Vio.com processes and assists with your booking. This booking is covered by our {terms} and {privacyPolicy}.
    {%- when "fil" -%}Pinoproseso at tinutulungan ka ng Vio.com sa pagbu-book mo. Saklaw ng aming {terms} at {privacyPolicy} ang booking na ito.
    {%- when "fi" -%}Vio.com käsittelee varauksesi ja auttaa sen kanssa. {terms} ja {privacyPolicy} koskevat tätä varausta.
    {%- when "fr" -%}Vio.com traite et facilite votre réservation. Cette réservation est soumise à nos {terms} et à notre {privacyPolicy}.
    {%- when "fr-ca" -%}Vio.com traite votre réservation et vous assiste dans le processus. Cette réservation est couverte par nos {terms} et notre {privacyPolicy}.
    {%- when "de" -%}Vio.com bearbeitet Ihre Buchung und unterstützt Sie dabei. Diese Buchung unterliegt unseren {terms} und unserer {privacyPolicy} .
    {%- when "el" -%}Το Vio.com επεξεργάζεται και βοηθά με την κράτησή σας. Αυτή η κράτηση καλύπτεται από τους {terms} και την {privacyPolicy} μας.
    {%- when "he" -%}Vio.com מעבדת את ההזמנה שלך ועוזרת לבצע אותה. הזמנה זו כפופה ל{terms} ול{privacyPolicy} שלנו.
    {%- when "hu" -%}A Vio.com feldolgozza és segíti az Ön foglalását. Erre a foglalásra a {terms} és a {privacyPolicy} érvényes.
    {%- when "id" -%}Vio.com memproses dan membantu pemesanan Anda. Pemesanan ini dilindungi oleh {terms} dan {privacyPolicy} kami.
    {%- when "it" -%}Vio.com elabora e fornisce assistenza per la tua prenotazione. Questa prenotazione è coperta dai {terms} e dalla {privacyPolicy} di Vio.
    {%- when "ja" -%}Vio.comが予約の処理とサポートを行います。この予約には当社の{terms}と{privacyPolicy}が適用されます。
    {%- when "ko" -%}본 예약은 Vio.com에서 처리하고 지원하며, 당사의 {terms} 및 {privacyPolicy}이 적용됩니다.
    {%- when "ms" -%}Vio.com memproses dan membantu dengan tempahan anda. Tempahan ini dilindungi oleh {terms} dan {privacyPolicy} kami.
    {%- when "no" -%}Vio.com behandler og hjelper deg med bestillingen din. Denne bestillingen dekkes av vår {terms} og {privacyPolicy}
    {%- when "pl" -%}Vio.com pomaga w dokonaniu rezerwacji i przetwarza ją. Ta rezerwacja jest objęta naszymi zasadami, których szczegóły zawierają {terms} i {privacyPolicy}.
    {%- when "pt" -%}A Vio.com gere e presta-lhe assistência na reserva. Esta reserva está coberta pelos nossos {terms} e a {privacyPolicy}.
    {%- when "pt-br" -%}Vio.com gerencia e ajuda com sua reserva. Esta reserva é coberta por nossos {terms} e {privacyPolicy}.
    {%- when "ro" -%}Vio.com procesează și te ajută cu rezervarea ta. Această rezervare este acoperită de {terms} și {privacyPolicy}.
    {%- when "ru" -%}Vio.com обрабатывает ваше бронирование и обеспечивает поддержку. На это бронирование распространяются наши {terms} и {privacyPolicy}.
    {%- when "es" -%}Vio.com procesa tu reserva y te ayuda con ella. Esta reserva está cubierta por nuestras {terms} y {privacyPolicy}.
    {%- when "es-419" -%}Vio.com procesa tu reserva y te brinda asistencia con ella. Esta reserva está cubierta por nuestros {terms} y nuestra {privacyPolicy}.
    {%- when "sv" -%}Vio.com behandlar och assisterar med din bokning. Denna bokning täcks av våra {terms} och {privacyPolicy} .
    {%- when "th" -%}Vio.com เป็นผู้ดำเนินการและให้ความช่วยเหลือในการจองของคุณ การจองนี้อยู่ภายใต้{terms} และ{privacyPolicy}ของเรา
    {%- when "tr" -%}Vio.com rezervasyonunuzu işleme alır ve size yardımcı olur. Bu rezervasyon {terms} ve {privacyPolicy} esaslarımız kapsamındadır.
    {%- when "uk" -%}Vio.com обробляє ваше бронювання та допомагає вам у ньому. На це бронювання поширюються наші {terms} та {privacyPolicy}.
    {%- when "vi" -%}Vio.com xử lý và hỗ trợ đặt phòng của bạn. Đặt phòng này được bảo vệ bởi {terms} và {privacyPolicy} của chúng tôi.
    {%- else -%}Vio.com processes and assists with your booking. This booking is covered by our {terms} and {privacyPolicy}.
  {%- endcase -%}
{%- endcapture -%}
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
        .email-hero-two-col-headline-box { width: 100% !important; max-width: 100% !important; }
        .email-hero-two-col-cta-wrap { width: 100% !important; }
        .email-hero-two-col-cta-cell { width: 100% !important; }
        .email-hero-two-col-cta { width: 100% !important; }
        .email-header-pad { padding: 16px 0 8px !important; }
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
                      <td align="center" class="email-header-pad" style="padding: {{ token_space_600 }} 0 {{ token_space_500 }};">
                        <img src="https://userimg-assets.customeriomail.com/images/client-env-124967/1769680583679_Hero_Logo_Vector_4x_01KG4JXF25SSBE0QK36X2MEAXM.png" width="89" height="30" alt="Vio" style="width:89px;height:30px;display:block;margin:0 auto;" />
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
                            <td style="padding:0 6px;"><a href="https://www.instagram.com/vio.com.travel" target="_blank" style="text-decoration:none;border:none;outline:none;display:inline-block"><img alt="Instagram" src="https://price-watch-email-images-explicit-prod-master.s3.eu-west-1.amazonaws.com/c59fe658/images/vio/vio-instagram.png" style="display:block;outline:none;border:none;text-decoration:none" width="32"></a></td>
                            <td style="padding:0 6px;"><a href="https://www.facebook.com/viodotcom" target="_blank" style="text-decoration:none;border:none;outline:none;display:inline-block"><img alt="Facebook" src="https://price-watch-email-images-explicit-prod-master.s3.eu-west-1.amazonaws.com/c59fe658/images/vio/vio-facebook.png" style="display:block;outline:none;border:none;text-decoration:none" width="32"></a></td>
                            <td style="padding:0 6px;"><a href="https://www.linkedin.com/company/viodotcom/" target="_blank" style="text-decoration:none;border:none;outline:none;display:inline-block"><img alt="LinkedIn" src="https://price-watch-email-images-explicit-prod-master.s3.eu-west-1.amazonaws.com/c59fe658/images/vio/vio-linkedin.png" style="display:block;outline:none;border:none;text-decoration:none" width="32"></a></td>
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
) -> str:
    """Generate the Liquid email template from a translations CSV. Returns the template string."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    translations, structure = load_translations(csv_path)
    if not translations and not structure:
        sys.exit("No rows found in CSV. Expected column 'Key' and locale columns: en, ar, zh-cn, ...")
    content_captures = build_content_captures(translations)
    rows_above = build_rows_above_image(translations)
    image_row = build_image_row(structure)
    rows_below = build_rows_below_image(translations, structure)
    hero_two_col = build_hero_two_column_module(translations, structure)
    app_download = build_app_download_module(translations, structure)
    config = build_config_block(
        show_header_logo,
        show_footer,
        show_terms,
        app_download_colour_preset,
    )
    design_tokens = _load_design_tokens()
    app_settings = build_app_download_settings(structure)
    result = (
        BASE_TEMPLATE.replace(PLACEHOLDER_DESIGN_TOKENS, design_tokens)
        .replace(PLACEHOLDER_APP_DOWNLOAD_SETTINGS, app_settings)
        .replace(PLACEHOLDER_CONTENT_CAPTURES, content_captures)
        .replace(PLACEHOLDER_ROWS_ABOVE_IMAGE, rows_above)
        .replace(PLACEHOLDER_IMAGE_ROW, image_row)
        .replace(PLACEHOLDER_ROWS_BELOW_IMAGE, rows_below)
        .replace(PLACEHOLDER_HERO_TWO_COLUMN_MODULE, hero_two_col)
        .replace(PLACEHOLDER_APP_DOWNLOAD_MODULE, app_download)
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
    args = parser.parse_args()
    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        sys.exit(f"CSV file not found: {csv_path}")
    result = generate_template(
        csv_path,
        show_header_logo=args.show_header_logo,
        show_footer=args.show_footer,
        show_terms=args.show_terms,
        app_download_colour_preset=args.app_download_colour_preset,
    )
    sys.stdout.write(result)


def _parse_design_tokens() -> dict[str, str]:
    """Parse design_tokens.liquid and return token_name -> value map."""
    import re
    tokens_path = Path(__file__).parent / "design_tokens.liquid"
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
) -> str:
    """
    Convert Liquid template to static HTML for preview (English locale).
    Does regex substitution of tokens and content; strips Liquid control flow.
    """
    import re
    tokens = _parse_design_tokens()
    en = "en"
    # Content replacements from translations (en locale)
    content_vars = [
        "subject_line", "preheader", "headline", "headline_2", "secondary_headline",
        "body_1", "body_2", "cta_text", "app_download_title",
        "app_download_feature_1", "app_download_feature_2", "app_download_feature_3",
        "hero_two_col_body_1_h2", "hero_two_col_body_1_copy", "hero_two_col_body_2_h2",
        "hero_two_col_body_2_copy", "hero_two_col_body_3_h2", "hero_two_col_body_3_copy",
        "hero_two_col_body_4_h2", "hero_two_col_body_4_copy", "hero_two_col_cta_text",
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
    replacements["{{ app_deeplink_url }}"] = structure.get("image_deeplink") or "https://www.vio.com/app"
    replacements["{{ app_download_colour }}"] = tokens.get("token_neutral_c050", "#fcf7f5")
    replacements["{{ app_download_text_colour }}"] = tokens.get("token_text_primary", "#180c06")
    # Footer/terms placeholders
    replacements["{{ footer_app_line }}"] = "Book like an insider. Download the app."
    replacements["{{ footer_address | strip }}"] = "FindHotel B.V. Nieuwe Looiersdwarsstraat 17, 1017 TZ, Amsterdam, The Netherlands."
    replacements["{{ terms_title | strip }}"] = "Terms and Privacy Policy"
    replacements["{{ footer_prefs_html }}"] = "Update your email preferences or unsubscribe."
    replacements["{{ terms_desc_html }}"] = "This booking is covered by our Terms and Privacy Policy."

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
