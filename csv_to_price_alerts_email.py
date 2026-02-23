#!/usr/bin/env python3
"""
Generate the Price Alerts email template from a translations CSV.
CSV: Key + locale columns (subject_line, preheader, headline, body_1, body_2, cta_text).
See SHEET_STRUCTURE_TRANSLATIONS.md for locale column order.

Usage:
  python3 csv_to_price_alerts_email.py price_alerts_translations.csv > price_alerts_full_email.liquid
  python3 csv_to_price_alerts_email.py price_alerts_translations.csv -o price_alerts_full_email.liquid
"""
import argparse
import csv
import json
import sys
from pathlib import Path

LOCALE_COLUMNS = [
    "en", "ar", "zh-cn", "zh-tw", "zh-hk", "hr", "cs", "da", "nl", "en-gb",
    "fil", "fi", "fr", "fr-ca", "de", "el", "he", "hu", "id", "it", "ja", "ko",
    "ms", "no", "pl", "pt", "pt-br", "ro", "ru", "es", "es-419", "sv", "th",
    "tr", "uk", "vi",
]

PRICE_ALERTS_KEYS = ["subject_line", "preheader", "headline", "body_1", "body_2", "cta_text"]
# Map CSV keys to JSON keys
KEY_TO_JSON = {
    "subject_line": "subject",
    "preheader": "preheader",
    "headline": "headline",
    "body_1": "body1",
    "body_2": "body2",
    "cta_text": "cta",
}


def load_translations(csv_path: Path) -> dict[str, dict[str, str]]:
    """Load translations from CSV. Returns translations[key][locale] = value."""
    translations: dict[str, dict[str, str]] = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        if not reader.fieldnames:
            return translations
        key_col = reader.fieldnames[0]
        locale_to_header = {}
        for i, loc in enumerate(LOCALE_COLUMNS):
            if i + 1 < len(reader.fieldnames):
                locale_to_header[loc] = reader.fieldnames[i + 1]
        for row in reader:
            key = (row.get(key_col) or "").strip().lower().replace(" ", "")
            if not key or key not in PRICE_ALERTS_KEYS:
                continue
            values_by_locale = {}
            for loc in LOCALE_COLUMNS:
                header = locale_to_header.get(loc)
                val = (row.get(header, "") if header else "").strip()
                values_by_locale[loc] = val
            en_val = values_by_locale.get("en", "").strip()
            for loc in LOCALE_COLUMNS:
                if not values_by_locale.get(loc, "").strip():
                    values_by_locale[loc] = en_val
            translations[key] = values_by_locale
    return translations


def build_i18n_json(translations: dict[str, dict[str, str]]) -> str:
    """Build the price_alerts_i18n_json string from translations."""
    i18n: dict[str, dict[str, str]] = {}
    for loc in LOCALE_COLUMNS:
        i18n[loc] = {}
        for csv_key, json_key in KEY_TO_JSON.items():
            if csv_key in translations:
                val = translations[csv_key].get(loc, "").strip()
                i18n[loc][json_key] = val
    return json.dumps(i18n, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Price Alerts email template from translations CSV"
    )
    parser.add_argument(
        "csv",
        type=Path,
        help="Path to price_alerts_translations.csv",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file (default: stdout)",
    )
    args = parser.parse_args()
    if not args.csv.exists():
        sys.exit(f"Error: CSV not found: {args.csv}")

    translations = load_translations(args.csv)
    if not translations:
        sys.exit("Error: No translations found in CSV. Expected keys: subject_line, preheader, headline, body_1, body_2, cta_text")

    i18n_json = build_i18n_json(translations)

    # Read the base template (this script's sibling)
    script_dir = Path(__file__).parent
    template_path = script_dir / "price_alerts_full_email.liquid"
    if not template_path.exists():
        sys.exit(f"Error: Base template not found: {template_path}")

    template = template_path.read_text(encoding="utf-8")

    # Replace the JSON block. The block is between {%- capture price_alerts_i18n_json -%} and {%- endcapture -%}
    start_marker = "{%- capture price_alerts_i18n_json -%}\n"
    end_marker = "\n{%- endcapture -%}"
    start_idx = template.find(start_marker)
    end_idx = template.find(end_marker, start_idx) if start_idx >= 0 else -1

    if start_idx < 0 or end_idx < 0:
        sys.exit("Error: Could not find price_alerts_i18n_json block in template")

    new_template = (
        template[: start_idx + len(start_marker)]
        + i18n_json
        + template[end_idx:]
    )

    out = args.output
    if out:
        out.write_text(new_template, encoding="utf-8")
        print(f"Generated: {out}", file=sys.stderr)
    else:
        print(new_template)


if __name__ == "__main__":
    main()
