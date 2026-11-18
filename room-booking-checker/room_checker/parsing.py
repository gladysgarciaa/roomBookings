"""CSV text -> (valid bookings, invalid rows). Never raises on bad row data."""

import csv
import datetime
import re

from .conflicts import normalize_room
from .models import Booking, InvalidRow


class MissingColumnsError(ValueError):
    """The file is empty or its header lacks required columns."""


class BookingParser:
    REQUIRED_COLUMNS = ("id", "room", "date", "start", "end", "status")

    _ID_RE = re.compile(r"^[0-9]+$")
    _DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    _TIME_RE = re.compile(r"^([0-9]{1,2}):([0-9]{2})$")

    def __init__(self):
        self.bookings = []
        self.invalid = []
        self._seen_ids = set()

    # ---- single values -------------------------------------------------

    @classmethod
    def parse_date(cls, text):
        text = text.strip()
        if not cls._DATE_RE.match(text):
            raise ValueError("date must be YYYY-MM-DD")
        year, month, day = (int(p) for p in text.split("-"))
        try:
            return datetime.date(year, month, day)
        except ValueError:
            raise ValueError("date does not exist")

    @classmethod
    def parse_time(cls, text):
        """'9:15' or '09:15' -> minutes since midnight. 24-hour clock, 00:00-23:59."""
        match = cls._TIME_RE.match(text.strip())
        if not match:
            raise ValueError("time must be HH:MM")
        hours, minutes = int(match.group(1)), int(match.group(2))
        if hours > 23 or minutes > 59:
            raise ValueError("time is out of range")
        return hours * 60 + minutes

    # ---- availability request ------------------------------------------

    @classmethod
    def parse_request(cls, room, date, start, end):
        """Validate an availability request. Returns (room_key, date, start, end)."""
        if not room or not room.strip():
            raise ValueError("room is empty")

        values = {}
        for name, label, parser, text in (
            ("date", "date", cls.parse_date, date),
            ("start", "start time", cls.parse_time, start),
            ("end", "end time", cls.parse_time, end),
        ):
            try:
                values[name] = parser(text)
            except ValueError as err:
                raise ValueError("%s '%s': %s" % (label, text, err))

        if values["end"] <= values["start"]:
            raise ValueError("end is not after start")
        return normalize_room(room), values["date"], values["start"], values["end"]

    # ---- CSV -----------------------------------------------------------

    def parse_lines(self, lines):
        """Parse CSV lines into self.bookings / self.invalid and return them.

        Raises MissingColumnsError only if the header itself is unusable.
        """
        reader = csv.reader(lines)
        index = self._read_header(reader)

        for row in reader:
            if not any(cell.strip() for cell in row):
                continue  # blank line
            self._parse_row(row, reader.line_num, index)

        return self.bookings, self.invalid

    def load(self, path):
        """Read a CSV file from disk. Undecodable bytes are replaced, not fatal."""
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as handle:
            return self.parse_lines(handle)

    def _read_header(self, reader):
        try:
            header = next(reader)
        except StopIteration:
            raise MissingColumnsError("file is empty")
        header = [h.strip().lower() for h in header]
        missing = [c for c in self.REQUIRED_COLUMNS if c not in header]
        if missing:
            raise MissingColumnsError("missing column(s): " + ", ".join(missing))
        return {name: header.index(name) for name in self.REQUIRED_COLUMNS}

    def _parse_row(self, row, row_number, index):
        def get(name):
            i = index[name]
            return row[i].strip() if i < len(row) else ""

        status = get("status").lower()
        if status == "cancelled":
            return  # ignored completely, even if otherwise malformed

        raw_id = get("id")
        row_id = int(raw_id) if self._ID_RE.match(raw_id) else None

        def reject(reason):
            self.invalid.append(InvalidRow(row_number, row_id, reason))

        empty = [name for name in self.REQUIRED_COLUMNS if not get(name)]
        if empty:
            return reject("missing value: " + ", ".join(empty))
        if row_id is None:
            return reject("id is not a whole number")
        if status != "confirmed":
            return reject("status must be confirmed or cancelled")
        if row_id in self._seen_ids:
            return reject("duplicate id")

        values = {}
        for name, label, parser in (
            ("date", "date", self.parse_date),
            ("start", "start time", self.parse_time),
            ("end", "end time", self.parse_time),
        ):
            try:
                values[name] = parser(get(name))
            except ValueError as err:
                return reject("%s can't be read (%s)" % (label, err))

        if values["end"] <= values["start"]:
            return reject("end is not after start")

        self._seen_ids.add(row_id)
        self.bookings.append(
            Booking(row_id, normalize_room(get("room")),
                    values["date"], values["start"], values["end"])
        )


# Module-level wrappers so cli.py and the tests keep working unchanged.
# Each call uses a fresh parser, so no state leaks between calls.
parse_date = BookingParser.parse_date
parse_time = BookingParser.parse_time
parse_request = BookingParser.parse_request


def parse_bookings(lines):
    return BookingParser().parse_lines(lines)


def load_bookings(path):
    return BookingParser().load(path)