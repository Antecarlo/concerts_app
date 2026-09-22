"""
Unit and integration tests for pdf_parser.py
Tests every internal function and the main parse_pdf flow.
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.pdf_parser import (
    _infer_year_and_month,
    _parse_date,
    _extract_venue_and_event,
    _add_hours,
    parse_pdf,
    MONTHS_ES,
    DAYS_ES,
    ROW_PATTERN,
)

@pytest.fixture
def temp_pdf_realistic(tmp_path):
    """
    Creates a PDF closely matching the 'Horario Septiembre' real format,
    with 9 concert rows.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    filepath = tmp_path / "Horario_Septiembre_2026.pdf"
    c = canvas.Canvas(str(filepath), pagesize=A4)

    lines = [
        ("CULTURA", 780),
        ("BANDA DE MÚSICA", 760),
        ("AVANCE DEL MES DE SEPTIEMBRE DE 2026", 740),
        ("ACTUACIONES", 720),
        ("DÍA ACTUACION-LUGAR HORA", 700),
        ("Viernes 4 Concierto Programado, (Lugar por confirmar) 20:30 H", 680),
        ("Viernes 11 Concierto Programado, Plaza de las Pasiegas 20:30 H", 660),
        ("Domingo 14 Voto de la Ciudad al Cristo de San Agustín (San Antón) 20:00 H", 640),
        ("Lunes 15 Ofrenda Floral Virgen de las Angustias 17:30 H", 620),
        ("Viernes 18 Concierto Programado, Plaza de las Pasiegas 20:00 H", 600),
        ("Domingo 20 Concierto Joaquina Egüara 12:00 H", 580),
        ("Viernes 25 Concierto Programado, (Lugar por confirmar) 20:00 H", 560),
        ("Sábado 26 Misa Virgen de las Angustias 11:45 H", 540),
        ("Domingo 27 Procesión Virgen de las Angustias 17:30 H", 520),
        ("ENSAYOS: 1, 2, 3, 8, 9, 10, 16, 17, 22, 23, 24, 29 y 30.", 500),
        ("DESCANSOS: 5, 6, 7, 12, 13, 19, 21 y 28.", 480),
        ("OBSERVACIONES:", 460),
        ("Los ensayos de carácter individual y de conjunto del mes anterior...", 440),
        ("Granada a 15 de Agosto de 2026", 420),
        ("Director de la Banda Municipal de Música de Granada", 400),
    ]
    for text, y in lines:
        c.drawString(50, y, text)

    c.save()
    return str(filepath)

