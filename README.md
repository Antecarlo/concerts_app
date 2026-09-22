# My Concert Diary

Import concerts from PDF files, review, save locally, and sync to Google Calendar.

## How to use the app

1. **Download** the latest `MyConcertDiary.exe` from the **Releases** tab.
2. **Double-click** the `.exe` to launch.
3. Drag & drop a PDF file (or click to browse).
4. Edit the extracted date/venue/notes if needed.
5. Click **"Save Imported"**.
6. Click **"Sync to Google Calendar"** and authenticate via browser (first time only).

> **Note:** Your data is stored at `~/.concert_diary_app/concerts.db`. The OAuth token is cached at `~/.concert_diary_app/token.json`.

## For developers

```bash
# Install dependencies
pip install -r requirements.txt

# (Optional) Use your own Google Cloud credentials
cp .env.template .env
# Edit .env with your Client ID and Secret

# Run
python main.py
```

### Setting up your own Google OAuth credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials**
2. Create **OAuth client ID** → **Desktop app**
3. Add redirect URI: `http://localhost`
4. Copy your Client ID and Secret
5. Copy `.env.template` to `.env` and paste your values

> If no `.env` file is found, the app falls back to compiled-in credentials.

### Build executable locally

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name "MyConcertDiary" main.py
# Output: dist/MyConcertDiary.exe
```

### Running tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```