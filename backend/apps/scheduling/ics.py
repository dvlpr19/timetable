"""iCalendar (RFC 5545) export: one event per dated lesson, so holidays, odd/even weeks and
session dates come out exactly as in the app."""

from datetime import UTC, datetime

from django.utils import timezone

from apps.core import clock

from .models import OccurrenceStatus

PRODID = "-//Dars jadvali//IIAU//UZ"


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    """Lines longer than 75 octets continue on the next line after a space."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, current = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(current) + len(b) > (75 if not parts else 74):
            parts.append(current.decode("utf-8"))
            current = b""
        current += b
    parts.append(current.decode("utf-8"))
    return "\r\n ".join(parts)


def _utc(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def build_calendar(occurrences, payloads: dict[int, dict], name: str) -> str:
    """occurrences: EntryOccurrence rows; payloads: entry id -> entry_payload()."""
    stamp = _utc(clock.now() if clock.is_demo() else timezone.now())
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(name)}",
        "X-WR-TIMEZONE:Asia/Tashkent",
    ]
    for occ in occurrences:
        e = payloads[occ.entry_id]
        title = f"{e['subject']['name']} ({e['lesson_type']['name'].lower()})"
        room = e["room"]
        location = f"{room['name']}, {room['building']}" if room else e["online_url"]
        groups = ", ".join(g["name"] for g in e["groups"])
        description = f"{e['teacher']['full_name']}\n{groups}"
        lines += [
            "BEGIN:VEVENT",
            f"UID:occ-{occ.pk}@dars-jadvali",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{_utc(occ.during.lower)}",
            f"DTEND:{_utc(occ.during.upper)}",
            f"SUMMARY:{_escape(title)}",
            f"LOCATION:{_escape(location or '')}",
            f"DESCRIPTION:{_escape(description)}",
        ]
        if e["online_url"] and not room:
            lines.append(f"URL:{e['online_url']}")
        if occ.status != OccurrenceStatus.SCHEDULED:
            lines.append("STATUS:CANCELLED")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
