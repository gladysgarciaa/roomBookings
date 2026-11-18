# Room Booking Checker

Finds double-booked meeting rooms in a bookings CSV and checks whether a room is free.
Python 3.8+, standard library only.

## Install

Nothing to install. Run all commands from this folder.

## Run

```
- running the report on what rooms have the time conflicts:
python3 -m room_checker.main report bookings.csv

- "Adding" a new booking to see whether the room is avaliable at that time :
python3 -m room_checker check bookings.csv "Board Room" 2026-11-12 10:10 11:00
```

- `report` prints conflicts (sorted by first ID, then second; lower ID first), then invalid rows sorted by ID. Prints nothing if there are none.
- `check` prints `Available`, or `Not available: conflicts with #1, #2`.
- Exit code 0 on success, 2 if the file is unreadable, the header is missing columns, or the request is malformed (message on stderr).

## Test

```
python3 run_tests.py
```

## Layout

| File                        | Purpose                                                                   |
| --------------------------- | ------------------------------------------------------------------------- |
| `room_checker/config.py`    | Cleaning minutes per (normalized) room. Board Room = 15.                  |
| `room_checker/models.py`    | `Booking` and `InvalidRow` dataclasses. Times are minutes since midnight. |
| `room_checker/parsing.py`   | CSV to valid bookings + invalid rows; request validation.                 |
| `room_checker/conflicts.py` | Overlap rule, conflict report, availability check.                        |
| `room_checker/report.py`    | Output formatting.                                                        |
| `room_checker/cli.py`       | Argument parsing; wires everything together.                              |
| `room_checker/__main__.py`  | Makes `python3 -m room_checker` work.                                     |

## How the rules are implemented

- Two bookings clash if same room key, same date, `a.start < b.end + cleaning(b)` and `b.start < a.end + cleaning(a)`. Back-to-back is therefore fine, except in rooms with cleaning time.
- Availability wraps the request as a temporary booking and uses the same `overlaps` function, so the cleaning rule applies to the requested slot too.
- Room key = `strip().lower()` only; inner spaces are not collapsed.

## Assumptions

- Cleaning time applies to every Board Room pair, so #2 (ends 10:30) and #3 (starts 10:30) conflict in the sample data.
- Cancelled rows are ignored completely, even if otherwise malformed (not reported as invalid).
- A status other than confirmed/cancelled (case and outer spaces ignored) is invalid.
- Times may be `9:15` or `09:15`; `24:00`, `12:60`, `09:30:00` are invalid.
- A later row with an already-used ID is invalid ("duplicate id"); the first one is kept.
- Rows with a missing/non-numeric ID are reported as `Invalid: row N (...)` (N = file line number) and listed after rows with IDs.
- Blank lines are skipped. Header names are matched ignoring case/spaces; column order doesn't matter.
- For `check`, invalid CSV rows are skipped just like in `report`.

## Stretch Goal

- We want to show the busiest room on each date so we had to create a new file `stats.py`
  that reports how many minutes and meetings a room has booked.

to run the busiest day report

```
python3 -m room_checker busiest bookings.csv
```
