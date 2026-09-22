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
pip install -r requirements.txt
python main.py
```

### Build executable

```bash
pyinstaller --noconsole --onefile --name "MyConcertDiary" main.py
```

### Google OAuth setup (for your own Client ID)

The app ships with embedded OAuth credentials. If you want to use your own:

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials**
2. Create **OAuth client ID** → **Desktop app**
3. Replace the `_CLIENT_CONFIG` dict in `app/calendar_sync.py` with your values.