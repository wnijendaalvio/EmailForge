# Hosting the Email Template Generator in Streamlit

This guide walks you through running the email template generator as a Streamlit web app.

## Prerequisites

- Python 3.10 or later
- pip (Python package manager)

## Setup

### 1. Install dependencies

```bash
cd /Users/wouter/Documents/Project_Email_Template
pip install -r requirements.txt
```

Or install Streamlit directly:

```bash
pip install streamlit
```

### 2. Run the app

```bash
streamlit run app.py
```

The app will start and open in your browser at `http://localhost:8501`. If it doesn’t open automatically, visit that URL.

## Using the app

1. **Upload a CSV** – Drag and drop or click to upload a translations CSV or TSV.
2. **Set options** (sidebar):
   - **Show header logo** – Toggle the Vio logo at the top.
   - **Show footer** – Toggle the footer section.
   - **Show terms** – Toggle the terms & privacy block.
   - **App download banner colour** – LIGHT or DARK.
3. **Generate** – The template is generated as soon as you upload a file.
4. **Download** – Click **Download full_email_template.liquid** to save the file.
5. **Preview** – Use the **📧 HTML preview** tab to see a rendered preview (English locale), or the **📝 Liquid source** tab to view the raw template.

## CSV format

Use the structure from [SHEET_STRUCTURE_TRANSLATIONS.md](SHEET_STRUCTURE_TRANSLATIONS.md). The app supports:

- **Legacy:** Key, en, ar, zh-cn, …
- **Module-based:** Key, Module, module_index, en, ar, …

## Deployment options

### Local only (default)

`streamlit run app.py` serves the app on your machine only. Other devices on your network can access it if you use `--server.address 0.0.0.0`:

```bash
streamlit run app.py --server.address 0.0.0.0
```

### Streamlit Community Cloud (free)

1. Push the project to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. Sign in with GitHub and deploy:
   - **Repository:** `your-username/your-repo`
   - **Branch:** main (or your branch)
   - **Main file path:** `app.py`
4. Click **Deploy**.

Ensure `requirements.txt` lists `streamlit` (and any other dependencies).

### Custom server

Run behind a reverse proxy (nginx, Caddy, etc.) or in a Docker container. See [Streamlit’s deployment docs](https://docs.streamlit.io/deploy).

## CLI still works

The original script can still be used from the command line:

```bash
python3 csv_translations_to_email.py email_translations.csv > full_email_template.liquid
```
