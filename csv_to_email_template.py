#!/usr/bin/env python3
"""
Generate full Customer.io email template from a CSV file of modules.
Usage:
  python3 csv_to_email_template.py email_modules.csv > full_email_template.liquid
  python3 csv_to_email_template.py email_modules.csv --show-footer FALSE > full_email_template.liquid
"""
import argparse
import csv
import sys
from pathlib import Path

PLACEHOLDER_CONFIG = "{{ MODULES_CONFIG_BLOCK }}"
PLACEHOLDER_ROWS_ABOVE_IMAGE = "{{ MODULES_ROWS_ABOVE_IMAGE }}"
PLACEHOLDER_IMAGE_ROW = "{{ MODULES_IMAGE_ROW }}"
PLACEHOLDER_ROWS_BELOW_IMAGE = "{{ MODULES_ROWS_BELOW_IMAGE }}"

# Base template: Liquid + HTML. Outer card 728px; inner content area 600px (via padding 64px).
BASE_TEMPLATE = r'''{%- comment -%}
FULL EMAIL HTML (Design Studio-friendly)
- Message/template language: LIQUID
- Requires snippets: snippets.vio_notification_preferences, snippets.vio_notification_preferences_unsubscribe
- app_deeplink_url: set your AppsFlyer / deep link. (Fallback included)
{%- endcomment -%}

{%- assign lang = customer.language | default: "en" | downcase | replace: "_", "-" -%}
{%- assign lang2 = lang | slice: 0, 2 -%}
{%- assign locale_key = lang2 -%}
{%- if lang2 == "iw" -%}{%- assign locale_key = "he" -%}{%- endif -%}
{%- if lang2 == "tl" -%}{%- assign locale_key = "fil" -%}{%- endif -%}
{%- if lang2 == "nb" or lang2 == "nn" -%}{%- assign locale_key = "no" -%}{%- endif -%}
{%- if lang contains "zh-hk" or lang contains "zh-hant-hk" -%}{%- assign locale_key = "zh-hk" -%}
{%- elsif lang contains "zh-tw" or lang contains "zh-hant" -%}{%- assign locale_key = "zh-tw" -%}
{%- elsif lang contains "zh-cn" or lang contains "zh-sg" or lang contains "zh-hans" -%}{%- assign locale_key = "zh-cn" -%}
{%- elsif lang contains "fr-ca" -%}{%- assign locale_key = "fr-ca" -%}
{%- elsif lang contains "pt-br" -%}{%- assign locale_key = "pt-br" -%}
{%- elsif lang contains "es-419" -%}{%- assign locale_key = "es-419" -%}
{%- elsif lang contains "en-gb" -%}{%- assign locale_key = "en-gb" -%}
{%- endif -%}

{%- assign rtl_locales = "ar,he" | split: "," -%}
{%- assign dir = "ltr" -%}
{%- if rtl_locales contains locale_key -%}{%- assign dir = "rtl" -%}{%- endif -%}
{%- assign headline_align = "center" -%}
{%- if locale_key == "ar" or locale_key == "he" -%}{%- assign headline_align = "right" -%}{%- endif -%}
{%- assign align = "left" -%}
{%- if locale_key == "ar" or locale_key == "he" -%}{%- assign align = "right" -%}{%- endif -%}
{%- assign app_deeplink_url = app_deeplink_url | default: "https://www.vio.com/app" -%}

{%- capture footer_app_line -%}
  {%- case locale_key -%}
    {%- when "ar" -%}احجز كأهل البلد. حمّل التطبيق.
    {%- when "zh-cn" -%}订房有一套。 下载应用。
    {%- when "zh-tw" -%}懂玩的人，都這樣訂房 下載應用程式
    {%- when "zh-hk" -%}訂得安心。 下載應用程式。
    {%- when "nl" -%}Boeken zonder poespas. Download de app.
    {%- when "en-gb" -%}Book like an insider. Download the app.
    {%- when "en" -%}Book like an insider. Download the app.
    {%- when "fr" -%}Réserver sans se tromper. Télécharger l'application.
    {%- when "de" -%}Buchen mit klarem Blick. App herunterladen.
    {%- when "es" -%}Reservar sin equivocarse. Descarga la app.
    {%- else -%}Book like an insider. Download the app.
  {%- endcase -%}
{%- endcapture -%}
{%- capture footer_address -%}FindHotel B.V. Nieuwe Looiersdwarsstraat 17, 1017 TZ, Amsterdam, The Netherlands.{%- endcapture -%}

{%- capture footer_prefs_text -%}
  {%- case locale_key -%}
    {%- when "en-gb" -%}Update your <emailPreferences>email preferences</emailPreferences> to choose which emails you get or <unsubscribe>unsubscribe</unsubscribe> from all emails.
    {%- when "en" -%}Update your <emailPreferences>email preferences</emailPreferences> to choose which emails you get or <unsubscribe>unsubscribe</unsubscribe> from all emails.
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
    {%- when "de" -%}Bedingungen und Richtlinien
    {%- when "nl" -%}Algemene voorwaarden en privacybeleid
    {%- when "en-gb" -%}Terms and Privacy Policy
    {%- when "en" -%}Terms and Privacy Policy
    {%- else -%}Terms and Privacy Policy
  {%- endcase -%}
{%- endcapture -%}
{%- capture terms_label -%}{%- case locale_key -%}{%- when "de" -%}Bedingungen{%- when "en" -%}Terms{%- else -%}Terms{%- endcase -%}{%- endcapture -%}
{%- capture privacy_label -%}{%- case locale_key -%}{%- when "de" -%}Datenschutzrichtlinie{%- when "en" -%}Privacy Policy{%- else -%}Privacy Policy{%- endcase -%}{%- endcapture -%}
{%- capture terms_link -%}<a href="https://www.vio.com/terms-of-use" target="_blank" style="color:#615a56;text-decoration:underline !important">{{ terms_label | strip }}</a>{%- endcapture -%}
{%- capture privacy_link -%}<a href="https://www.vio.com/privacy-policy" target="_blank" style="color:#615a56;text-decoration:underline !important">{{ privacy_label | strip }}</a>{%- endcapture -%}
{%- capture terms_desc_text -%}
  {%- case locale_key -%}
    {%- when "zh-tw" -%}Vio.com 處理並協助您完成預訂。我們的 {terms} 和 {privacyPolicy} 承保此預訂。
    {%- when "hr" -%}Vio.com obrađuje i pomaže s vašom rezervacijom. Ova rezervacija pokrivena je našim {terms} i {privacyPolicy}.
    {%- when "en" -%}Vio.com processes and assists with your booking. This booking is covered by our {terms} and {privacyPolicy}.
    {%- else -%}Vio.com processes and assists with your booking. This booking is covered by our {terms} and {privacyPolicy}.
  {%- endcase -%}
{%- endcapture -%}
{%- assign terms_desc_html = terms_desc_text | replace: "{terms}", terms_link | replace: "{privacyPolicy}", privacy_link -%}

{%- comment -%}
===== CONTENT CONFIG (generated by script) =====
show_header_logo, show_footer, show_terms: "TRUE" / "FALSE"
{%- endcomment -%}
''' + PLACEHOLDER_CONFIG + '''

<!doctype html>
<html lang="{{ locale_key }}" dir="{{ dir }}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <meta name="x-apple-disable-message-reformatting" />
    <title>Email</title>
  </head>
  <body style="margin:0;padding:0;background:#FCF7F5;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#FCF7F5" style="width:100%;background:#FCF7F5;">
      <tr>
        <td align="center" style="padding:32px 12px;">
          <table role="presentation" width="728" cellpadding="0" cellspacing="0" border="0" style="max-width:728px;width:100%;background:#ffffff;border-radius:24px;">
            <tr>
              <td style="padding:40px 64px 0 64px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;border-collapse:collapse;">
                  <tbody>
                    {%- assign _show_header_logo_raw = show_header_logo | default: "TRUE" | downcase | strip -%}
                    {%- assign _show_header_logo = true -%}
                    {%- if _show_header_logo_raw == "false" or _show_header_logo_raw == "0" or _show_header_logo_raw == "" -%}{%- assign _show_header_logo = false -%}{%- endif -%}
                    {%- if _show_header_logo -%}
                    <tr>
                      <td align="center" style="padding: 22px 0 10px;">
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
              <td style="padding:0 64px 40px 64px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;border-collapse:collapse;">
                  <tbody>
''' + PLACEHOLDER_ROWS_BELOW_IMAGE + '''
                  </tbody>
                </table>

                {%- if show_footer == "TRUE" -%}
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;">
                  <tbody>
                    <tr><td style="padding:0 24px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:40px 0;"><tr><td style="height:1px;background-color:#ddd7d5;font-size:1px;line-height:1px">&nbsp;</td></tr></table></td></tr>
                    <tr>
                      <td style="padding:0 24px;text-align:center;">
                        <img alt="Vio.com" src="https://userimg-assets.customeriomail.com/images/client-env-124967/1770377276677_Vector_HighDef_01KGSBAVCB07TGMTGYZBMPCWD9.png" style="display:block;outline:none;border:none;text-decoration:none;margin:0 auto;" width="90" />
                        <p style="font-size:20px;line-height:28px;font-weight:600;font-family:Campton, Circular, Helvetica, Arial, sans-serif;text-align:center;margin:0;color:#7130c9;padding-top:12px;padding-bottom:0;direction:{{ dir }};unicode-bidi:plaintext;">
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
                        <p style="font-size:12px;line-height:16px;font-weight:450;font-family:Campton, Circular, Helvetica, Arial, sans-serif;text-align:center;margin:0;color:#615a56;padding-top:24px;padding-bottom:6px;direction:{{ dir }};unicode-bidi:plaintext;">{{ footer_address | strip }}</p>
                        <p style="font-size:12px;line-height:16px;font-weight:450;font-family:Campton, Circular, Helvetica, Arial, sans-serif;text-align:center;margin:0;color:#615a56;padding-top:0;padding-bottom:0;direction:{{ dir }};unicode-bidi:plaintext;">{{ footer_prefs_html }}</p>
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
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#FCF7F5" style="width:100%;background:#FCF7F5;">
      <tr>
        <td align="center" style="padding:0 12px 28px;">
          <table align="center" width="728" border="0" cellpadding="0" cellspacing="0" role="presentation" style="max-width:728px;width:100%;padding-left:20px;padding-right:20px;">
            <tr>
              <td>
                <p style="font-size:12px;line-height:16px;font-weight:500;font-family:Campton, Circular, Helvetica, Arial, sans-serif;text-align:center;margin:0;color:#615a56;padding-top:32px;padding-bottom:0;direction:{{ dir }};unicode-bidi:plaintext;">{{ terms_title | strip }}</p>
                <p style="font-size:12px;line-height:16px;font-weight:450;font-family:Campton, Circular, Helvetica, Arial, sans-serif;text-align:center;margin:0;color:#615a56;padding-top:0;padding-bottom:32px;padding-left:4px;direction:{{ dir }};unicode-bidi:plaintext;">{{ terms_desc_html }}</p>
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


def load_modules_from_csv(path: Path):
    """Load modules from CSV. Columns: module_index, type, headline_1, headline_2, secondary_headline, image_url, image_deeplink, body_copy, cta_text, cta_link, cta_alias."""
    modules_by_index = {}
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            module_type = (row.get("type") or "").strip()
            if not module_type:
                continue
            idx_str = (row.get("module_index") or "0").strip()
            try:
                idx = int(idx_str)
            except ValueError:
                idx = 0
            module = {"type": module_type}
            for field, col in [
                ("headline_1", "headline_1"), ("headline_2", "headline_2"),
                ("secondary_headline", "secondary_headline"), ("image_url", "image_url"),
                ("image_deeplink", "image_deeplink"), ("body_copy", "body_copy"),
                ("cta_text", "cta_text"), ("cta_link", "cta_link"), ("cta_alias", "cta_alias"),
            ]:
                val = (row.get(col) or "").strip()
                if val:
                    module[field] = val
            modules_by_index.setdefault(idx, []).append(module)
    modules = []
    for idx in sorted(modules_by_index.keys()):
        modules.extend(modules_by_index[idx])
    return modules


def html_escape(s: str) -> str:
    s = s or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def normalise_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if "://" not in url:
        return "https://" + url
    return url


def build_config_block(show_header_logo: str, show_footer: str, show_terms: str) -> str:
    def norm(val: str) -> str:
        val = (val or "TRUE").upper()
        return "TRUE" if val not in ("TRUE", "FALSE") else val
    a = norm(show_header_logo)
    b = norm(show_footer)
    c = norm(show_terms)
    return f'{{%- assign show_header_logo = "{a}" -%}}\n{{%- assign show_footer = "{b}" -%}}\n{{%- assign show_terms = "{c}" -%}}'


def _hero_headlines(module: dict) -> str:
    """Headline rows only (above image)."""
    h1 = (module.get("headline_1") or "").strip()
    h2 = (module.get("headline_2") or "").strip()
    sh = (module.get("secondary_headline") or "").strip()
    if not (h1 or h2 or sh):
        return ""
    parts = ["<tr>", '  <td style="padding: 10px 0 18px; text-align: {{ headline_align }}; direction: {{ dir }};">']
    if h1:
        parts.append('    <h1 style="margin:0;font-family:Campton, Circular, Helvetica, Arial, sans-serif;font-size:32px;line-height:38px;color:#6d33d9;font-weight:600;direction:{{ dir }};unicode-bidi:plaintext;">' + html_escape(h1) + "</h1>")
    if h2:
        parts.append('    <p style="margin:10px 0 0 0;font-family:Campton, Circular, Helvetica, Arial, sans-serif;font-size:22px;line-height:28px;font-weight:600;color:#6d33d9;direction:{{ dir }};unicode-bidi:plaintext;">' + html_escape(h2) + "</p>")
    if sh:
        parts.append('    <p style="margin:10px 0 0 0;font-family:Campton, Circular, Helvetica, Arial, sans-serif;font-size:16px;line-height:22px;font-weight:450;color:#111111;direction:{{ dir }};unicode-bidi:plaintext;">' + html_escape(sh) + "</p>")
    parts.append("  </td>")
    parts.append("</tr>")
    return "\n".join(parts)


def _hero_image_row(module: dict) -> str:
    """Single full-width image row (no wrapper tr/td; goes in padding:0 cell)."""
    img_url = (module.get("image_url") or "").strip()
    if not img_url:
        return ""
    img_link = normalise_url(module.get("image_deeplink") or "")
    if img_link:
        return (
            '<a href="' + html_escape(img_link) + '" target="_blank" style="display:block;text-decoration:none;border:0;outline:none;">'
            '<img src="' + html_escape(img_url) + '" width="728" alt="" style="display:block;width:100%;max-width:728px;height:auto;border:0;outline:none;text-decoration:none;" />'
            "</a>"
        )
    return '<img src="' + html_escape(img_url) + '" width="728" alt="" style="display:block;width:100%;max-width:728px;height:auto;border:0;outline:none;text-decoration:none;" />'


def _hero_below_image(module: dict) -> str:
    """Body + CTA rows (below image). Styles aligned with Transparent Pricing template."""
    body = (module.get("body_copy") or "").strip()
    cta_text = (module.get("cta_text") or "").strip()
    cta_link = normalise_url(module.get("cta_link") or "")
    cta_alias = (module.get("cta_alias") or "hero-cta").strip()
    parts = []
    # Body copy: match .copy from reference (padding 28px 0 0, p: 16px/24px, #111111, font-weight 400)
    if body:
        parts.append("<tr>")
        parts.append('  <td style="padding:28px 0 0;direction:{{ dir }};text-align:{{ align }};">')
        parts.append('    <p style="margin:0 0 24px 0;font-size:16px;line-height:24px;color:#111111;font-weight:400;letter-spacing:normal;font-family:Campton, Circular, Helvetica, Arial, sans-serif;direction:{{ dir }};unicode-bidi:plaintext;">' + html_escape(body) + "</p>")
        parts.append("  </td>")
        parts.append("</tr>")
    # CTA: match .cta-wrap and .btn from reference (padding 0 0 22px, block button 16px/20px, border-radius 10px)
    if cta_text and cta_link:
        parts.append("<tr>")
        parts.append('  <td align="center" style="padding:0 0 22px;">')
        parts.append('    <a href="' + html_escape(cta_link) + '" target="_blank" data-cio-tag="' + html_escape(cta_alias) + '" style="display:block;width:100%;background:#6d33d9;color:#ffffff;text-align:center;font-weight:600;font-size:16px;line-height:20px;padding:16px 0;border-radius:10px;letter-spacing:normal;font-family:Campton, Circular, Helvetica, Arial, sans-serif;text-decoration:none;">' + html_escape(cta_text) + "</a>")
        parts.append("  </td>")
        parts.append("</tr>")
    return "\n".join(parts)


def build_module_blocks(modules) -> tuple:
    """Return (above_image_html, image_row_html, below_image_html)."""
    above, image, below = [], [], []
    for m in modules:
        if (m.get("type") or "").strip() != "hero":
            continue
        a = _hero_headlines(m)
        if a:
            above.append(a)
        im = _hero_image_row(m)
        if im:
            image.append(im)
        b = _hero_below_image(m)
        if b:
            below.append(b)
    return ("\n".join(above), "\n".join(image), "\n".join(below))


def main():
    parser = argparse.ArgumentParser(description="Generate full Customer.io email template from a CSV modules file.")
    parser.add_argument("csv_path", help="Path to CSV file with modules")
    parser.add_argument("--show-header-logo", dest="show_header_logo", default="TRUE", help='Show top logo: "TRUE" or "FALSE"')
    parser.add_argument("--show-footer", dest="show_footer", default="TRUE", help='Show footer block: "TRUE" or "FALSE"')
    parser.add_argument("--show-terms", dest="show_terms", default="TRUE", help='Show terms block: "TRUE" or "FALSE"')
    args = parser.parse_args()
    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        sys.exit(f"CSV file not found: {csv_path}")
    modules = load_modules_from_csv(csv_path)
    if not modules:
        sys.exit("No modules found in CSV. Check that the 'type' column is set.")
    config_block = build_config_block(args.show_header_logo, args.show_footer, args.show_terms)
    above, image_row, below = build_module_blocks(modules)
    for ph in (PLACEHOLDER_CONFIG, PLACEHOLDER_ROWS_ABOVE_IMAGE, PLACEHOLDER_IMAGE_ROW, PLACEHOLDER_ROWS_BELOW_IMAGE):
        if ph not in BASE_TEMPLATE:
            sys.exit(f"Placeholder not found in base template: {ph}")
    result = (
        BASE_TEMPLATE.replace(PLACEHOLDER_CONFIG, config_block)
        .replace(PLACEHOLDER_ROWS_ABOVE_IMAGE, above)
        .replace(PLACEHOLDER_IMAGE_ROW, image_row)
        .replace(PLACEHOLDER_ROWS_BELOW_IMAGE, below)
    )
    sys.stdout.write(result)


if __name__ == "__main__":
    main()
