# Deployment Guide: Host Your Email Template Generator

This guide walks you through putting your project on GitHub and hosting it on **Streamlit Community Cloud** (free). No prior Git experience required.

---

## Part 1: Install Git (if needed)

1. **Check if Git is installed** – Open Terminal and run:
   ```bash
   git --version
   ```
   If you see a version number (e.g. `git version 2.39.0`), you're good. Otherwise:

2. **Install Git** – Download from [git-scm.com](https://git-scm.com/downloads) or install via Homebrew:
   ```bash
   brew install git
   ```

---

## Part 2: Configure Git (first time only)

If you've never used Git before, set your name and email (used for commits):

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

Use the same email as your GitHub account if you like.

---

## Part 3: Create a GitHub Repository

1. **Sign in** to [github.com](https://github.com).

2. **Create a new repository:**
   - Click the **+** in the top-right → **New repository**
   - **Repository name:** e.g. `email-template-generator` (lowercase, hyphens allowed)
   - **Description:** optional, e.g. "Customer.io email template generator"
   - **Public** (required for free Streamlit hosting)
   - Do **not** tick "Add a README" or "Add .gitignore" – we already have files
   - Click **Create repository**

3. **Copy the repo URL** – After creation, you'll see a URL like:
   ```
   https://github.com/YOUR_USERNAME/email-template-generator.git
   ```
   Or SSH: `git@github.com:YOUR_USERNAME/email-template-generator.git`

---

## Part 4: Push Your Code to GitHub

Run these commands in Terminal, in your project folder:

```bash
cd /Users/wouter/Documents/Project_Email_Template

# 1. Initialize Git
git init

# 2. Add all files (respects .gitignore)
git add .

# 3. Create the first commit
git commit -m "Initial commit: email template generator with Streamlit"

# 4. Name the default branch (GitHub expects 'main')
git branch -M main

# 5. Connect to your GitHub repo (replace with YOUR username and repo name)
git remote add origin https://github.com/YOUR_USERNAME/email-template-generator.git

# 6. Push to GitHub
git push -u origin main
```

**First push:** Git will ask you to sign in. Use one of these:

- **HTTPS:** GitHub will prompt for username and a **Personal Access Token** (not your password). See [Creating a token](https://github.com/settings/tokens) → "Generate new token (classic)" → give it `repo` scope.
- **GitHub CLI:** Run `brew install gh` then `gh auth login` – often easier.

---

## Part 5: Deploy on Streamlit Community Cloud

1. **Go to** [share.streamlit.io](https://share.streamlit.io).

2. **Sign in with GitHub** – Authorize Streamlit to access your account.

3. **Deploy a new app:**
   - Click **New app** (or "Deploy an app")
   - **Repository:** select `YOUR_USERNAME/email-template-generator`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - (Optional) **App URL:** e.g. `email-template-generator` → your app will be at `https://email-template-generator.streamlit.app`

4. **Click Deploy** – Streamlit will build and run your app. This usually takes 1–3 minutes.

5. **Your app is live** – You'll get a URL like `https://your-app-name.streamlit.app`.

---

## Making Updates Later

When you change code and want to update the hosted app:

```bash
cd /Users/wouter/Documents/Project_Email_Template

git add .
git commit -m "Describe your changes"
git push
```

Streamlit Community Cloud will automatically redeploy your app when you push to the `main` branch.

---

## Troubleshooting

| Problem | What to try |
|--------|-------------|
| `git push` asks for password | Use a [Personal Access Token](https://github.com/settings/tokens) instead of your GitHub password. |
| Streamlit build fails | Check the build log on share.streamlit.io. Ensure `requirements.txt` lists `streamlit` and any other packages your app needs. |
| App crashes on startup | Make sure `design_tokens.liquid` (and any other files your script reads) are in the repo and in the same directory as `app.py`. |
| "Repository not found" | Confirm the repo name and that it's **public**. Double-check `git remote -v` shows the correct URL. |

---

## What Gets Pushed

Your `.gitignore` excludes:

- `__pycache__/`
- Virtual environments (`venv/`, `.venv/`)
- `.DS_Store`
- IDE config

All Python files, Liquid templates, markdown docs, and sample CSVs will be in the repo. If you have **private** data (e.g. API keys, real customer CSVs), do **not** add them – use [Streamlit secrets](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management) for sensitive values instead.
