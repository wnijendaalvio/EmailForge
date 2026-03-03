"""
Streamlit app for the Email Template Generator.
Upload a translations CSV, configure options, and download the generated Liquid template.
Protected by password authentication (streamlit-authenticator).
"""
import base64
import json
import tempfile
import yaml
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
import streamlit_authenticator as stauth

# Import from the local module (same directory)
from csv_translations_to_email import (
    generate_template,
    generate_standard_input_template,
    get_module_preview_html,
    liquid_to_preview_html,
    load_translations,
    load_standard_links,
    build_customerio_subject_preheader_snippets,
    DEFAULT_LINKS,
    LOCALE_COLUMNS,
    resolve_include_locales,
    DESIGN_TOKENS_BRANDS,
)

st.set_page_config(
    page_title="Email Template Generator",
    page_icon="✉️",
    layout="centered",
)


def _render_copy_button(text: str, key_suffix: str) -> None:
    """Render a button that copies text to clipboard via embedded HTML/JS."""
    b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    html = f"""
    <div id="copy-container-{key_suffix}">
        <button onclick="
            (function(btn) {{
                const binary = atob('{b64}');
                const bytes = new Uint8Array(binary.length);
                for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
                const text = new TextDecoder('utf-8').decode(bytes);
                navigator.clipboard.writeText(text).then(function() {{
                    btn.textContent = 'Copied!';
                    btn.style.background = '#2ea043';
                    btn.style.color = 'white';
                    setTimeout(function() {{
                    btn.textContent = 'Copy to clipboard';
                    btn.style.background = '';
                    btn.style.color = '';
                    }}, 1500);
                }});
            }})(this);
        " style="
            padding: 6px 14px;
            cursor: pointer;
            border-radius: 6px;
            border: 1px solid #ccc;
            background: #f0f2f6;
            font-size: 14px;
            font-family: inherit;
        ">Copy to clipboard</button>
    </div>
    """
    components.html(html, height=40)


# --- Authentication ---
def _to_dict(obj):
    """Convert st.secrets-like object to plain dict (for nested structures)."""
    if hasattr(obj, "keys"):
        return {k: _to_dict(obj[k]) for k in obj.keys()}
    return obj

def _load_auth_config():
    """Load auth config from config.yaml (local) or Streamlit secrets (Cloud deployment)."""
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    # Streamlit Cloud: use Secrets (add via app Settings → Secrets)
    try:
        creds = st.secrets.get("credentials", {}) if hasattr(st.secrets, "get") else getattr(st.secrets, "credentials", None)
        cookie = st.secrets.get("cookie", {}) if hasattr(st.secrets, "get") else getattr(st.secrets, "cookie", None)
        if creds and cookie:
            return {"credentials": _to_dict(creds), "cookie": _to_dict(cookie)}
    except Exception as e:
        st.warning(f"Secrets load failed: {e}")
    return None

config = _load_auth_config()
if not config:
    st.error(
        "Authentication config not found.\n\n"
        "**Local:** Create `config.yaml` in the project folder (see USER_DOCUMENTATION.md).\n\n"
        "**Streamlit Cloud:** Add to Secrets (use explicit nested format):\n\n"
        "[credentials]\n[credentials.usernames]\n[credentials.usernames.admin]\n"
        "email = \"admin@example.com\"\nname = \"Admin\"\npassword = \"$2b$12$YourHash\"\n\n"
        "[cookie]\nexpiry_days = 7\nkey = \"any_random_string\"\nname = \"email_template_cookie\"\n\n"
        "**Fallback:** Remove config.yaml from .gitignore and commit it (hash is one-way safe)."
    )
    st.stop()

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

# login() returns None when location="main" (renders form); use session_state for auth status
authenticator.login(location="main")
name = st.session_state.get("name")
authentication_status = st.session_state.get("authentication_status")
username = st.session_state.get("username")

if not authentication_status:
    st.stop()

