"""CSV text -> (valid bookings, invalid rows). Never raises on bad row data."""

import csv
import datetime
import re

from .conflicts import normalize_room
from .models import Booking, InvalidRow

REQUIRED_COLUMNS = ("id", "room", "date", "start", "end", "status")

_ID_RE = re.compile(r"^[0-9]+$")
_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_TIME_RE = re.compile(r"^([0-9]{1,2}):([0-9]{2})$")


class MissingColumnsError(ValueError):
    """The file is empty or its header lacks required columns."""


def parse_date(text):
    text = text.strip()
    if not _DATE_RE.match(text):
        raise ValueError("date must be YYYY-MM-DD")
    year, month, day = (int(p) for p in text.split("-"))
    try:
        return datetime.date(year, month, day)
    except ValueError:
        raise ValueError("date does not exist")


def parse_time(text):
    """'9:15' or '09:15' -> minutes since midnight. 24-hour clock, 00:00-23:59."""
    match = _TIME_RE.match(text.strip())
    if not match:
        raise ValueError("time must be HH:MM")
    hours, minutes = int(match.group(1)), int(match.group(2))
    if hours > 23 or minutes > 59:
        raise ValueError("time is out of range")
    return hours * 60 + minutes


def parse_request(room, date, start, end):
    """Validate an availability request. Returns (room_key, date, start, end).

    Raises ValueError with a readable message on any problem.
    """
    if not room or not room.strip():
        raise ValueError("room is empty")
    try:
        parsed_date = parse_date(date)
    except ValueError as err:
        raise ValueError("date '%s': %s" % (date, err))
    try:
        start_min = parse_time(start)
    except ValueError as err:
        raise ValueError("start time '%s': %s" % (start, err))
    try:
        end_min = parse_time(end)
    except ValueError as err:
        raise ValueError("end time '%s': %s" % (end, err))
    if end_min <= start_min:
        raise ValueError("end is not after start")
    return normalize_room(room), parsed_date, start_min, end_min


def parse_bookings(lines):
    """Parse CSV lines. Returns (bookings, invalid_rows).

    Raises MissingColumnsError only if the header itself is unusable.
    """
    reader = csv.reader(lines)
    try:
        header = next(reader)
    except StopIteration:
        raise MissingColumnsError("file is empty")
    header = [h.strip().lower() for h in header]
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing_cols:
        raise MissingColumnsError("missing column(s): " + ", ".join(missing_cols))
    index = {name: header.index(name) for name in REQUIRED_COLUMNS}

    bookings = []
    invalid = []
    seen_ids = set()

    for row in reader:
        row_number = reader.line_num
        if not any(cell.strip() for cell in row):
            continue  # blank line

        def get(name):
            i = index[name]
            return row[i].strip() if i < len(row) else ""

        status = get("status").lower()
        if status == "cancelled":
            continue  # ignored completely, even if otherwise malformed

        raw_id = get("id")
        row_id = int(raw_id) if _ID_RE.match(raw_id) else None

        def reject(reason):
            invalid.append(InvalidRow(row_number, row_id, reason))

        empty = [name for name in REQUIRED_COLUMNS if not get(name)]
        if empty:
            reject("missing value: " + ", ".join(empty))
            continue
        if row_id is None:
            reject("id is not a whole number")
            continue
        if status != "confirmed":
            reject("status must be confirmed or cancelled")
            continue
        if row_id in seen_ids:
            reject("duplicate id")
            continue

        try:
            date = parse_date(get("date"))
        except ValueError as err:
            reject("date can't be read (%s)" % err)
            continue
        try:
            start = parse_time(get("start"))
        except ValueError as err:
            reject("start time can't be read (%s)" % err)
            continue
        try:
            end = parse_time(get("end"))
        except ValueError as err:
            reject("end time can't be read (%s)" % err)
            continue
        if end <= start:
            reject("end is not after start")
            continue

        seen_ids.add(row_id)
        bookings.append(Booking(row_id, normalize_room(get("room")), date, start, end))

    return bookings, invalid


def load_bookings(path):
    """Read a CSV file from disk. Undecodable bytes are replaced, not fatal."""
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as handle:
        return parse_bookings(handle)
