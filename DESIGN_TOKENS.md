# Design Tokens – Vio Email System

Design tokens standardize colors, spacing, and layout across all email templates. Edit `design_tokens.liquid` to change the design system; templates use these tokens.

## Usage

`design_tokens.liquid` is injected into the generated template. Use tokens in inline styles:

```liquid
style="color:{{ token_accent }}; padding:{{ token_space_600 }} {{ token_space_800 }};"
style="background:{{ token_bg_page }}; font-family:{{ token_font_stack }};"
```

## Colour Tokens

Full scale per primitive: `token_{scale}_c{step}` (steps 050, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950; neutral also has c000, c999).

| Scale | Key tokens | Use |
|-------|------------|-----|
| **neutral** | c000 #ffffff, c050 #fcf7f5, c200 #ddd7d5, c600 #615a56, c950 #180c06, c999 #000000 | Grays, page bg, text |
| **brand** | c050 #f8f5ff, c600 #7130c9, c700 #5700a9 | Brand purple |
| **interactive** | c050 #f9f5ff, c600 #7130c9 | Same as brand for email |
| **success** | c050 #ebffec, c600 #2ea54a | Success states |
| **warning** | c050 #fff9f3, c200 #ffdab8, c300 #ffb670, c950 #4a1c00 | Alerts |
| **danger** | c050 #fff2f4, c600 #d91b38 | Error states |
| **accent** | c050 #fffbf0, c500 #ffc103, c600 #faab00 | Gold/yellow accent |

### Semantic Aliases

| Token | Maps to | Use |
|-------|---------|-----|
| `token_bg_page` | neutral_c050 | Page background |
| `token_bg_card` | neutral_c000 | Card/container background |
| `token_bg_brand` | brand_c600 | Brand backgrounds |
| `token_text_primary` | neutral_c950 | Primary text |
| `token_text_body` | #111111 | Body paragraph text |
| `token_text_muted` | neutral_c600 | Muted/secondary text |
| `token_text_on_brand` | neutral_c000 | Text on brand background |
| `token_accent` | brand_c600 | Accent/emphasis |
| `token_border` | neutral_c200 | Borders, dividers |
| `token_cta_bg` | brand_c600 | CTA button background |

## Spacing Tokens

| Token | Value |
|-------|-------|
| `token_space_100` | 4px |
| `token_space_200` | 8px |
| `token_space_300` | 12px |
| `token_space_400` | 16px |
| `token_space_500` | 20px |
| `token_space_600` | 24px |
| `token_space_700` | 28px |
| `token_space_800` | 32px |
| `token_space_900` | 40px |
| `token_space_1000` | 48px |
| `token_space_1200` | 64px |

## Layout Tokens

| Token | Value |
|-------|-------|
| `token_width_page` | 728 |
| `token_width_content` | 600 |
| `token_radius_card` | 24px |
| `token_radius_button` | 10px |
| `token_radius_module` | 16px |
| `token_font_stack` | Campton, Circular, Helvetica, Arial, sans-serif |

## App download block colour

The app download block has a **toggle at the top** of the template (next to `show_header_logo`, `show_footer`, `show_terms`):

- **`app_download_colour_preset`** – `"LIGHT"` (cream `#fcf7f5`) or `"DARK"` (brand purple `#7130c9`). Set at build time: `--app-download-colour-preset DARK`. Override per campaign via merge field `app_download_colour_preset`.
- **`app_download_colour`** – Optional hex override (merge field). When set, overrides the preset.
- **Auto text colour** – Light backgrounds (#fcf7f5, #ffffff, #f8f5ff, #eee9e7, #ddd7d5) use dark text (`token_text_primary`). Other backgrounds use white text (`token_text_on_brand`).

---

## Adding to Other Emails

To use tokens in another Liquid template:

1. Copy the contents of `design_tokens.liquid` into the top of your template (after locale setup).
2. Replace hardcoded values with token references.

For Customer.io, the script injects tokens automatically when generating from CSV.