# --- Main app (authenticated) ---
st.title("✉️ Email Template Generator")

# Sidebar: options (shared)
with st.sidebar:
    authenticator.logout("Logout", "sidebar")
    st.divider()
    st.header("Options")
    show_header_logo = st.toggle("Show header logo", value=True)
    show_footer = st.toggle("Show footer", value=True)
    show_terms = st.toggle("Show terms", value=True)
    app_download_colour_preset = st.selectbox(
        "App download banner colour",
        options=["LIGHT", "DARK"],
        index=0,
        help="LIGHT = cream (#fcf7f5), DARK = purple (#7130c9)",
    )
    design_tokens_brand = st.selectbox(
        "Colour scheme / brand",
        options=list(DESIGN_TOKENS_BRANDS),
        format_func=lambda x: {"vio": "Vio (purple)", "holiday_pirates": "Holiday Pirates (plum)", "kiwi": "KIWI (teal)"}[x],
        index=0,
        help="Toggle design tokens (colours, spacing) for different brands.",
    )
    st.divider()
    st.subheader("Target languages")
    locale_preset = st.selectbox(
        "Locale scope",
        options=["en_only", "top_5", "global", "custom"],
        format_func=lambda x: {
            "en_only": "1. English only",
            "top_5": "2. Top 5 (EN + ES, FR, JA, AR, PT)",
            "global": "3. Global (all languages)",
            "custom": "4. Custom selection",
        }[x],
        index=1,
        help="Which languages to include in the output. Affects both the CSV template and generated Liquid.",
    )
    custom_locales: list[str] = []
    if locale_preset == "custom":
        custom_locales = st.multiselect(
            "Select languages",
            options=LOCALE_COLUMNS,
            default=["en", "es", "fr", "de", "nl"],
            help="Choose which languages to include in your template.",
        )
    include_locales = resolve_include_locales(
        locale_preset,
        custom_locales if locale_preset == "custom" else None,
    )
    st.divider()
    st.caption("See **Documentation** tab for user guide and technical docs.")

# Convert to the format expected by generate_template
show_header_logo_str = "TRUE" if show_header_logo else "FALSE"
show_footer_str = "TRUE" if show_footer else "FALSE"
show_terms_str = "TRUE" if show_terms else "FALSE"

tab_generate, tab_template, tab_docs = st.tabs(["Generate from CSV", "Standard input template", "📚 Documentation"])

