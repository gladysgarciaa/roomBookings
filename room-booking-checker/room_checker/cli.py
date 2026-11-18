"""Command-line entry point: wires parsing, conflicts and report together."""

import argparse
import sys

from .conflicts import check_availability, find_conflicts
from .parsing import MissingColumnsError, load_bookings, parse_request
from .report import format_availability, format_busiest, format_report
from .stats import busiest_rooms

def build_parser():
    parser = argparse.ArgumentParser(prog="room_checker", description="Room booking checker")
    sub = parser.add_subparsers(dest="command", required=True)

    report = sub.add_parser("report", help="list conflicts and invalid rows")
    report.add_argument("csv_file")

    busiest = sub.add_parser("busiest", help="show the busiest room on each date")
    busiest.add_argument("csv_file")

    check = sub.add_parser("check", help="check whether a room is free")
    check.add_argument("csv_file")
    check.add_argument("room")
    check.add_argument("date", help="YYYY-MM-DD")
    check.add_argument("start", help="HH:MM (24-hour)")
    check.add_argument("end", help="HH:MM (24-hour)")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    request = None
    if args.command == "check":
        try:
            request = parse_request(args.room, args.date, args.start, args.end)
        except ValueError as err:
            print("Error: %s" % err, file=sys.stderr)
            return 2

    try:
        bookings, invalid = load_bookings(args.csv_file)
    except (OSError, MissingColumnsError) as err:
        print("Error: %s" % err, file=sys.stderr)
        return 2
    except Exception as err:  # e.g. csv.Error on a corrupt file
        print("Error: could not read file (%s)" % err, file=sys.stderr)
        return 2

    if args.command == "report":
        output = format_report(find_conflicts(bookings), invalid)
    elif args.command == "busiest":
        output = format_busiest(busiest_rooms(bookings))
    else:
        room, date, start, end = request
        output = format_availability(check_availability(bookings, room, date, start, end))

        
    if output:
        print(output)
    return 0
