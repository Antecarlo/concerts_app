from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from datetime import datetime, timedelta, timezone
import time

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
DEFAULT_TIMEZONE = "Europe/Madrid"

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

    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path(__file__).parent / ".env",
        Path.home() / ".concert_diary_app" / ".env",
    ]

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

    if not client_id:
        import os
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_secret:
        import os
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

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

            creds = flow.run_local_server(port=8080, open_browser=True)

        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())

    return creds


def _make_datetime_iso(date_str: str, time_str: str) -> str:
    """Combine YYYY-MM-DD and HH:MM into an RFC3339 datetime string."""
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(DEFAULT_TIMEZONE)
        dt = dt.replace(tzinfo=tz)
    except Exception:
        offset_sec = time.localtime().tm_gmtoff
        tz = timezone(timedelta(seconds=offset_sec))
        dt = dt.replace(tzinfo=tz)
    return dt.isoformat()


def _handle_http_error(err: HttpError):
    """Extract a user-friendly message from a Google API HttpError."""
    try:
        body = json.loads(err.content.decode()) if err.content else {}
        details = body.get("error", {})
        message = details.get("message", str(err))
    except Exception:
        message = str(err)

    if "has not been used in project" in message and "or it is disabled" in message:
        raise RuntimeError(
            "Google Calendar API is disabled.\n\n"
            "Enable it at:\n"
            "https://console.cloud.google.com/apis/library/calendar-json.googleapis.com\n\n"
            "Wait 1-2 minutes, then retry."
        )

    if len(message) > 400:
        message = message[:400] + "..."

    raise RuntimeError(f"Google Calendar API error: {message}")


def create_calendar_event(date: str, location: str, notes: str,
                          start_time: str = "", end_time: str = "",
                          color_id: str = "") -> str:
    """
    Creates an event on the user's primary Google Calendar.
    Returns the event ID.
    """
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    if start_time and end_time:
        start_body = {"dateTime": _make_datetime_iso(date, start_time)}
        end_body = {"dateTime": _make_datetime_iso(date, end_time)}
    else:
        start_body = {"date": date}
        end_body = {"date": date}

    event = {
        "summary": f"Concert at {location}" if location else "Concert",
        "location": location,
        "description": notes,
        "start": start_body,
        "end": end_body,
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 24 * 60},
                {"method": "popup", "minutes": 60},
            ],
        },
    }
    if color_id:
        event["colorId"] = color_id

    try:
        created_event = service.events().insert(calendarId="primary", body=event).execute()
    except HttpError as e:
        _handle_http_error(e)
    return created_event["id"]


def update_calendar_event(event_id: str, date: str, location: str, notes: str,
                          start_time: str = "", end_time: str = "",
                          color_id: str = ""):
    """Updates an existing Google Calendar event."""
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    if start_time and end_time:
        start_body = {"dateTime": _make_datetime_iso(date, start_time)}
        end_body = {"dateTime": _make_datetime_iso(date, end_time)}
    else:
        start_body = {"date": date}
        end_body = {"date": date}

    event = {
        "summary": f"Concert at {location}" if location else "Concert",
        "location": location,
        "description": notes,
        "start": start_body,
        "end": end_body,
    }
    if color_id:
        event["colorId"] = color_id

    try:
        service.events().update(calendarId="primary", eventId=event_id, body=event).execute()
    except HttpError as e:
        _handle_http_error(e)


def upsert_calendar_event(event_id: str, date: str, location: str, notes: str,
                          start_time: str = "", end_time: str = "",
                          color_id: str = "") -> str:
    """
    Update an existing Google Calendar event, or create a new one
    if it has been deleted from Google Calendar.
    Returns the (possibly new) event ID.
    """
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    if start_time and end_time:
        start_body = {"dateTime": _make_datetime_iso(date, start_time)}
        end_body = {"dateTime": _make_datetime_iso(date, end_time)}
    else:
        start_body = {"date": date}
        end_body = {"date": date}

    event = {
        "summary": f"Concert at {location}" if location else "Concert",
        "location": location,
        "description": notes,
        "start": start_body,
        "end": end_body,
    }
    if color_id:
        event["colorId"] = color_id

    if event_id:
        try:
            result = service.events().update(
                calendarId="primary", eventId=event_id, body=event
            ).execute()
            return result["id"]
        except HttpError as e:
            if e.resp.status == 404:
                pass  # fall through to create a new event
            else:
                _handle_http_error(e)

    # Create new event (includes reminders)
    event["reminders"] = {
        "useDefault": False,
        "overrides": [
            {"method": "popup", "minutes": 24 * 60},
            {"method": "popup", "minutes": 60},
        ],
    }

    try:
        result = service.events().insert(calendarId="primary", body=event).execute()
    except HttpError as e:
        _handle_http_error(e)
    return result["id"]


def delete_calendar_event(event_id: str):
    """Deletes a Google Calendar event."""
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
    except HttpError as e:
        _handle_http_error(e)
