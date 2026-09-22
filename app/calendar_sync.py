from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the token file.
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# Token stored in user's home directory
TOKEN_DIR = Path.home() / ".concert_diary_app"
TOKEN_PATH = TOKEN_DIR / "token.json"


def _load_client_config() -> dict:
    """
    Loads OAuth client credentials from, in order of priority:
    1. .env file in the app directory or executable directory
    2. Environment variables: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
    3. Compiled-in defaults (used only if nothing else is set)

    This allows each user/developer to use their own Google Cloud project
    without modifying the source code.
    """
    client_id = None
    client_secret = None

    # 1. Try to load from .env file
    env_paths = [
        Path(__file__).parent.parent / ".env",         # project root (development)
        Path(__file__).parent / ".env",                # app directory
        Path.home() / ".concert_diary_app" / ".env",   # user config directory
    ]
    # Also check if running frozen (PyInstaller)
    import sys
    if getattr(sys, "frozen", False):
        env_paths.insert(0, Path(sys.executable).parent / ".env")

    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("\"'")
                        if key == "GOOGLE_CLIENT_ID":
                            client_id = val
                        elif key == "GOOGLE_CLIENT_SECRET":
                            client_secret = val

    # 2. Fallback to environment variables
    if not client_id:
        import os
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_secret:
        import os
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    # 3. If no credentials found at all, raise a clear error
    #    (GitHub builds inject .env via secrets, local devs copy .env.template)
    if not client_id:
        raise RuntimeError(
            "Missing GOOGLE_CLIENT_ID. "
            "Copy .env.template to .env and set your Google OAuth credentials."
        )
    if not client_secret:
        raise RuntimeError(
            "Missing GOOGLE_CLIENT_SECRET. "
            "Copy .env.template to .env and set your Google OAuth credentials."
        )

    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["http://localhost"],
        }
    }


def get_credentials() -> Credentials:
    """Gets valid user credentials, running OAuth flow if needed."""
    TOKEN_DIR.mkdir(exist_ok=True)

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            config = _load_client_config()
            flow = InstalledAppFlow.from_client_config(config, SCOPES)
            # Opens browser on localhost:8080
            creds = flow.run_local_server(port=8080, open_browser=True)

        # Save token for next run so the user doesn't re-authenticate
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())

    return creds


def create_calendar_event(date: str, location: str, notes: str) -> str:
    """
    Creates an event on the user's primary Google Calendar.
    Returns the event ID.
    """
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    # All-day event
    event = {
        "summary": f"Concert at {location}" if location else "Concert",
        "location": location,
        "description": notes,
        "start": {"date": date},
        "end": {"date": date},
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 24 * 60},  # 1 day before
                {"method": "popup", "minutes": 60},       # 1 hour before
            ],
        },
    }

    created_event = service.events().insert(calendarId="primary", body=event).execute()
    return created_event["id"]


def update_calendar_event(event_id: str, date: str, location: str, notes: str):
    """Updates an existing Google Calendar event."""
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    event = {
        "summary": f"Concert at {location}" if location else "Concert",
        "location": location,
        "description": notes,
        "start": {"date": date},
        "end": {"date": date},
    }

    service.events().update(calendarId="primary", eventId=event_id, body=event).execute()


def delete_calendar_event(event_id: str):
    """Deletes a Google Calendar event."""
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    service.events().delete(calendarId="primary", eventId=event_id).execute()