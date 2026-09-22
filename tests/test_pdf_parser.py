"""
Unit and integration tests for pdf_parser.py
Tests every internal function and the main parse_pdf flow.
"""
import pytest
import os
import sys

# Ensure the project root is on sys.path so we can import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.pdf_parser import (
    _infer_year_and_month,
    _parse_date,
    _extract_venue_and_event,
    parse_pdf,
    MONTHS_ES,
    DAYS_ES,
    ROW_PATTERN,
)


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def sample_pdf_path():
    """Path to the real PDF on the developer's machine (used for integration)."""
    path = r"C:\Users\carli\Desktop\09.Horario Septiembre 2026.pdf"
    if os.path.exists(path):
        return path
    pytest.skip("Sample PDF not found at " + path)


@pytest.fixture
def temp_pdf(tmp_path):
    """Create a temporary PDF file for testing parse_pdf."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    filepath = tmp_path / "test_schedule.pdf"
    c = canvas.Canvas(str(filepath), pagesize=A4)
    c.drawString(50, 800, "AVANCE DEL MES DE SEPTIEMBRE DE 2026")
    c.drawString(50, 770, "ACTUACIONES")
    c.drawString(50, 750, "Viernes 4 Concierto Programado, Plaza Mayor 20:30 H")
    c.drawString(50, 730, "Domingo 20 Concierto Especial, Teatro Central 12:00 H")
    c.drawString(50, 710, "Martes 9 Ningun evento aqui")
    c.drawString(50, 690, "ENSAYOS: 1, 2, 3")
    c.save()
    return str(filepath)


# ── Unit tests: _infer_year_and_month ──────────────────────────────

class TestInferYearAndMonth:
    def test_header_septiembre(self):
        text = "AVANCE DEL MES DE SEPTIEMBRE DE 2026"
        year, month = _infer_year_and_month(text)
        assert year == 2026
        assert month == 9

    def test_header_enero(self):
        text = "MES DE ENERO DE 2025"
        year, month = _infer_year_and_month(text)
        assert year == 2025
        assert month == 1

    def test_header_diciembre(self):
        text = "MES DE DICIEMBRE DE 2027"
        year, month = _infer_year_and_month(text)
        assert year == 2027
        assert month == 12

    def test_no_month_just_year(self):
        text = "CALENDARIO 2023"
        year, month = _infer_year_and_month(text)
        assert year == 2023
        assert month is None

    def test_no_year(self):
        text = "Solo un texto sin año ni mes"
        year, month = _infer_year_and_month(text)
        assert year is None
        assert month is None

    def test_empty_string(self):
        year, month = _infer_year_and_month("")
        assert year is None
        assert month is None


# ── Unit tests: _parse_date ────────────────────────────────────────

class TestParseDate:
    def test_normal(self):
        assert _parse_date(4, 9, 2026) == "2026-09-04"

    def test_single_digits(self):
        assert _parse_date(1, 1, 2025) == "2025-01-01"

    def test_december(self):
        assert _parse_date(31, 12, 2023) == "2023-12-31"

    def test_padding_day(self):
        assert _parse_date(9, 10, 2024) == "2024-10-09"

    def test_padding_month(self):
        assert _parse_date(15, 3, 2020) == "2020-03-15"


# ── Unit tests: _extract_venue_and_event ───────────────────────────

class TestExtractVenueAndEvent:
    def test_comma_split_venue(self):
        event, venue = _extract_venue_and_event("Concierto Programado, Plaza de las Pasiegas")
        assert "Concierto Programado" in event
        assert "Plaza de las Pasiegas" in venue

    def test_no_comma_with_venue_keyword(self):
        event, venue = _extract_venue_and_event("Concierto en el Teatro Central")
        assert "Concierto en el" in event
        assert "Teatro Central" in venue

    def test_no_venue_at_all(self):
        event, venue = _extract_venue_and_event("Misa Virgen de las Angustias")
        assert event == "Misa Virgen de las Angustias"
        assert venue == ""

    def test_dash_split(self):
        event, venue = _extract_venue_and_event("Ofrenda Floral – Plaza Mayor")
        assert "Ofrenda Floral" in event
        assert "Plaza Mayor" in venue

    def test_em_dash_split(self):
        event, venue = _extract_venue_and_event("Concierto — Auditorio Nacional")
        assert "Concierto" in event
        assert "Auditorio Nacional" in venue

    def test_lugar_por_confirmar(self):
        event, venue = _extract_venue_and_event("Concierto Programado, (Lugar por confirmar)")
        assert "Concierto Programado" in event
        # "(Lugar por confirmar)" contains "lugar" keyword, so it should be extracted as venue
        assert venue != ""

    def test_empty_string(self):
        event, venue = _extract_venue_and_event("")
        assert event == ""
        assert venue == ""

    def test_venue_centro(self):
        event, venue = _extract_venue_and_event("Evento, Centro Cultural")
        assert "Centro Cultural" in venue

    def test_venue_auditorio(self):
        event, venue = _extract_venue_and_event("Concierto, Auditorio Municipal")
        assert "Auditorio Municipal" in venue

    def test_sala_keyword(self):
        event, venue = _extract_venue_and_event("Festival, Sala Mozart")
        assert "Sala Mozart" in venue


# ── Unit tests: ROW_PATTERN regex ──────────────────────────────────

class TestRowPattern:
    def test_standard_row(self):
        m = ROW_PATTERN.search("Viernes 4 Concierto, Plaza Mayor 20:30 H")
        assert m is not None
        assert m.group("dayname") == "Viernes"
        assert m.group("day") == "4"
        assert "Concierto, Plaza Mayor" in m.group("description")
        assert m.group("time") == "20:30"

    def test_no_time_h(self):
        m = ROW_PATTERN.search("Domingo 20 Evento 12:00")
        assert m is not None
        assert m.group("day") == "20"
        assert m.group("time") == "12:00"

    def test_not_a_row(self):
        m = ROW_PATTERN.search("ENSAYOS: 1, 2, 3")
        assert m is None

    def test_notes_line(self):
        m = ROW_PATTERN.search("DESCANSOS: 5, 6, 7")
        assert m is None

    def test_ignored_text(self):
        m = ROW_PATTERN.search("OBSERVACIONES:")
        assert m is None


# ── Integration tests: parse_pdf with real PDF ─────────────────────

class TestParsePdfIntegration:
    def test_real_pdf_returns_concerts(self, sample_pdf_path):
        """Integration test with the actual concert schedule PDF."""
        results = parse_pdf(sample_pdf_path)
        assert len(results) > 0
        for concert in results:
            assert "date" in concert
            assert "location" in concert
            assert "notes" in concert
            assert "source_file" in concert

    def test_real_pdf_all_have_dates(self, sample_pdf_path):
        results = parse_pdf(sample_pdf_path)
        for concert in results:
            assert concert["date"] != "", f"Missing date for {concert}"
            # Should be YYYY-MM-DD format
            parts = concert["date"].split("-")
            assert len(parts) == 3, f"Invalid date format: {concert['date']}"

    def test_real_pdf_september_dates(self, sample_pdf_path):
        results = parse_pdf(sample_pdf_path)
        for concert in results:
            assert concert["date"].startswith("2026-09-"), \
                f"Expected September 2026, got {concert['date']}"

    def test_real_pdf_all_have_locations(self, sample_pdf_path):
        results = parse_pdf(sample_pdf_path)
        for concert in results:
            assert concert["location"] != "", f"Missing location for {concert}"

    def test_real_pdf_all_have_notes(self, sample_pdf_path):
        results = parse_pdf(sample_pdf_path)
        for concert in results:
            assert concert["notes"] != "", f"Missing notes for {concert}"

    def test_real_pdf_source_file(self, sample_pdf_path):
        results = parse_pdf(sample_pdf_path)
        for concert in results:
            assert concert["source_file"] == sample_pdf_path

    def test_real_pdf_expected_count(self, sample_pdf_path):
        """We expect 9 concerts from this specific PDF."""
        results = parse_pdf(sample_pdf_path)
        assert len(results) == 9, f"Expected 9 concerts, got {len(results)}"

    def test_real_pdf_specific_concert(self, sample_pdf_path):
        """Verify a specific known entry."""
        results = parse_pdf(sample_pdf_path)
        # Find the "Plaza de las Pasiegas" concert on 2026-09-11
        found = [c for c in results if "Pasiegas" in c["location"]]
        assert len(found) >= 1
        concert = found[0]
        assert concert["date"] == "2026-09-11"

    def test_real_pdf_time_in_notes(self, sample_pdf_path):
        """Check that time info is present in notes."""
        results = parse_pdf(sample_pdf_path)
        for concert in results:
            assert ":" in concert["notes"], \
                f"Expected time in notes: {concert['notes']}"


# ── Integration tests: parse_pdf with temp PDF ─────────────────────

class TestParsePdfTempPdf:
    def test_temp_pdf_returns_expected(self, temp_pdf):
        results = parse_pdf(temp_pdf)
        # We expect at least 2 rows: Viernes 4 and Domingo 20
        # (Martes 9 line has no time → not matched by ROW_PATTERN)
        assert len(results) >= 2

    def test_temp_pdf_first_concert(self, temp_pdf):
        results = parse_pdf(temp_pdf)
        # First row: "Viernes 4 Concierto Programado, Plaza Mayor 20:30 H"
        first = results[0]
        assert first["date"] == "2026-09-04"
        assert "Plaza Mayor" in first["location"]

    def test_temp_pdf_event_name(self, temp_pdf):
        results = parse_pdf(temp_pdf)
        # "Domingo 20 Concierto Especial, Teatro Central 12:00 H"
        concert = [c for c in results if "Teatro Central" in c["location"]]
        assert len(concert) >= 1
        assert "Concierto Especial" in concert[0]["notes"]

    def test_temp_pdf_source_file(self, temp_pdf):
        results = parse_pdf(temp_pdf)
        for r in results:
            assert r["source_file"] == temp_pdf

    def test_temp_pdf_no_empty_dates(self, temp_pdf):
        results = parse_pdf(temp_pdf)
        for r in results:
            assert r["date"] != ""


# ── Edge cases for parse_pdf ───────────────────────────────────────

class TestParsePdfEdgeCases:
    def test_nonexistent_file(self):
        with pytest.raises(Exception):
            parse_pdf("/path/to/nonexistent.pdf")

    def test_empty_pdf(self, tmp_path):
        """Create an empty PDF (no text) and verify fallback."""
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        filepath = tmp_path / "empty.pdf"
        c = canvas.Canvas(str(filepath), pagesize=A4)
        c.save()
        results = parse_pdf(str(filepath))
        assert len(results) == 1
        assert results[0]["date"] == ""
        assert results[0]["location"] == ""
        assert results[0]["source_file"] == str(filepath)

    def test_pdf_with_only_header(self, tmp_path):
        """PDF with header but no concert rows."""
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        filepath = tmp_path / "header_only.pdf"
        c = canvas.Canvas(str(filepath), pagesize=A4)
        c.drawString(50, 800, "AVANCE DEL MES DE ENERO DE 2025")
        c.drawString(50, 770, "No hay conciertos aqui")
        c.save()
        results = parse_pdf(str(filepath))
        # No rows matched, should yield fallback
        assert len(results) == 1