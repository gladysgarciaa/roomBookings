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

# hardcoding the dates need to make it so it parses through the file

D1 = datetime.date(2026, 11, 12)
D2 = datetime.date(2026, 11, 13)


def t(text):
    h, m = text.split(":")
    return int(h) * 60 + int(m)


def mk(id, room, start, end, date=D1):
    return Booking(id, normalize_room(room), date, t(start), t(end))


class NormalizeTests(unittest.TestCase):
    def test_case_and_outer_spaces(self):
        """
        Input:    " Board Room " vs "board room", and "Board  Room" (two inner spaces)
        Expected: the first two match (case and outer spaces are ignored);
                  the two-inner-space version does NOT match
        """
        self.assertEqual(normalize_room(" Board Room "), normalize_room("board room"))
        self.assertNotEqual(normalize_room("Board  Room"), normalize_room("board room"))


class OverlapTests(unittest.TestCase):
    def test_overlap_same_room(self):
        """
        Input:    room A 09:00-10:00 and room A 09:30-10:30
        Expected: they overlap
        """
        self.assertTrue(overlaps(mk(1, "A", "09:00", "10:00"), mk(2, "A", "09:30", "10:30")))

    def test_containment(self):
        """
        Input:    room A 08:00-12:00 and room A 09:00-09:30 (one inside the other),
                  checked in both argument orders
        Expected: they overlap either way
        """
        self.assertTrue(overlaps(mk(1, "A", "08:00", "12:00"), mk(2, "A", "09:00", "09:30")))
        self.assertTrue(overlaps(mk(2, "A", "09:00", "09:30"), mk(1, "A", "08:00", "12:00")))

    def test_identical_times(self):
        """
        Input:    two room A bookings, both 09:00-10:00
        Expected: they overlap
        """
        self.assertTrue(overlaps(mk(1, "A", "09:00", "10:00"), mk(2, "A", "09:00", "10:00")))

    def test_back_to_back_is_fine(self):
        """
        Input:    Huddle A 09:00-10:00 and Huddle A 10:00-11:00, both argument orders
        Expected: no overlap (one ends exactly when the other starts)
        """
        self.assertFalse(overlaps(mk(1, "Huddle A", "09:00", "10:00"), mk(2, "Huddle A", "10:00", "11:00")))
        self.assertFalse(overlaps(mk(2, "Huddle A", "10:00", "11:00"), mk(1, "Huddle A", "09:00", "10:00")))

    def test_different_room_or_date(self):
        """
        Input:    same times 09:00-10:00, but (a) room A vs room B,
                  (b) room A on 2026-11-12 vs room A on 2026-11-13
        Expected: no overlap in either case
        """
        self.assertFalse(overlaps(mk(1, "A", "09:00", "10:00"), mk(2, "B", "09:00", "10:00")))
        self.assertFalse(overlaps(mk(1, "A", "09:00", "10:00"), mk(2, "A", "09:00", "10:00", D2)))

    def test_room_names_match_ignoring_case_and_spaces(self):
        """
        Input:    "Board Room" 09:00-10:00 and " board ROOM " 09:30-10:30
        Expected: treated as the same room, so they overlap
        """
        self.assertTrue(overlaps(mk(1, "Board Room", "09:00", "10:00"), mk(2, " board ROOM ", "09:30", "10:30")))


