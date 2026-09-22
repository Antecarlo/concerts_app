"""
Unit and integration tests for database.py
Uses an in-memory SQLite database overridden via monkeypatching.
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import database


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_db_path(tmp_path, monkeypatch):
    """Override DB_DIR to a temp directory so tests don't touch the real DB."""
    test_dir = str(tmp_path / ".concert_diary_app")
    monkeypatch.setattr(database, "DB_DIR", test_dir)
    monkeypatch.setattr(database, "DB_PATH", os.path.join(test_dir, "concerts.db"))
    database.init_db()
    yield
    # Cleanup: remove test DB
    if os.path.exists(database.DB_PATH):
        os.remove(database.DB_PATH)
    if os.path.exists(database.DB_DIR):
        os.rmdir(database.DB_DIR)


@pytest.fixture
def sample_concert_id(patch_db_path):
    """Insert a sample concert and return its ID."""
    return database.add_concert("2026-09-04", "Plaza Mayor", "Concierto de prueba", "test.pdf")


# ── Unit tests: init_db ─────────────────────────────────────────────

class TestInitDb:
    def test_db_created(self):
        assert os.path.exists(database.DB_DIR)
        assert os.path.exists(database.DB_PATH)

    def test_table_exists(self):
        """Verify the concerts table was created."""
        import sqlite3
        conn = sqlite3.connect(database.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='concerts'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_table_columns(self):
        import sqlite3
        conn = sqlite3.connect(database.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(concerts)")
        columns = {col[1] for col in cursor.fetchall()}
        expected = {"id", "date", "location", "notes", "calendar_event_id", "source_file", "created_at"}
        assert expected.issubset(columns), f"Missing columns: {expected - columns}"
        conn.close()


# ── Unit tests: add_concert ─────────────────────────────────────────

class TestAddConcert:
    def test_add_and_return_id(self):
        cid = database.add_concert("2026-09-11", "Teatro Central", "Nota", "f.pdf")
        assert isinstance(cid, int)
        assert cid > 0

    def test_add_minimal(self):
        cid = database.add_concert("2026-09-20", "Plaza Mayor")
        assert cid > 0

    def test_add_without_source(self):
        cid = database.add_concert("2026-10-01", "Auditorio", "Sin archivo")
        assert cid > 0

    def test_add_duplicate_dates(self):
        """Adding multiple events with the same date should work."""
        cid1 = database.add_concert("2026-09-04", "Lugar A", "Evento 1")
        cid2 = database.add_concert("2026-09-04", "Lugar B", "Evento 2")
        assert cid1 != cid2

    def test_add_empty_notes(self):
        cid = database.add_concert("2026-09-15", "Sala Mozart", "")
        assert cid > 0


# ── Unit tests: update_concert ──────────────────────────────────────

class TestUpdateConcert:
    def test_update_all_fields(self, sample_concert_id):
        database.update_concert(sample_concert_id, "2027-01-01", "New Venue", "New notes")
        concerts = database.get_concerts()
        match = [c for c in concerts if c[0] == sample_concert_id]
        assert len(match) == 1
        _, date, loc, notes, _, _ = match[0]
        assert date == "2027-01-01"
        assert loc == "New Venue"
        assert notes == "New notes"

    def test_update_partial(self, sample_concert_id):
        """update_concert requires all 3 fields, but we can pass unchanged values."""
        database.update_concert(sample_concert_id, "2026-09-04", "Plaza Mayor", "Updated notes")
        concerts = database.get_concerts()
        match = [c for c in concerts if c[0] == sample_concert_id]
        assert match[0][3] == "Updated notes"

    def test_update_nonexistent_id(self):
        """Updating a non-existent ID should not raise an error (no-op)."""
        database.update_concert(99999, "2026-09-04", "Place", "Notes")


# ── Unit tests: set_calendar_event_id ───────────────────────────────

class TestSetCalendarEventId:
    def test_set_event_id(self, sample_concert_id):
        database.set_calendar_event_id(sample_concert_id, "abc123event")
        concerts = database.get_concerts()
        match = [c for c in concerts if c[0] == sample_concert_id]
        assert match[0][4] == "abc123event"

    def test_overwrite_event_id(self, sample_concert_id):
        database.set_calendar_event_id(sample_concert_id, "first_id")
        database.set_calendar_event_id(sample_concert_id, "second_id")
        concerts = database.get_concerts()
        match = [c for c in concerts if c[0] == sample_concert_id]
        assert match[0][4] == "second_id"

    def test_set_event_id_nonexistent(self):
        """Setting event ID on non-existent ID should not raise."""
        database.set_calendar_event_id(99999, "some_id")


# ── Integration tests: get_concerts ─────────────────────────────────

class TestGetConcerts:
    def test_empty_db(self):
        results = database.get_concerts()
        assert results == []

    def test_after_insert(self, sample_concert_id):
        results = database.get_concerts()
        assert len(results) == 1

    def test_order_descending(self):
        database.add_concert("2026-09-04", "Venue A", "First")
        database.add_concert("2026-09-20", "Venue B", "Second")
        database.add_concert("2026-09-11", "Venue C", "Third")
        results = database.get_concerts()
        # Dates should be descending: 2026-09-20, 2026-09-11, 2026-09-04
        assert results[0][1] == "2026-09-20"
        assert results[1][1] == "2026-09-11"
        assert results[2][1] == "2026-09-04"

    def test_full_row_content(self, sample_concert_id):
        results = database.get_concerts()
        row = results[0]
        # Row format: (id, date, location, notes, calendar_event_id, source_file)
        assert len(row) == 6
        assert row[0] == sample_concert_id
        assert row[1] == "2026-09-04"
        assert row[2] == "Plaza Mayor"
        assert row[3] == "Concierto de prueba"
        assert row[4] is None  # no calendar_event_id set
        assert row[5] == "test.pdf"

    def test_multiple_concerts(self):
        c1 = database.add_concert("2026-09-04", "Lugar A", "Nota 1")
        c2 = database.add_concert("2026-09-11", "Lugar B", "Nota 2")
        results = database.get_concerts()
        assert len(results) == 2


# ── Integration tests: get_concerts_without_calendar_event ─────────

class TestGetConcertsWithoutCalendarEvent:
    def test_all_unsynced_initially(self, sample_concert_id):
        results = database.get_concerts_without_calendar_event()
        assert len(results) == 1
        assert results[0][0] == sample_concert_id

    def test_excludes_synced(self, sample_concert_id):
        database.set_calendar_event_id(sample_concert_id, "event_123")
        results = database.get_concerts_without_calendar_event()
        assert len(results) == 0

    def test_mixed_synced_and_unsynced(self):
        synced = database.add_concert("2026-09-04", "A", "notes")
        unsynced = database.add_concert("2026-09-11", "B", "notes")
        database.set_calendar_event_id(synced, "event_abc")
        results = database.get_concerts_without_calendar_event()
        assert len(results) == 1
        assert results[0][0] == unsynced

    def test_empty_when_all_synced(self):
        c1 = database.add_concert("2026-09-04", "A", "n")
        c2 = database.add_concert("2026-09-11", "B", "n")
        database.set_calendar_event_id(c1, "e1")
        database.set_calendar_event_id(c2, "e2")
        results = database.get_concerts_without_calendar_event()
        assert len(results) == 0

    def test_empty_db(self):
        results = database.get_concerts_without_calendar_event()
        assert results == []

    def test_returns_correct_columns(self):
        cid = database.add_concert("2026-09-04", "Venue", "Notes", "source.pdf")
        results = database.get_concerts_without_calendar_event()
        row = results[0]
        # Should be (id, date, location, notes, source_file)
        assert len(row) == 5
        assert row[0] == cid
        assert row[4] == "source.pdf"