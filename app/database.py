import os
import sqlite3

DB_DIR = os.path.join(os.path.expanduser("~"), ".concert_diary_app")
DB_PATH = os.path.join(DB_DIR, "concerts.db")


def init_db():
    """Initializes the database and creates the table if it doesn't exist."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            location TEXT NOT NULL,
            notes TEXT,
            calendar_event_id TEXT,
            source_file TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Migration for existing databases
    cursor.execute("PRAGMA table_info(concerts)")
    columns = [col[1] for col in cursor.fetchall()]
    if "calendar_event_id" not in columns:
        cursor.execute("ALTER TABLE concerts ADD COLUMN calendar_event_id TEXT")
    if "source_file" not in columns:
        cursor.execute("ALTER TABLE concerts ADD COLUMN source_file TEXT")
    conn.commit()
    conn.close()


def add_concert(date: str, location: str, notes: str = "", source_file: str = ""):
    """Adds a new concert to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO concerts (date, location, notes, source_file) VALUES (?, ?, ?, ?)",
        (date, location, notes, source_file)
    )
    conn.commit()
    concert_id = cursor.lastrowid
    conn.close()
    return concert_id


def update_concert(concert_id: int, date: str, location: str, notes: str):
    """Updates an existing concert."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE concerts SET date = ?, location = ?, notes = ? WHERE id = ?",
        (date, location, notes, concert_id)
    )
    conn.commit()
    conn.close()


def set_calendar_event_id(concert_id: int, event_id: str):
    """Stores the Google Calendar event ID for a concert."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE concerts SET calendar_event_id = ? WHERE id = ?",
        (event_id, concert_id)
    )
    conn.commit()
    conn.close()


def get_concerts():
    """Retrieves all concerts ordered by date descending."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, date, location, notes, calendar_event_id, source_file
        FROM concerts ORDER BY date DESC
    """)
    concerts = cursor.fetchall()
    conn.close()
    return concerts


def get_concerts_without_calendar_event():
    """Retrieves concerts that haven't been synced to Google Calendar yet."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, date, location, notes, source_file
        FROM concerts WHERE calendar_event_id IS NULL OR calendar_event_id = ''
        ORDER BY date DESC
    """)
    concerts = cursor.fetchall()
    conn.close()
    return concerts