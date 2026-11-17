import datetime
import os
import tempfile
import unittest

from room_checker.parsing import (
    MissingColumnsError,
    load_bookings,
    parse_bookings,
    parse_request,
    parse_time,
)

HEADER = "id,room,date,start,end,status\n"


def parse(*rows):
    return parse_bookings((HEADER + "\n".join(rows) + "\n").splitlines(keepends=True))


class ParseTimeTests(unittest.TestCase):
    def test_valid_times(self):
        self.assertEqual(parse_time("09:15"), 555)
        self.assertEqual(parse_time("9:15"), 555)
        self.assertEqual(parse_time(" 23:59 "), 23 * 60 + 59)
        self.assertEqual(parse_time("00:00"), 0)

    def test_invalid_times(self):
        for bad in ["25:00", "24:00", "12:60", "abc", "9:5", "", "9", "09:30:00", "9.30"]:
            with self.assertRaises(ValueError, msg=bad):
                parse_time(bad)


class ParseBookingsTests(unittest.TestCase):
    def test_valid_row(self):
        bookings, invalid = parse("1,Board Room,2026-11-12,09:00,10:00,confirmed")
        self.assertEqual(invalid, [])
        b = bookings[0]
        self.assertEqual((b.id, b.room, b.start, b.end), (1, "board room", 540, 600))
        self.assertEqual(b.date, datetime.date(2026, 11, 12))

    def test_room_normalized_case_and_outer_spaces_only(self):
        bookings, _ = parse(
            "1, Board Room ,2026-11-12,09:00,10:00,confirmed",
            "2,BOARD ROOM,2026-11-12,11:00,12:00,confirmed",
            "3,Board  Room,2026-11-12,13:00,14:00,confirmed",
        )
        self.assertEqual(bookings[0].room, bookings[1].room)
        self.assertNotEqual(bookings[0].room, bookings[2].room)  # inner spaces kept

    def test_cancelled_ignored_in_any_capitalization(self):
        bookings, invalid = parse(
            "1,A,2026-11-12,09:00,10:00,cancelled",
            "2,A,2026-11-12,09:00,10:00,CANCELLED",
            "3,A,2026-11-12,09:00,10:00, Cancelled ",
        )
        self.assertEqual((bookings, invalid), ([], []))

    def test_cancelled_row_is_ignored_even_if_malformed(self):
        bookings, invalid = parse("4,,not-a-date,xx,yy,cancelled")
        self.assertEqual((bookings, invalid), ([], []))

    def test_status_case_insensitive_for_confirmed(self):
        bookings, _ = parse("1,A,2026-11-12,09:00,10:00, CONFIRMED ")
        self.assertEqual(len(bookings), 1)

    def test_missing_values(self):
        bookings, invalid = parse("5,,2026-11-12,09:00,10:00,confirmed")
        self.assertEqual(bookings, [])
        self.assertEqual(invalid[0].id, 5)
        self.assertIn("missing", invalid[0].reason)

    def test_short_row_does_not_crash(self):
        bookings, invalid = parse("6,Room,2026-11-12")
        self.assertEqual(bookings, [])
        self.assertEqual(invalid[0].id, 6)

    def test_bad_times_dates(self):
        rows = [
            "1,A,2026-11-12,25:00,26:00,confirmed",
            "2,A,2026-11-12,abc,10:00,confirmed",
            "3,A,2026-11-12,09:00,9:5,confirmed",
            "4,A,2026-13-01,09:00,10:00,confirmed",
            "5,A,2026-02-30,09:00,10:00,confirmed",
            "6,A,12/11/2026,09:00,10:00,confirmed",
        ]
        bookings, invalid = parse(*rows)
        self.assertEqual(bookings, [])
        self.assertEqual([r.id for r in invalid], [1, 2, 3, 4, 5, 6])

    def test_end_not_after_start(self):
        bookings, invalid = parse(
            "1,A,2026-11-12,10:00,10:00,confirmed",
            "2,A,2026-11-12,15:00,14:00,confirmed",
        )
        self.assertEqual(bookings, [])
        self.assertTrue(all("end is not after start" in r.reason for r in invalid))

    def test_unreadable_id(self):
        bookings, invalid = parse(
            "abc,A,2026-11-12,09:00,10:00,confirmed",
            "1.5,A,2026-11-12,09:00,10:00,confirmed",
            "-3,A,2026-11-12,09:00,10:00,confirmed",
        )
        self.assertEqual(bookings, [])
        self.assertEqual(len(invalid), 3)
        self.assertTrue(all(r.id is None for r in invalid))

    def test_unknown_status_is_invalid(self):
        _, invalid = parse("1,A,2026-11-12,09:00,10:00,pending")
        self.assertEqual(invalid[0].id, 1)
        self.assertIn("status", invalid[0].reason)

    def test_duplicate_id_second_is_invalid(self):
        bookings, invalid = parse(
            "1,A,2026-11-12,09:00,10:00,confirmed",
            "1,B,2026-11-12,09:00,10:00,confirmed",
        )
        self.assertEqual(len(bookings), 1)
        self.assertEqual(invalid[0].reason, "duplicate id")

    def test_bad_row_does_not_stop_processing(self):
        bookings, invalid = parse(
            "1,A,2026-11-12,09:00,10:00,confirmed",
            "2,A,oops,09:00,10:00,confirmed",
            "3,A,2026-11-12,11:00,12:00,confirmed",
        )
        self.assertEqual([b.id for b in bookings], [1, 3])
        self.assertEqual([r.id for r in invalid], [2])

    def test_blank_lines_ignored(self):
        bookings, invalid = parse("", "1,A,2026-11-12,09:00,10:00,confirmed", "")
        self.assertEqual((len(bookings), invalid), (1, []))

    def test_header_problems(self):
        with self.assertRaises(MissingColumnsError):
            parse_bookings([])
        with self.assertRaises(MissingColumnsError):
            parse_bookings(["id,room,date\n"])

    def test_load_bookings_handles_bom_and_bad_bytes(self):
        content = b"\xef\xbb\xbf" + HEADER.encode() + b"1,Caf\xe9,2026-11-12,09:00,10:00,confirmed\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "b.csv")
            with open(path, "wb") as handle:
                handle.write(content)
            bookings, invalid = load_bookings(path)
        self.assertEqual((len(bookings), invalid), (1, []))


class ParseRequestTests(unittest.TestCase):
    def test_valid(self):
        room, date, start, end = parse_request(" Board Room ", "2026-11-12", "9:00", "10:30")
        self.assertEqual((room, start, end), ("board room", 540, 630))

    def test_invalid(self):
        for args in [
            ("", "2026-11-12", "09:00", "10:00"),
            ("A", "nope", "09:00", "10:00"),
            ("A", "2026-11-12", "25:00", "10:00"),
            ("A", "2026-11-12", "09:00", "xx"),
            ("A", "2026-11-12", "10:00", "10:00"),
        ]:
            with self.assertRaises(ValueError, msg=str(args)):
                parse_request(*args)


if __name__ == "__main__":
    unittest.main()