class CleaningTimeTests(unittest.TestCase):
    def test_effective_end(self):
        """
        Input:    a 09:00-10:00 booking in Board Room, and one in Training
        Expected: Board Room's effective end is 10:15 (15 min cleaning);
                  Training's stays 10:00 (no cleaning time)
        """
        self.assertEqual(effective_end(mk(1, "Board Room", "09:00", "10:00")), t("10:15"))
        self.assertEqual(effective_end(mk(1, "Training", "09:00", "10:00")), t("10:00"))

    def test_board_room_back_to_back_conflicts(self):
        """
        Input:    Board Room 09:00-10:00 and Board Room 10:00-11:00
        Expected: they conflict (cleaning needs until 10:15)
        """
        self.assertTrue(overlaps(mk(1, "Board Room", "09:00", "10:00"), mk(2, "Board Room", "10:00", "11:00")))

    def test_board_room_gap_boundaries(self):
        """
        Input:    Board Room 09:00-10:00, then a second booking starting at
                  10:14 (a), and one starting at 10:15 (b, checked both orders)
        Expected: 10:14 conflicts (one minute short of cleaning);
                  10:15 is fine in both argument orders
        """
        first = mk(1, "Board Room", "09:00", "10:00")
        self.assertTrue(overlaps(first, mk(2, "Board Room", "10:14", "11:00")))
        self.assertFalse(overlaps(first, mk(2, "Board Room", "10:15", "11:00")))
        self.assertFalse(overlaps(mk(2, "Board Room", "10:15", "11:00"), first))

    def test_other_rooms_have_no_cleaning_time(self):
        """
        Input:    Huddle A 09:00-10:00 then 10:01-11:00;
                  Training 09:00-10:00 then 10:00-11:00
        Expected: neither pair overlaps (only Board Room needs cleaning time)
        """
        self.assertFalse(overlaps(mk(1, "Huddle A", "09:00", "10:00"), mk(2, "Huddle A", "10:01", "11:00")))
        self.assertFalse(overlaps(mk(1, "Training", "09:00", "10:00"), mk(2, "Training", "10:00", "11:00")))


class FindConflictsTests(unittest.TestCase):
    def test_pairs_sorted_lower_id_first(self):
        """
        Input:    room A bookings #9 (09:00-10:00), #3 (09:30-10:30), #5 (09:45-10:15),
                  given in that order
        Expected: [(3, 5), (3, 9), (5, 9)] (each pair lower ID first, list sorted)
        """
        bookings = [
            mk(9, "A", "09:00", "10:00"),
            mk(3, "A", "09:30", "10:30"),
            mk(5, "A", "09:45", "10:15"),
        ]
        self.assertEqual(find_conflicts(bookings), [(3, 5), (3, 9), (5, 9)])

    def test_no_conflicts(self):
        """
        Input:    room A 09:00-10:00 and room A 10:00-11:00
        Expected: [] (back-to-back is not a conflict)
        """
        self.assertEqual(find_conflicts([mk(1, "A", "09:00", "10:00"), mk(2, "A", "10:00", "11:00")]), [])

    def test_cancelled_and_invalid_are_excluded_via_parsing(self):
        """
        Input:    CSV with #1 and #3 confirmed at 09:00-10:00, #2 cancelled in the
                  same slot, and #4 invalid (10:00-09:00)
        Expected: [(1, 3)] only; #2 and #4 never become bookings
        """
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
        """
        Setup:    #1 Board Room 09:00-10:00, #2 Huddle A 09:00-10:00 on 2026-11-12
        Input:    Huddle A 10:00-11:00 on 2026-11-12; Huddle A 09:00-10:00 on 2026-11-13
        Expected: [] for both (back-to-back is fine; different date is free)
        """
        self.assertEqual(self.check("Huddle A", "10:00", "11:00"), [])
        self.assertEqual(self.check("Huddle A", "09:00", "10:00", D2), [])

    def test_not_available_lists_ids(self):
        """
        Setup:    #1 Board Room 09:00-10:00, #2 Huddle A 09:00-10:00
        Input:    "huddle a " (lowercase, trailing space) 09:30-10:30
        Expected: [2] (room name matching is forgiving)
        """
        self.assertEqual(self.check("huddle a ", "09:30", "10:30"), [2])

    def test_board_room_request_after_meeting_needs_cleaning_gap(self):
        """
        Setup:    #1 Board Room 09:00-10:00 (cleaning until 10:15)
        Input:    Board Room request at 10:10-11:00, then 10:15-11:00
        Expected: 10:10 -> [1] (too soon); 10:15 -> [] (cleaning finished)
        """
        self.assertEqual(self.check("Board Room", "10:10", "11:00"), [1])
        self.assertEqual(self.check("Board Room", "10:15", "11:00"), [])

    def test_board_room_request_before_meeting_needs_cleaning_gap(self):
        """
        Setup:    #1 Board Room 09:00-10:00
        Input:    Board Room request at 08:00-08:45, then 08:00-08:46
        Expected: 08:45 -> [] (cleaning ends exactly at 09:00);
                  08:46 -> [1] (cleaning would run into the 09:00 meeting)
        """
        self.assertEqual(self.check("Board Room", "08:00", "08:45"), [])
        self.assertEqual(self.check("Board Room", "08:00", "08:46"), [1])


if __name__ == "__main__":
    unittest.main()
