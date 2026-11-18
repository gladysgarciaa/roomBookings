"""Busiest-room statistics."""

from collections import defaultdict


def busiest_rooms(bookings):
    """Return one (date, room, total_minutes, booking_count) per date, sorted by date.

    Busiest = most booked minutes that day. Ties: more bookings, then room name.
    """
    totals = defaultdict(lambda: [0, 0])  # (date, room) -> [minutes, count]
    for b in bookings:
        entry = totals[(b.date, b.room)]
        entry[0] += b.end - b.start
        entry[1] += 1

    best = {}  # date -> (sort_key, room, minutes, count)
    for (date, room), (minutes, count) in totals.items():
        key = (-minutes, -count, room)
        if date not in best or key < best[date][0]:
            best[date] = (key, room, minutes, count)

    return [(d, best[d][1], best[d][2], best[d][3]) for d in sorted(best)]