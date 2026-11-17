"""Core logic: overlap rules, conflict report and availability check."""

from collections import defaultdict
from itertools import combinations

from .config import cleaning_minutes
from .models import Booking


def normalize_room(name):
    """Rooms match ignoring case and outer spaces only (inner spaces are kept)."""
    return name.strip().lower()


def effective_end(booking):
    """End of the booking plus the cleaning time its room needs."""
    return booking.end + cleaning_minutes(booking.room)


def overlaps(a, b):
    """True if the bookings are the same room and date and their times clash.

    Back-to-back is fine (strict < comparisons). The cleaning time is added
    to the end of BOTH bookings, so it applies whichever one comes first.
    """
    return (
        a.room == b.room
        and a.date == b.date
        and a.start < effective_end(b)
        and b.start < effective_end(a)
    )


def find_conflicts(bookings):
    """Return sorted (lower_id, higher_id) pairs of conflicting bookings."""
    groups = defaultdict(list)
    for booking in bookings:
        groups[(booking.room, booking.date)].append(booking)

    pairs = []
    for group in groups.values():
        group.sort(key=lambda b: b.id)
        for a, b in combinations(group, 2):
            if overlaps(a, b):
                pairs.append((a.id, b.id))
    return sorted(pairs)


def check_availability(bookings, room, date, start, end):
    """Return sorted IDs of bookings the requested slot would conflict with.

    An empty list means the room is available. The request is wrapped in a
    temporary Booking so it goes through exactly the same overlap rule
    (including cleaning time) as the report.
    """
    request = Booking(id=0, room=normalize_room(room), date=date, start=start, end=end)
    return sorted(b.id for b in bookings if overlaps(b, request))