@pytest.fixture
def temp_pdf_simple(tmp_path):
    """Simple PDF with fewer rows for quick testing."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    filepath = tmp_path / "simple_schedule.pdf"
    c = canvas.Canvas(str(filepath), pagesize=A4)
    c.drawString(50, 800, "AVANCE DEL MES DE SEPTIEMBRE DE 2026")
    c.drawString(50, 770, "ACTUACIONES")
    c.drawString(50, 750, "Viernes 4 Concierto Programado, Plaza Mayor 20:30 H")
    c.drawString(50, 730, "Domingo 20 Concierto Especial, Teatro Central 12:00 H")
    c.drawString(50, 710, "Martes 9 Ningun evento aqui")
    c.save()
    return str(filepath)

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

class TestAddHours:
    def test_add_two_hours(self):
        assert _add_hours("20:30", 2) == "22:30"

    def test_wrap_midnight(self):
        assert _add_hours("23:00", 2) == "01:00"

    def test_empty_string(self):
        assert _add_hours("", 2) == ""

    def test_invalid_string(self):
        assert _add_hours("abc", 2) == ""

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

    def test_parenthetical_location(self):
        """Location can be in parentheses like '(Lugar por confirmar)'."""
        m = ROW_PATTERN.search("Viernes 4 Concierto, (Lugar por confirmar) 20:30 H")
        assert m is not None
        assert m.group("description").strip() == "Concierto, (Lugar por confirmar)"
        assert m.group("time") == "20:30"

class TestParsePdfRealistic:
    """Tests that parse the full 9-concert realistic PDF fixture."""

    def test_returns_concerts(self, temp_pdf_realistic):
        results = parse_pdf(temp_pdf_realistic)
        assert len(results) > 0
        for concert in results:
            assert "date" in concert
            assert "start_time" in concert
            assert "end_time" in concert
            assert "location" in concert
            assert "notes" in concert
            assert "source_file" in concert

    def test_all_have_dates(self, temp_pdf_realistic):
        results = parse_pdf(temp_pdf_realistic)
        for concert in results:
            assert concert["date"] != ""
            parts = concert["date"].split("-")
            assert len(parts) == 3, f"Invalid date format: {concert['date']}"

    def test_september_dates(self, temp_pdf_realistic):
        results = parse_pdf(temp_pdf_realistic)
        for concert in results:
            assert concert["date"].startswith("2026-09-"), \
                f"Expected September 2026, got {concert['date']}"

    def test_all_have_locations(self, temp_pdf_realistic):
        results = parse_pdf(temp_pdf_realistic)
        for concert in results:
            assert concert["location"] != ""

    def test_all_have_notes(self, temp_pdf_realistic):
        results = parse_pdf(temp_pdf_realistic)
        for concert in results:
            assert concert["notes"] != ""

    def test_source_file(self, temp_pdf_realistic):
        results = parse_pdf(temp_pdf_realistic)
        for concert in results:
            assert concert["source_file"] == temp_pdf_realistic

    def test_expected_count(self, temp_pdf_realistic):
        """We expect 9 concerts, matching the real PDF format."""
        results = parse_pdf(temp_pdf_realistic)
        assert len(results) == 9, f"Expected 9 concerts, got {len(results)}"

    def test_specific_concert_plaza_pasiegas(self, temp_pdf_realistic):
        """Verify the 'Plaza de las Pasiegas' concert on 2026-09-11."""
        results = parse_pdf(temp_pdf_realistic)
        found = [c for c in results if "Pasiegas" in c["location"]]
        assert len(found) >= 1
        concert = found[0]
        assert concert["date"] == "2026-09-11"

    def test_specific_concert_lugar_confirmar(self, temp_pdf_realistic):
        """Concerts with '(Lugar por confirmar)' should be extracted."""
        results = parse_pdf(temp_pdf_realistic)
        found = [c for c in results if "confirmar" in c["location"]]
        assert len(found) >= 1

    def test_time_in_notes(self, temp_pdf_realistic):
        """Check that time info is present in notes."""
        results = parse_pdf(temp_pdf_realistic)
        for concert in results:
            assert ":" in concert["notes"]

    def test_start_time_extracted(self, temp_pdf_realistic):
        results = parse_pdf(temp_pdf_realistic)
        for concert in results:
            assert concert["start_time"] != ""
            assert ":" in concert["start_time"]

    def test_end_time_default_plus_two(self, temp_pdf_realistic):
        results = parse_pdf(temp_pdf_realistic)
        for concert in results:
            assert concert["end_time"] != ""
            h1, m1 = map(int, concert["start_time"].split(":"))
            h2, m2 = map(int, concert["end_time"].split(":"))
            total1 = h1 * 60 + m1
            total2 = h2 * 60 + m2
            diff = (total2 - total1) % (24 * 60)
            assert diff == 120, f"Expected +2h, got {diff} min for {concert['start_time']} -> {concert['end_time']}"

class TestParsePdfSimple:
    def test_returns_expected(self, temp_pdf_simple):
        results = parse_pdf(temp_pdf_simple)
        assert len(results) >= 2

    def test_first_concert(self, temp_pdf_simple):
        results = parse_pdf(temp_pdf_simple)
        first = results[0]
        assert first["date"] == "2026-09-04"
        assert "Plaza Mayor" in first["location"]
        assert first["start_time"] == "20:30"
        assert first["end_time"] == "22:30"

    def test_event_name(self, temp_pdf_simple):
        results = parse_pdf(temp_pdf_simple)
        concert = [c for c in results if "Teatro Central" in c["location"]]
        assert len(concert) >= 1
        assert "Concierto Especial" in concert[0]["notes"]
        assert concert[0]["start_time"] == "12:00"

    def test_source_file(self, temp_pdf_simple):
        results = parse_pdf(temp_pdf_simple)
        for r in results:
            assert r["source_file"] == temp_pdf_simple

    def test_no_empty_dates(self, temp_pdf_simple):
        results = parse_pdf(temp_pdf_simple)
        for r in results:
            assert r["date"] != ""

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
        assert results[0]["start_time"] == ""
        assert results[0]["end_time"] == ""
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
        assert len(results) == 1
