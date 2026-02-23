"""
Streamlit app for the Email Template Generator.
Upload a translations CSV, configure options, and download the generated Liquid template.
"""
import tempfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# Import from the local module (same directory)
from csv_translations_to_email import generate_template, liquid_to_preview_html, load_translations

st.set_page_config(
    page_title="Email Template Generator",
    page_icon="✉️",
    layout="centered",
)

st.title("✉️ Email Template Generator")
st.markdown(
    "Upload a translations CSV (Key, Module, module_index, en, ...) to generate "
    "a multi-locale Customer.io email template. See [SHEET_STRUCTURE_TRANSLATIONS.md](SHEET_STRUCTURE_TRANSLATIONS.md) for the expected format."
)

# File upload
uploaded_file = st.file_uploader(
    "Upload translations CSV or TSV",
    type=["csv", "tsv"],
    help="Drag and drop or click to browse. Supports legacy (Key, en, ar...) and module format (Key, Module, module_index, en...).",
)

# Sidebar: options
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

# Convert to the format expected by generate_template
show_header_logo_str = "TRUE" if show_header_logo else "FALSE"
show_footer_str = "TRUE" if show_footer else "FALSE"
show_terms_str = "TRUE" if show_terms else "FALSE"

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
