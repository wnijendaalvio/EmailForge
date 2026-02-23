"""
Streamlit app for the Email Template Generator.
Upload a translations CSV, configure options, and download the generated Liquid template.
"""
import json
import tempfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# Import from the local module (same directory)
from csv_translations_to_email import (
    generate_template,
    generate_standard_input_template,
    get_module_preview_html,
    liquid_to_preview_html,
    load_translations,
    load_standard_links,
    DEFAULT_LINKS,
    LOCALE_COLUMNS,
    resolve_include_locales,
)

st.set_page_config(
    page_title="Email Template Generator",
    page_icon="✉️",
    layout="centered",
)

st.title("✉️ Email Template Generator")

# Sidebar: options (shared)
with st.sidebar:
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

# Convert to the format expected by generate_template
show_header_logo_str = "TRUE" if show_header_logo else "FALSE"
show_footer_str = "TRUE" if show_footer else "FALSE"
show_terms_str = "TRUE" if show_terms else "FALSE"

tab_generate, tab_template = st.tabs(["Generate from CSV", "Standard input template"])

with tab_generate:
    st.markdown(
        "Upload a translations CSV (Key, Module, module_index, en, ...) to generate "
        "a multi-locale Customer.io email template. See [SHEET_STRUCTURE_TRANSLATIONS.md](SHEET_STRUCTURE_TRANSLATIONS.md) for the expected format."
    )
    uploaded_file = st.file_uploader(
        "Upload translations CSV or TSV",
        type=["csv", "tsv"],
        help="Drag and drop or click to browse. Supports legacy (Key, en, ar...) and module format (Key, Module, module_index, en...).",
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
                    include_locales=include_locales,
                )

            st.success("Template generated successfully!")

            # Download button
            st.download_button(
                label="📥 Download full_email_template.liquid",
                data=result,
                file_name="full_email_template.liquid",
                mime="text/plain",
            )

            # Load translations/structure for preview
            translations, structure = load_translations(Path(tmp_path))

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
                        include_locales=include_locales,
                    )
                st.success("Template generated!")
                st.download_button(
                    label="📥 Download full_email_template.liquid",
                    data=result,
                    file_name="full_email_template.liquid",
                    mime="text/plain",
                    key="download_sample",
                )
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
    include_usp = st.checkbox("Include USP module", value=False, help="Unique selling propositions: title + 3 feature rows with icons")
    include_usp_feature = st.checkbox("Include USP feature module", value=False, help="Same content with text left, illustrative images right (two-column layout)")
    include_disclaimer = st.checkbox("Include disclaimer/terms module", value=False)
    modules = [hero_type]
    if include_app_download:
        modules.append("app_download_module")
    if include_usp:
        modules.append("usp_module")
    if include_usp_feature:
        modules.append("usp_feature_module")
    if include_disclaimer:
        modules.append("disclaimer_module")

    st.subheader("2. Preview")
    st.caption("This is how your selected modules will look with placeholder content.")
    preview_html = get_module_preview_html(modules, app_download_colour_preset=app_download_colour_preset)
    components.html(preview_html, height=500, scrolling=True)

    st.subheader("3. Download your input template")
    csv_content, links_dict = generate_standard_input_template(modules, include_locales=include_locales)
    st.caption(f"Open in Excel, Google Sheets (File → Import → Upload), or any spreadsheet tool. Fill in the locale columns ({', '.join(include_locales)}) with your copy, add image URLs and links where needed.")
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
