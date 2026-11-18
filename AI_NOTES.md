# AI usage note

## Tools used and how

USING: CLAUDE SONNET 5.5

In order to have AI take the lead on this project I created a folder in Claude that was specific to only this project and connected my github repo. Because the folder is for Room Bookings it also can save the previous chats I had and would keep in its memory things we changed, added, and deleted. I have two chats with Claude related to this project in the folder.

- For the first initial push AI wrote the code base after I asked for a mock design and we went back and forth deciding on which files to add and why they were important to the code base. When I needed to fix or implemt little things such as the test it coded them for me. I also went back and asked it for a few changes when it came to parsing the command line arguments for users to check if a room was avaliable.
- After that it was just little comments about what we needed to change whether it was to make the User Experience better or because it got a specific file wrong or it wasn't testing properly.

- For the UI i specfied what look I wanted, in this case I wanted it to look like notion calendar so I told the AI to make it look like that and also highlight the bookings in RED if they have time conflicts. I asked for it to also show on the right side of the calendar which meeting ID's had time conflicts. I also wanted each room to have their own slot and color associated with the room it belongs to. Since this is for office use the calendar is shown from 07:00 to 18:00

## Moments the AI got something wrong

1. In the inital review which just consisted of the testing aspect, it did not write how to test the code properly. When running the unit tests it specificied to use “python -m unittests” when it should have been “python3 -m unittests”
2. When I was reading parsing.py I did notice that it was not formatting the columns correctly when it came to seeing how the start and end times were being parsed so I told the chat how to fix it and then I reviewed it.
3. When I was looking over the code base I did see that it had two `__init.py` files and I wasn't sure what they were for since they were both empty. There was one in room_checker and another in tests so I asked the chat what they were for and it did realize that the one in room_checker was not needed.

## Part I wrote or rewrote myself

<u>Things the AI messed up on:</u>

- I created and edited the `parsing.py` since the code was just messy and created a bunch of functions where we could create a class in order to keep everything organized when it later gets accessed in `conflicts.py` to parse through the CSV file and getting the columns
- I did not like the way the AI was taking in the command line arguments when we try to see whether a room is available so I changed the function **build_parser** in `CLI.py` to read our arguments closer to what they would look like as if they were coming from the csv file so it went from looking like:
  - python3 -m room_checker check bookings.csv --room "Board Room" --date 2026-11-12 --start 10:10 --end 11:00
    to looking like
  - python3 -m room_checker check bookings.csv "Board Room" 2026-11-12 10:10 11:00
    because it should be pretty straight forward when trying to see if the room is available
