# AI usage note

## Tools used and how

- For the first initial push AI wrote the code base after I asked for a mock design and we went back anf forth deciding on which files to add and why they were important to the code base.

## Moments the AI got something wrong

1. In the inital review which just consisted of the testing aspect, it did not write how to test the code properly. When running the unit tests it specificied to use “python -m unittests” when it should have been “python3 -m unittests”

## Part I wrote or rewrote myself

<u>Things the AI messed up on:</u>

- I created and edited the **parsing.py** since the code was just messy and created a bunch of functions where we could create a class in order to keep everything organized when it later gets accessed in conflicts.py to parse through the CSV file and getting the columns
- I did not like the way the AI was taking in the command line arguments when we try to see whether a room is available so I changed the function **build_parser** in **_CLI.py_** to read our arguments closer to what they would look like as if they were coming from the csv file so it went from looking like:
  - python3 -m room_checker check bookings.csv --room "Board Room" --date 2026-11-12 --start 10:10 --end 11:00
  to looking like
  - python3 -m room_checker check bookings.csv "Board Room" 2026-11-12 10:10 11:00
  because it should be pretty straight forward when trying to see if the room is available
