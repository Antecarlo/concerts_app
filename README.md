# My Concert Diary

Import concerts from PDF files, review, save locally, and sync to Google Calendar.

## Quick start

1. **Download** the latest `MyConcertDiary.exe` from the **Releases** tab.
2. **Double-click** the `.exe` to launch.
3. Drag & drop a PDF file (or click to browse).
4. Edit the extracted date/venue/notes if needed.
5. Click **"Save Imported"**.
6. Click **"Sync to Google Calendar"** and authenticate via browser (first time only).

> Your data is stored at `~/.concert_diary_app/concerts.db`. The OAuth token is cached at `~/.concert_diary_app/token.json`.

## For developers

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up your own Google OAuth credentials
cp .env.template .env
# Edit .env with your Client ID and Secret (see below)

# Run
python main.py
```

### Get Google OAuth credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials**
2. Create **OAuth client ID** → **Desktop app**
3. Add redirect URI: `http://localhost`
4. Copy your Client ID and Secret into `.env`

### Build executable locally

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name "MyConcertDiary" main.py
```

### Build with your own credentials bundled

```bash
cp .env.template .env
# Fill in your credentials
pyinstaller --noconsole --onefile --add-data ".env;." --name "MyConcertDiary" main.py
```

### Run tests

```bash
python -m pytest tests/ -v
```

## Building on GitHub

The release workflow reads `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from GitHub Secrets
and injects them into the `.exe` at build time. No secrets are stored in the source code.