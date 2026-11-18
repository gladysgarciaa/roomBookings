"""Per-room settings. This is the only place the cleaning-time rule lives.

Keys are NORMALIZED room names (stripped, lower-case). Rooms not listed here
need no cleaning time.
"""
# Hashmap for adding cleaning minutes to different rooms if needed
CLEANING_MINUTES = {
    "board room": 15,
}

DEFAULT_CLEANING_MINUTES = 0


def cleaning_minutes(room_key):
    """Minutes of cleaning needed after every meeting in this (normalized) room."""
    return CLEANING_MINUTES.get(room_key, DEFAULT_CLEANING_MINUTES)
