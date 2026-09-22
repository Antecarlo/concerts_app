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

# ── Embedded OAuth client credentials ────────────────────────────
# This enables seamless Google authentication via browser.
# The user only needs to log in to their Google account once.
_CLIENT_CONFIG = {
    "installed": {
        "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
        "client_secret": "YOUR_CLIENT_SECRET",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "redirect_uris": ["http://localhost"]
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
            # Use embedded client configuration — no file needed
            flow = InstalledAppFlow.from_client_config(
                _CLIENT_CONFIG, SCOPES
            )
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