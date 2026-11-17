import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Booking:
    id: int
    room: str            # normalized key: stripped and lower-case
    date: datetime.date
    start: int           # minutes since midnight
    end: int             # minutes since midnight


@dataclass(frozen=True)
class InvalidRow:
    row_number: int      # line number in the CSV file
    id: Optional[int]    # None when the id itself is missing or unreadable
    reason: str