with tab_generate:
    st.markdown(
        "Upload a translations CSV (Key, Module, module_index, en, ...) to generate "
        "a multi-locale Customer.io email template."
    )
    uploaded_file = st.file_uploader(
        "Upload translations CSV or TSV",
        type=["csv", "tsv"],
        help="Drag and drop or click to browse. Supports legacy (Key, en, ar...) and module format (Key, Module, module_index, en...).",
    )
    include_hotel_reco_gen = st.checkbox(
        "Include hotel recommendations module",
        value=False,
        key="gen_include_hotel_reco",
        help="Adds hotel_reco_grid_4 (4 cards). Uses API data: rec_hotels + reco_city at send time.",
    )

    if uploaded_file is not None:
        # Save uploaded file to a temp path (generate_template expects a file path)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=Path(uploaded_file.name).suffix or ".csv",
            delete=False,
        ) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        try:
            with st.spinner("Generating template..."):
                result = generate_template(
                    tmp_path,
                    show_header_logo=show_header_logo_str,
                    show_footer=show_footer_str,
                    show_terms=show_terms_str,
                    app_download_colour_preset=app_download_colour_preset,
                    design_tokens_brand=design_tokens_brand,
                    include_locales=include_locales,
                    include_hotel_reco=include_hotel_reco_gen,
                )

            st.success("Template generated successfully!")

            # Load translations/structure (for snippets and preview)
            translations, structure = load_translations(Path(tmp_path), include_locales=include_locales)

            # Customer.io subject & preheader snippets
            snippets = build_customerio_subject_preheader_snippets(
                translations, include_locales=include_locales
            )
            if snippets:
                with st.expander("📋 Customer.io subject line & preheader", expanded=True):
                    st.caption("Paste these Liquid snippets into Customer.io's subject line and preheader fields. They use the same locale logic as the email body.")
                    if "subject_line" in snippets:
                        st.markdown("**Subject line** — paste into Customer.io subject field:")
                        st.code(snippets["subject_line"], language="liquid")
                        _render_copy_button(snippets["subject_line"], "subject_line")
                    if "preheader" in snippets:
                        st.markdown("**Preheader** — paste into Customer.io preheader field:")
                        st.code(snippets["preheader"], language="liquid")
                        _render_copy_button(snippets["preheader"], "preheader")

            # Download + Copy
            col_dl, col_copy, _ = st.columns([1, 1, 2])
            with col_dl:
                st.download_button(
                    label="📥 Download full_email_template.liquid",
                    data=result,
                    file_name="full_email_template.liquid",
                    mime="text/plain",
                )
            with col_copy:
                _render_copy_button(result, "liquid_full")

            # Preview options: HTML preview + code
            col_preview, col_code = st.tabs(["📧 HTML preview", "📝 Liquid source"])
            with col_preview:
                preview_html = liquid_to_preview_html(
                    result,
                    translations,
                    structure,
                    show_header_logo=show_header_logo,
                    show_footer=show_footer,
                    show_terms=show_terms,
                    design_tokens_brand=design_tokens_brand,
                )
                st.caption("Preview (English locale) — layout may differ slightly in email clients.")
                components.html(preview_html, height=800, scrolling=True)
            with col_code:
                st.code(result, language="liquid")

        except FileNotFoundError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"An error occurred: {e}")
            raise
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)
    else:
        st.info("👆 Upload a translations CSV to get started.")

    # Optional: use sample file if it exists
    sample_path = Path(__file__).parent / "email_translations.csv"
    if sample_path.exists() and uploaded_file is None:
        if st.button("Try with sample file (email_translations.csv)"):
            try:
                with st.spinner("Generating template from sample..."):
                    result = generate_template(
                        sample_path,
                        show_header_logo=show_header_logo_str,
                        show_footer=show_footer_str,
                        show_terms=show_terms_str,
                        app_download_colour_preset=app_download_colour_preset,
                        design_tokens_brand=design_tokens_brand,
                        include_locales=include_locales,
                        include_hotel_reco=include_hotel_reco_gen,
                    )
                st.success("Template generated!")
                col_dl_s, col_copy_s, _ = st.columns([1, 1, 2])
                with col_dl_s:
                    st.download_button(
                        label="📥 Download full_email_template.liquid",
                        data=result,
                        file_name="full_email_template.liquid",
                        mime="text/plain",
                        key="download_sample",
                    )
                with col_copy_s:
                    _render_copy_button(result, "liquid_sample")
            except Exception as e:
                st.error(f"Error: {e}")

