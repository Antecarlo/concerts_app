import pdfplumber
import re
from datetime import datetime
from typing import List, Dict, Optional

# ── Month name mapping (Spanish → English) ──────────────────────────
MONTHS_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# ── Day-of-week names (Spanish) ─────────────────────────────────────
DAYS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

# ── Regex: line that starts a "concert" row ─────────────────────────
# Format: "Viernes 4 Concierto Programado, (Lugar por confirmar) 20:30 H"
#        "Domingo 20 Concierto Joaquina Egüara 12:00 H"
ROW_PATTERN = re.compile(
    r"(?P<dayname>" + "|".join(DAYS_ES) + r")\s+"
    r"(?P<day>\d{1,2})\s+"
    r"(?P<description>.+?)\s+"
    r"(?P<time>\d{1,2}:\d{2})\s*H?",
    re.IGNORECASE
)

# ── Venue indicator keywords in Spanish ─────────────────────────────
VENUE_KEYWORDS_ES = [
    "plaza", "teatro", "teatre", "auditorio", "sala", "lugar",
    "palacio", "estadio", "pabellón", "centro", "club", "bar",
]


def _infer_year_and_month(full_text: str) -> tuple:
    """Try to extract the year and month from header text like:
    'AVANCE DEL MES DE SEPTIEMBRE DE 2026'
    Returns (year, month_number) or (None, None).
    """
    m = re.search(r"(?:MES\s+DE\s+)?(\w+)\s+DE\s+(\d{4})", full_text, re.IGNORECASE)
    if m:
        month_name = m.group(1).lower()
        year = int(m.group(2))
        month_num = MONTHS_ES.get(month_name)
        return year, month_num
    # Fallback: try to find any 4-digit year
    m2 = re.search(r"\b(20\d{2})\b", full_text)
    if m2:
        return int(m2.group(1)), None
    return None, None


def _parse_date(day: int, month: int, year: int) -> str:
    """Return a YYYY-MM-DD string."""
    return f"{year:04d}-{month:02d}-{day:02d}"


def _extract_venue_and_event(description: str) -> tuple:
    """
    From a description like:
        'Concierto Programado, Plaza de las Pasiegas'
        'Ofrenda Floral Virgen de las Angustias'
        'Misa Virgen de las Angustias'
    Returns (event_name, venue).
    """
    desc = description.strip()
    venue = ""

    # Try to split by comma or dash, second part is often the venue
    parts = re.split(r"[,\-–—]+", desc)
    if len(parts) >= 2:
        venue = parts[-1].strip()
        event = " - ".join(p.strip() for p in parts[:-1])
    else:
        event = desc

    # If venue still looks like an event (no known venue keyword), treat as notes
    if venue:
        low_venue = venue.lower()
        has_kw = any(kw in low_venue for kw in VENUE_KEYWORDS_ES)
        # If not a clear venue keyword, keep it as part of event/notes
        if not has_kw and len(venue.split()) > 5:
            event = desc
            venue = ""
    else:
        # Try to find a venue keyword inside the full description
        for kw in VENUE_KEYWORDS_ES:
            idx = desc.lower().find(kw)
            if idx >= 0:
                venue_candidate = desc[idx:].strip(" ,-–—")
                if venue_candidate:
                    venue = venue_candidate
                    event = desc[:idx].strip(" ,-–—")
                    break

    return event[:200], venue[:100]


def parse_pdf(file_path: str) -> List[Dict]:
    """
    Parses a PDF file and returns a list of concert dicts:
    [{date, location, notes, source_file}, ...]
    Specifically handles the 'Horario Septiembre' schedule format.
    """
    concerts = []
    with pdfplumber.open(file_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    # Extract global year/month from header
    year, month_num = _infer_year_and_month(full_text)

    # If no month detected, try to match rows anyway with arbitrary month
    if month_num is None:
        # Try all months
        for name, num in MONTHS_ES.items():
            if name in full_text.lower():
                month_num = num
                break

    if year is None:
        year = 2026  # reasonable default for this format

    # Find all row matches
    for match in ROW_PATTERN.finditer(full_text):
        day = int(match.group("day"))
        description = match.group("description").strip()
        time_str = match.group("time")

        # Build date
        if month_num:
            date_str = _parse_date(day, month_num, year)
        else:
            date_str = f"{year:04d}-??-{day:02d}"

        # Extract event name and venue
        event_name, venue = _extract_venue_and_event(description)

        notes = f"{event_name} at {time_str}" if event_name and time_str else description

        concerts.append({
            "date": date_str,
            "location": venue or event_name[:100],
            "notes": notes,
            "source_file": file_path,
        })

    # If no rows matched, try the old generic approach
    if not concerts:
        lines = [line.strip() for line in full_text.split("\n") if line.strip()]
        # Look for any line with a day-of-week and a number
        for line in lines:
            m = re.match(
                r"(?P<dayname>" + "|".join(DAYS_ES) + r")\s+(?P<day>\d{1,2})\s+(.+)",
                line, re.IGNORECASE
            )
            if m:
                day = int(m.group("day"))
                rest = m.group(3).strip()
                # Try to extract time
                time_m = re.search(r"(\d{1,2}:\d{2})", rest)
                time_str = time_m.group(1) if time_m else ""
                rest_clean = re.sub(r"\d{1,2}:\d{2}\s*H?", "", rest).strip()
                event_name, venue = _extract_venue_and_event(rest_clean)
                date_str = _parse_date(day, month_num or 1, year)
                concerts.append({
                    "date": date_str,
                    "location": venue or event_name[:100],
                    "notes": f"{event_name} at {time_str}" if time_str else event_name,
                    "source_file": file_path,
                })

    # True final fallback
    if not concerts:
        concerts.append({
            "date": "",
            "location": "",
            "notes": full_text[:500],
            "source_file": file_path,
        })

    return concerts