"""Turn results into the exact output text."""


def format_report(conflicts, invalid_rows):
    """Conflicts (already sorted), then invalid rows sorted by ID.

    Rows whose id is unreadable have no ID to sort by, so they go last,
    ordered by line number.
    """
    lines = ["Conflict: #%d and #%d" % pair for pair in conflicts]
    ordered = sorted(
        invalid_rows,
        key=lambda r: (r.id is None, r.id if r.id is not None else 0, r.row_number),
    )
    for row in ordered:
        label = "#%d" % row.id if row.id is not None else "row %d" % row.row_number
        lines.append("Invalid: %s (%s)" % (label, row.reason))
    return "\n".join(lines)


def format_availability(conflicting_ids):
    if not conflicting_ids:
        return "Available"
    return "Not available: conflicts with " + ", ".join("#%d" % i for i in conflicting_ids)
