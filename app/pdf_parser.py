import pdfplumber
import re
from datetime import datetime
from typing import List, Dict, Optional


# Common date patterns
DATE_PATTERNS = [
    r"\b(\d{4}-\d{2}-\d{2})\b",           # 2024-12-25
    r"\b(\d{2}/\d{2}/\d{4})\b",           # 12/25/2024
    r"\b(\d{2}-\d{2}-\d{4})\b",           # 12-25-2024
    r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b",  # 25 Dec 2024
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b",  # Dec 25, 2024
]

VENUE_KEYWORDS = [
    "venue", "location", "place", "sala", "lugar", "where", "at", "@",
    "theatre", "theater", "hall", "arena", "stadium", "club", "bar",
    "auditorium", "center", "centre", "pavilion", "amphitheatre"
]


def parse_date(text: str) -> Optional[str]:
    """Attempts to parse a date from text and returns YYYY-MM-DD format."""
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y"):
                try:
                    return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
    return None


def extract_venue(text: str) -> Optional[str]:
    """Attempts to extract a venue name from text."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    for line in lines:
        lower = line.lower()
        for kw in VENUE_KEYWORDS:
            if kw in lower:
                # Return the line or the part after the keyword
                idx = lower.index(kw)
                candidate = line[idx + len(kw):].strip(" :.-")
                if candidate:
                    return candidate[:100]  # Truncate
                return line[:100]
    # Fallback: first non-date, non-empty line that looks like a place
    for line in lines:
        if not parse_date(line) and len(line) > 3:
            return line[:100]
    return None


def extract_notes(text: str, date: str, venue: str) -> str:
    """Returns remaining text as notes, excluding the date/venue lines."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    notes_lines = []
    for line in lines:
        if parse_date(line) == date:
            continue
        if venue and venue.lower() in line.lower():
            continue
        notes_lines.append(line)
    return "\n".join(notes_lines)[:500]  # Truncate


def parse_pdf(file_path: str) -> List[Dict]:
    """
    Parses a PDF file and returns a list of concert dicts:
    [{date, location, notes, source_file}, ...]
    """
    concerts = []
    with pdfplumber.open(file_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    # Heuristic: split by page or by double newlines
    # Try to find multiple concerts in one PDF
    chunks = re.split(r"\n\s*\n", full_text)
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        date = parse_date(chunk)
        venue = extract_venue(chunk)
        if date or venue:
            notes = extract_notes(chunk, date or "", venue or "")
            concerts.append({
                "date": date or "",
                "location": venue or "",
                "notes": notes,
                "source_file": file_path
            })

    # If no concerts found, return one entry with raw text as notes
    if not concerts:
        concerts.append({
            "date": "",
            "location": "",
            "notes": full_text[:500],
            "source_file": file_path
        })

    return concerts