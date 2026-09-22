# My Concert Diary

A desktop application to import concert schedules from PDF files, review and edit them, and sync to Google Calendar with precise times and custom colors.

Built for municipal music bands and concert organizers who need to quickly extract event details from schedule PDFs and push them directly to their calendar.

---

## Features

- **PDF Import** — Drag & drop (or browse) PDF files to automatically extract concerts
- **Smart PDF Parsing** — Recognizes Spanish municipal band schedules with dates, venues, and times
- **Review & Edit** — Review imported concerts in an editable table before saving
- **Time Support** — Extracts and syncs exact start/end times (not just all-day events)
- **Color Selection** — Choose Google Calendar event colors (Peacock, Tomato, Lavender, etc.)
- **Bulk & Single Sync** — Sync all concerts at once or one by one
- **Re-sync Support** — Update already-synced events in Google Calendar if details change
- **Local Database** — Concerts stored locally in SQLite; data persists between sessions
- **Modern UI** — Built with CustomTkinter for a clean, native-looking interface

---

## Technologies

| Layer | Technology |
|-------|-----------|
| **UI** | Python `customtkinter` — modern themed Tkinter widgets |
| **Database** | `sqlite3` (built-in) — local persistence with automatic migrations |
| **PDF Parsing** | `pdfplumber` — text extraction with regex pattern matching |
| **Calendar API** | Google Calendar API v3 via `google-api-python-client`, `google-auth-oauthlib` |
| **Date/Time** | Python `datetime`, `zoneinfo` for timezone-aware RFC 3339 timestamps |
| **Testing** | `pytest` + `reportlab` (test PDF fixtures) |
| **Packaging** | `PyInstaller` — single `.exe` distribution |

---

## Project Structure

```
concerts_app/
├── main.py                    # Application entry point
├── app/
│   ├── __init__.py
│   ├── gui.py                 # CustomTkinter UI (tables, dialogs, sync flow)
│   ├── database.py            # SQLite database layer (CRUD + migrations)
│   ├── pdf_parser.py          # PDF text extraction and concert parsing
│   └── calendar_sync.py       # Google OAuth + Calendar API (create/update)
├── tests/
│   ├── test_database.py         # SQLite CRUD tests
│   └── test_pdf_parser.py     # PDF parsing tests with generated fixtures
├── .env.template              # Template for Google OAuth credentials
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## Quick Start (End User)

1. **Download** the latest `MyConcertDiary.exe` from the **Releases** tab.
2. **Double-click** the `.exe` to launch.
3. **Import a PDF** — Drag & drop a PDF file (or click to browse).
4. **Review** — Edit dates, times, venue, or notes if needed.
5. **Save** — Click **"Save Imported"** to store locally.
6. **Sync** — Click **"☁ Sync to Google Calendar"** below the Saved Concerts table:
   - Select which concerts to sync
   - Pick an event color
   - Authenticate via browser (first time only)
   - Your OAuth token is cached so you won't need to re-authenticate

> **Your data** is stored at `~/.concert_diary_app/concerts.db`.  
> **Your OAuth token** is cached at `~/.concert_diary_app/token.json`.

---

## Developer Setup

### Prerequisites

- Python 3.9+
- A Google Cloud project with the **Google Calendar API enabled**

### Install

```bash
# Clone and enter the project
cd concerts_app

# Install dependencies
pip install -r requirements.txt

# Set up your Google OAuth credentials
cp .env.template .env
# Edit .env with your Client ID and Secret (see below)

# Run
python main.py
```

### Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID** → **Desktop app**
3. Add redirect URI: `http://localhost`
4. Go to **APIs & Services** → **Library** → search for **Google Calendar API** → click **Enable**
5. Copy your **Client ID** and **Client Secret** into `.env`:

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

### Run Tests

```bash
python -m pytest tests/ -v
```

### Build Executable

```bash
pip install pyinstaller

# Basic build
pyinstaller --noconsole --onefile --name "MyConcertDiary" main.py

# With credentials bundled (for distribution)
cp .env.template .env
# Fill in your credentials
pyinstaller --noconsole --onefile --add-data ".env;." --name "MyConcertDiary" main.py
```

### Build on GitHub Actions

The repository includes a release workflow that reads `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from GitHub Secrets and injects them into the `.exe` at build time. No secrets are stored in the source code.

---

## How Syncing Works

| Scenario | Behavior |
|----------|----------|
| **First sync** | Creates a new Google Calendar event, stores the event ID locally |
| **Re-sync (update)** | Uses the stored event ID to update the existing calendar event |
| **Re-sync after deletion** | If the event was deleted in Google Calendar (404), creates a new one automatically |
| **Color change** | Overwrites the event's `colorId` on the next sync |

---

## Data Model

Each concert stored locally contains:

| Field | Description |
|-------|-------------|
| `id` | Auto-incrementing primary key |
| `date` | Event date (`YYYY-MM-DD`) |
| `start_time` | Start time (`HH:MM`) — optional |
| `end_time` | End time (`HH:MM`) — optional |
| `location` | Venue or place |
| `notes` | Event description |
| `calendar_event_id` | Google Calendar event ID (null if not synced) |
| `source_file` | Original PDF file path |
| `calendar_color` | Preferred Google Calendar color ID |
| `created_at` | Timestamp of local creation |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| *"Google Calendar API is disabled"* | Go to [Google Cloud Console](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com) and enable the Calendar API. Wait 1–2 minutes. |
| *"Missing GOOGLE_CLIENT_ID"* | Create `.env` from `.env.template` and fill in your OAuth credentials. |
| Synced events appear as "All day" | Make sure the concert has both `start_time` and `end_time` set. If either is empty, the event becomes an all-day event. |
| Want to re-authenticate with a different Google account | Delete `~/.concert_diary_app/token.json` and sync again. |

---

## License

MIT
