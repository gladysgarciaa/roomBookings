import contextlib
import io
import os
import unittest

from room_checker.cli import main

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "bookings.csv")


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(list(argv))
        except SystemExit as exit_:  # argparse errors
            code = exit_.code
    return code, out.getvalue(), err.getvalue()


def check(room, date, start, end):
    return run("check", SAMPLE, "--room", room, "--date", date, "--start", start, "--end", end)


class ReportTests(unittest.TestCase):
    def test_sample_file_report(self):
        code, out, _ = run("report", SAMPLE)
        self.assertEqual(code, 0)
        self.assertEqual(
            out,
            "Conflict: #1 and #2\n"
            "Conflict: #2 and #3\n"
            "Conflict: #7 and #8\n"
            "Conflict: #7 and #9\n"
            "Conflict: #7 and #10\n"
            "Conflict: #8 and #10\n"
            "Invalid: #12 (end is not after start)\n",
        )

    def test_missing_file(self):
        code, out, err = run("report", "does_not_exist.csv")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("Error", err)


class CheckTests(unittest.TestCase):
    def test_available(self):
        self.assertEqual(check("Huddle A", "2026-11-12", "15:00", "16:00")[1], "Available\n")

    def test_cancelled_booking_does_not_block(self):
        # #4 (13:00-14:00) is cancelled, only #5 blocks
        self.assertEqual(
            check("Huddle A", "2026-11-12", "13:00", "14:00")[1],
            "Not available: conflicts with #5\n",
        )

    def test_board_room_cleaning_applies_to_request(self):
        self.assertEqual(
            check("Board Room", "2026-11-12", "10:10", "10:20")[1],
            "Not available: conflicts with #1, #2, #3\n",
        )
        self.assertEqual(check("board room", "2026-11-12", "11:15", "12:00")[1], "Available\n")
        self.assertIn("#3", check("board room", "2026-11-12", "11:14", "12:00")[1])

    def test_bad_request_is_a_clean_error(self):
        code, out, err = check("Huddle A", "2026-11-12", "25:00", "26:00")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("Error", err)


if __name__ == "__main__":
    unittest.main()
