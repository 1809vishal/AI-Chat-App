# Deploying Your Assistant to the Web (Free, 24/7)

This makes your assistant reachable from any browser, on any device,
even when your laptop is off — because it now runs on free cloud
infrastructure instead of your machine.

## What changed from your local version

| | Local (Ollama) | Cloud (this folder) |
|---|---|---|
| Chat model | Llama 3.2 via Ollama | Llama 3.1 8B via Groq API |
| Embeddings | nomic-embed-text via Ollama | sentence-transformers (runs in-process) |
| Cost | Free | Free |
| Available when laptop is off | ❌ No | ✅ Yes |
| Privacy | Fully private, nothing leaves your machine | Data passes through Groq's API |

## Step 1: Get a free Groq API key
1. Go to https://console.groq.com and sign up (no credit card needed)
2. Go to "API Keys" and create a new key
3. Copy it somewhere safe — you'll need it in Step 3

## Step 2: Put this project on GitHub
Streamlit Community Cloud deploys directly from a GitHub repository.

```bash
cd cloud
git init
git add .
git commit -m "First AI assistant - cloud version"
```

Then create a new repository on https://github.com (public or private,
both work), and push:
```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

**Important:** Do NOT commit your Groq API key to GitHub. It doesn't
appear anywhere in this code — it's added securely in Step 4 instead.

## Step 3: Deploy on Streamlit Community Cloud
1. Go to https://share.streamlit.io and sign in with GitHub (free)
2. Click "New app"
3. Select your repository, branch (`main`), and set the main file to `app.py`
4. Click "Deploy"

## Step 4: Add your Groq API key as a secret
1. On your deployed app's page, click the "⋮" menu → "Settings" → "Secrets"
2. Add this exactly:
   ```toml
   GROQ_API_KEY = "your-groq-key-here"
   ```
3. Save — the app will automatically restart with the key available

## Step 5: Use it from anywhere
Your app now has a public URL like:
```
https://your-app-name.streamlit.app
```
Open this from your phone, another computer, or send it to a
teammate — it works independently of your laptop being on.

## Notes on this setup
- **Free tier limits**: Groq's free tier allows up to 14,400 requests/day
  on this model — more than enough for personal or small-team use.
- **Chat history resets** if the app restarts (e.g. after inactivity,
  Streamlit Cloud free apps "sleep" and wake on the next visit). This
  is the same limitation as your local version, just for a different
  reason.
- **The policy documents are rebuilt fresh** each time the app starts
  (that's what `build_policy_index()` does), since free hosting doesn't
  guarantee your local `policy_db/` folder persists between restarts.
  This is fine for a handful of documents; for a large document set
  later on, you'd want a proper hosted vector database instead.
- **To update your policies later**: edit the `.txt` files in
  `policies/`, commit, and push to GitHub — Streamlit Cloud
  auto-redeploys on every push to `main`.