with tab_template:
    st.markdown(
        "**Create an input template** for your selected modules. Download a blank CSV (or open it in Google Sheets), "
        "fill in your translations, then upload it in the **Generate from CSV** tab to produce your Liquid email template."
    )
    st.subheader("1. Select modules")
    hero_type = st.radio(
        "Hero module",
        options=["hero_module", "hero_module_two_column"],
        format_func=lambda x: "Simple (headline + body + CTA)" if x == "hero_module" else "Two-column (4 feature blocks + CTA)",
        horizontal=True,
    )
    include_app_download = st.checkbox("Include app download module", value=True)
    with st.expander("USP modules (How Vio helps you book like an insider)", expanded=True):
        st.caption("Choose one or more. All use the same copy; differ by layout.")
        include_icon_left = st.checkbox("Icon left, text right", value=False, key="usp_icons", help="Small icon on left, heading + copy on right")
        include_text_left = st.checkbox("Text left, image right", value=False, key="usp_feature", help="All three rows: text left, image right")
        include_alternating = st.checkbox("Alternating text and image", value=True, key="usp_ui", help="Row 1: text left. Row 2: image left. Row 3: text left.")
    include_disclaimer = st.checkbox("Include disclaimer/terms module", value=False)
    include_hotel_reco = st.checkbox(
        "Include hotel recommendations module",
        value=False,
        help="Adds hotel_reco_grid_4 (4 cards). Uses API data: rec_hotels + reco_city at send time.",
    )
    modules = [hero_type]
    if include_app_download:
        modules.append("app_download_module")
    if include_icon_left:
        modules.append("icon_left_text_right_module")
    if include_text_left:
        modules.append("text_left_image_right_module")
    if include_alternating:
        modules.append("alternating_text_image_module")
    if include_disclaimer:
        modules.append("disclaimer_module")

    st.subheader("2. Preview")
    st.caption("This is how your selected modules will look with placeholder content.")
    preview_html = get_module_preview_html(
        modules,
        app_download_colour_preset=app_download_colour_preset,
        design_tokens_brand=design_tokens_brand,
        include_hotel_reco=include_hotel_reco,
    )
    components.html(preview_html, height=500, scrolling=True)

    st.subheader("3. Download your input template")
    csv_content, links_dict = generate_standard_input_template(
        modules, include_locales=include_locales, include_hotel_reco=include_hotel_reco
    )
    st.caption(f"Open in Excel, Google Sheets (File → Import → Upload), or any spreadsheet tool. Fill in the locale columns ({', '.join(include_locales)}) with your copy, add image URLs and links where needed.")
    if include_hotel_reco:
        with st.expander("Hotel recommendations module — CSV variables", expanded=False):
            st.markdown("""
**hotel_reco_headline** — Headline text. Use `{city}` as placeholder for the city (e.g. *"Recently viewed hotels in {city}"*).

**hotel_reco_type** — Recommender type (for API). Use one of:
- `last_browsed` — Last browsed hotels
- `similar_to_last_viewed` — Similar to last viewed hotels  
- `top_in_destination` — Top hotels in last browsed destination
            """)
    st.download_button(
        label="📥 Download input template (CSV)",
        data=csv_content,
        file_name="email_translations_template.csv",
        mime="text/csv",
        key="dl_csv_template",
    )

    with st.expander("Optional: Standard links config"):
        st.caption("Customize URLs (terms, privacy, social icons, app download) before generating. Save as standard_links.json in your project folder.")
        links = dict(load_standard_links())
        for key in DEFAULT_LINKS:
            links[key] = st.text_input(
                key.replace("_", " ").title(),
                value=links.get(key, DEFAULT_LINKS[key]),
                key=f"link_{key}",
            )
        final_links = {k: links.get(k, v) for k, v in links_dict.items()}
        st.download_button(
            label="📥 Download standard_links.json",
            data=json.dumps(final_links, indent=2),
            file_name="standard_links.json",
            mime="application/json",
            key="dl_links",
        )

with tab_docs:
    st.subheader("Documentation")
    doc_user = Path(__file__).parent / "USER_DOCUMENTATION.md"
    doc_tech = Path(__file__).parent / "TECHNICAL_DOCUMENTATION.md"

    doc_tab_user, doc_tab_tech = st.tabs(["User Guide", "Technical Docs"])
    with doc_tab_user:
        if doc_user.exists():
            st.markdown(doc_user.read_text(encoding="utf-8"))
        else:
            st.warning(f"User documentation not found: {doc_user}")
    with doc_tab_tech:
        if doc_tech.exists():
            st.markdown(doc_tech.read_text(encoding="utf-8"))
        else:
            st.warning(f"Technical documentation not found: {doc_tech}")
