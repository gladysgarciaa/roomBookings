import datetime
import unittest

from room_checker.conflicts import (
    check_availability,
    effective_end,
    find_conflicts,
    normalize_room,
    overlaps,
)
from room_checker.models import Booking
from room_checker.parsing import parse_bookings

# hardcoding the dates need to make it so it parses throughthe file

D1 = datetime.date(2026, 11, 12)
D2 = datetime.date(2026, 11, 13)


def t(text):
    h, m = text.split(":")
    return int(h) * 60 + int(m)


def mk(id, room, start, end, date=D1):
    return Booking(id, normalize_room(room), date, t(start), t(end))


class NormalizeTests(unittest.TestCase):
    def test_case_and_outer_spaces(self):
        self.assertEqual(normalize_room(" Board Room "), normalize_room("board room"))
        self.assertNotEqual(normalize_room("Board  Room"), normalize_room("board room"))


class OverlapTests(unittest.TestCase):
    def test_overlap_same_room(self):
        self.assertTrue(overlaps(mk(1, "A", "09:00", "10:00"), mk(2, "A", "09:30", "10:30")))

    def test_containment(self):
        self.assertTrue(overlaps(mk(1, "A", "08:00", "12:00"), mk(2, "A", "09:00", "09:30")))
        self.assertTrue(overlaps(mk(2, "A", "09:00", "09:30"), mk(1, "A", "08:00", "12:00")))

    def test_identical_times(self):
        self.assertTrue(overlaps(mk(1, "A", "09:00", "10:00"), mk(2, "A", "09:00", "10:00")))

    def test_back_to_back_is_fine(self):
        self.assertFalse(overlaps(mk(1, "Huddle A", "09:00", "10:00"), mk(2, "Huddle A", "10:00", "11:00")))
        self.assertFalse(overlaps(mk(2, "Huddle A", "10:00", "11:00"), mk(1, "Huddle A", "09:00", "10:00")))

    def test_different_room_or_date(self):
        self.assertFalse(overlaps(mk(1, "A", "09:00", "10:00"), mk(2, "B", "09:00", "10:00")))
        self.assertFalse(overlaps(mk(1, "A", "09:00", "10:00"), mk(2, "A", "09:00", "10:00", D2)))

    def test_room_names_match_ignoring_case_and_spaces(self):
        self.assertTrue(overlaps(mk(1, "Board Room", "09:00", "10:00"), mk(2, " board ROOM ", "09:30", "10:30")))


class CleaningTimeTests(unittest.TestCase):
    def test_effective_end(self):
        self.assertEqual(effective_end(mk(1, "Board Room", "09:00", "10:00")), t("10:15"))
        self.assertEqual(effective_end(mk(1, "Training", "09:00", "10:00")), t("10:00"))

    def test_board_room_back_to_back_conflicts(self):
        self.assertTrue(overlaps(mk(1, "Board Room", "09:00", "10:00"), mk(2, "Board Room", "10:00", "11:00")))

    def test_board_room_gap_boundaries(self):
        first = mk(1, "Board Room", "09:00", "10:00")
        self.assertTrue(overlaps(first, mk(2, "Board Room", "10:14", "11:00")))
        self.assertFalse(overlaps(first, mk(2, "Board Room", "10:15", "11:00")))
        self.assertFalse(overlaps(mk(2, "Board Room", "10:15", "11:00"), first))

    def test_other_rooms_have_no_cleaning_time(self):
        self.assertFalse(overlaps(mk(1, "Huddle A", "09:00", "10:00"), mk(2, "Huddle A", "10:01", "11:00")))
        self.assertFalse(overlaps(mk(1, "Training", "09:00", "10:00"), mk(2, "Training", "10:00", "11:00")))


class FindConflictsTests(unittest.TestCase):
    def test_pairs_sorted_lower_id_first(self):
        bookings = [
            mk(9, "A", "09:00", "10:00"),
            mk(3, "A", "09:30", "10:30"),
            mk(5, "A", "09:45", "10:15"),
        ]
        self.assertEqual(find_conflicts(bookings), [(3, 5), (3, 9), (5, 9)])

    def test_no_conflicts(self):
        self.assertEqual(find_conflicts([mk(1, "A", "09:00", "10:00"), mk(2, "A", "10:00", "11:00")]), [])

    def test_cancelled_and_invalid_are_excluded_via_parsing(self):
        text = (
            "id,room,date,start,end,status\n"
            "1,A,2026-11-12,09:00,10:00,confirmed\n"
            "2,A,2026-11-12,09:00,10:00,cancelled\n"
            "3,A,2026-11-12,09:00,10:00,confirmed\n"
            "4,A,2026-11-12,10:00,09:00,confirmed\n"
        )
        bookings, _ = parse_bookings(text.splitlines(keepends=True))
        self.assertEqual(find_conflicts(bookings), [(1, 3)])


class AvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.bookings = [
            mk(1, "Board Room", "09:00", "10:00"),
            mk(2, "Huddle A", "09:00", "10:00"),
        ]

    def check(self, room, start, end, date=D1):
        return check_availability(self.bookings, room, date, t(start), t(end))

    def test_available(self):
        self.assertEqual(self.check("Huddle A", "10:00", "11:00"), [])
        self.assertEqual(self.check("Huddle A", "09:00", "10:00", D2), [])

    def test_not_available_lists_ids(self):
        self.assertEqual(self.check("huddle a ", "09:30", "10:30"), [2])

    def test_board_room_request_after_meeting_needs_cleaning_gap(self):
        self.assertEqual(self.check("Board Room", "10:10", "11:00"), [1])
        self.assertEqual(self.check("Board Room", "10:15", "11:00"), [])

    def test_board_room_request_before_meeting_needs_cleaning_gap(self):
        self.assertEqual(self.check("Board Room", "08:00", "08:45"), [])
        self.assertEqual(self.check("Board Room", "08:00", "08:46"), [1])


if __name__ == "__main__":
    unittest.main()
