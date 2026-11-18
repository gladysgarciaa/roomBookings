"""Read-only day-view calendar served on localhost (standard library only).

Run:  python -m room_checker.web bookings.csv [--port 8000]

All rules (validation, cancelled rows, cleaning time, conflicts) come from the
same functions the CLI uses; this file only reshapes the results for the page.
The CSV is re-read on every request, so edit it and refresh to see changes.
"""

import argparse
import datetime
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from .config import cleaning_minutes
from .conflicts import effective_end, find_conflicts
from .parsing import MissingColumnsError, load_bookings, parse_date

# No reds: red is reserved for conflicts.
PALETTE = ["#2563eb", "#0d9488", "#d97706", "#7c3aed", "#db2777", "#65a30d", "#0891b2", "#4f46e5"]
DEFAULT_START = 7 * 60
DEFAULT_END = 18 * 60


def build_day_view(bookings, invalid, day):
    """Everything the page needs to draw one day, as plain JSON-ready data."""
    partners = {}
    for a, b in find_conflicts(bookings):
        partners.setdefault(a, []).append(b)
        partners.setdefault(b, []).append(a)

    all_rooms = sorted({b.room for b in bookings})
    colors = {room: PALETTE[i % len(PALETTE)] for i, room in enumerate(all_rooms)}
    todays = sorted((b for b in bookings if b.date == day), key=lambda b: (b.start, b.id))
    today_ids = {b.id for b in todays}

    rooms = []
    for room in all_rooms:
        items, lane_ends = [], []
        for b in (x for x in todays if x.room == room):
            block_end = effective_end(b)
            for lane, last in enumerate(lane_ends):
                if last <= b.start:
                    lane_ends[lane] = block_end
                    break
            else:
                lane = len(lane_ends)
                lane_ends.append(block_end)
            items.append({
                "id": b.id,
                "start": b.start,
                "end": b.end,
                "cleaning": cleaning_minutes(b.room),
                "lane": lane,
                "conflict": b.id in partners,
                "with": sorted(partners.get(b.id, [])),
            })
        rooms.append({
            "name": room.title(),
            "color": colors[room],
            "lanes": max(len(lane_ends), 1),
            "bookings": items,
        })

    first = min([DEFAULT_START] + [b.start for b in todays])
    last = max([DEFAULT_END] + [effective_end(b) for b in todays])
    ordered = sorted(
        invalid, key=lambda r: (r.id is None, r.id if r.id is not None else 0, r.row_number)
    )
    return {
        "date": day.isoformat(),
        "start": first // 60 * 60,
        "end": min(-(-last // 60) * 60, 24 * 60),
        "rooms": rooms,
        "conflicts": [list(p) for p in find_conflicts(bookings) if p[0] in today_ids],
        "invalid": [
            {
                "label": "#%d" % r.id if r.id is not None else "row %d" % r.row_number,
                "reason": r.reason,
            }
            for r in ordered
        ],
    }


def day_payload(csv_path, date_text=None):
    """Return (http_status, data). Defaults to the earliest booking date."""
    try:
        bookings, invalid = load_bookings(csv_path)
    except (OSError, MissingColumnsError) as err:
        return 500, {"error": str(err)}
    except Exception as err:  # e.g. csv.Error on a corrupt file
        return 500, {"error": "could not read file (%s)" % err}

    if date_text:
        try:
            day = parse_date(date_text)
        except ValueError as err:
            return 400, {"error": "date '%s': %s" % (date_text, err)}
    elif bookings:
        day = min(b.date for b in bookings)
    else:
        day = datetime.date.today()
    return 200, build_day_view(bookings, invalid, day)


def make_handler(csv_path):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, body, content_type):
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/":
                self._send(200, PAGE, "text/html")
            elif url.path == "/api/day":
                date_text = parse_qs(url.query).get("date", [None])[0]
                status, data = day_payload(csv_path, date_text)
                self._send(status, json.dumps(data), "application/json")
            else:
                self._send(404, "Not found", "text/plain")

        def log_message(self, *args):  # keep the terminal quiet
            pass

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(prog="room_checker.web", description="Calendar view")
    parser.add_argument("csv_file")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    status, data = day_payload(args.csv_file)
    if status != 200:
        print("Error: %s" % data["error"], file=sys.stderr)
        return 2

    server = HTTPServer(("127.0.0.1", args.port), make_handler(args.csv_file))
    print("Calendar at http://127.0.0.1:%d  (Ctrl+C to stop)" % args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Room bookings</title>
<style>
:root{--bg:#fff;--fg:#1f2937;--muted:#6b7280;--line:#e5e7eb;--panel:#f9fafb;--bad:#dc2626}
@media (prefers-color-scheme: dark){
  :root{--bg:#111827;--fg:#e5e7eb;--muted:#9ca3af;--line:#374151;--panel:#1f2937;--bad:#f87171}}
*{box-sizing:border-box}
body{margin:0;font:14px/1.4 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
header{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:12px 16px;border-bottom:1px solid var(--line)}
h1{font-size:17px;margin:0 auto 0 0}
button,input{font:inherit;padding:4px 10px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--fg)}
button{cursor:pointer}
:focus-visible{outline:2px solid var(--fg);outline-offset:2px}
main{display:flex;gap:20px;padding:16px;align-items:flex-start;flex-wrap:wrap}
#cal{flex:1 1 560px;min-width:0;overflow-x:auto}
.grid{display:grid;grid-template-columns:48px repeat(var(--n),minmax(140px,1fr))}
.head{font-weight:600;padding:6px 8px;border-bottom:3px solid var(--c,transparent)}
.times{position:relative}
.tlabel{position:absolute;right:6px;font-size:11px;color:var(--muted);transform:translateY(-50%)}
.col{position:relative;border-left:1px solid var(--line);
  background-image:linear-gradient(var(--line) 1px,transparent 1px);background-size:100% 28px}
.booking{position:absolute;padding:3px 6px;overflow:hidden;border-radius:4px;border:1px solid var(--c);
  border-left-width:4px;background:color-mix(in srgb,var(--c) 18%,var(--bg))}
.booking .t{font-weight:600}
.booking .s{font-size:12px;color:var(--muted)}
.booking.bad{border:2px solid var(--bad);border-left-width:4px}
.booking.bad .t{color:var(--bad)}
.x{position:absolute;top:2px;right:4px;color:var(--bad);font-weight:700}
.clean{position:absolute;opacity:.55;
  background:repeating-linear-gradient(45deg,var(--c) 0 3px,transparent 3px 7px)}
aside{flex:0 1 260px;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 14px}
aside h2{font-size:14px;margin:0 0 6px}
aside ul{margin:0 0 14px;padding-left:18px}
.bad-text{color:var(--bad)}
.key{display:flex;gap:14px;flex-wrap:wrap;color:var(--muted);font-size:12px;margin-top:10px}
.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;background:var(--c)}
#err{color:var(--bad);padding:16px}
</style></head><body>
<header>
  <h1>Room bookings</h1>
  <button id="prev" aria-label="Previous day">&lsaquo;</button>
  <input type="date" id="date" aria-label="Date">
  <button id="next" aria-label="Next day">&rsaquo;</button>
</header>
<div id="err" hidden></div>
<main>
  <section id="cal"></section>
  <aside>
    <h2>Conflicts</h2><ul id="conflicts"></ul>
    <h2>Invalid rows</h2><ul id="invalid"></ul>
    <div class="key">
      <span class="bad-text">&#10005; red = conflict</span>
      <span>hatched = cleaning time</span>
    </div>
  </aside>
</main>
<script>
const H = 56; // pixels per hour
const $ = id => document.getElementById(id);
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
};
const fmt = m => String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0');

async function load(date) {
  const res = await fetch('/api/day' + (date ? '?date=' + encodeURIComponent(date) : ''));
  const data = await res.json();
  $('err').hidden = res.ok;
  if (!res.ok) { $('err').textContent = 'Error: ' + data.error; return; }
  render(data);
}

function shift(days) {
  const d = new Date($('date').value + 'T00:00:00Z');
  if (isNaN(d)) return;
  d.setUTCDate(d.getUTCDate() + days);
  load(d.toISOString().slice(0, 10));
}

function listInto(id, items, emptyText) {
  const ul = $(id);
  ul.replaceChildren();
  if (!items.length) ul.appendChild(el('li', '', emptyText));
  items.forEach(t => ul.appendChild(el('li', '', t)));
}

function render(d) {
  $('date').value = d.date;
  const total = (d.end - d.start) / 60 * H;
  const grid = el('div', 'grid');
  grid.style.setProperty('--n', d.rooms.length);
  grid.appendChild(el('div', 'head'));
  d.rooms.forEach(r => {
    const h = el('div', 'head', r.name);
    h.style.setProperty('--c', r.color);
    grid.appendChild(h);
  });
  const times = el('div', 'times');
  times.style.height = total + 'px';
  for (let m = d.start; m <= d.end; m += 60) {
    const l = el('div', 'tlabel', fmt(m));
    l.style.top = ((m - d.start) / 60 * H) + 'px';
    times.appendChild(l);
  }
  grid.appendChild(times);

  d.rooms.forEach(r => {
    const col = el('div', 'col');
    col.style.height = total + 'px';
    col.style.setProperty('--c', r.color);
    r.bookings.forEach(b => {
      const left = b.lane / r.lanes * 100 + '%', width = 100 / r.lanes + '%';
      if (b.cleaning) {
        const c = el('div', 'clean');
        c.style.cssText = 'top:' + ((b.end - d.start) / 60 * H) + 'px;height:' + (b.cleaning / 60 * H) +
          'px;left:' + left + ';width:' + width;
        col.appendChild(c);
      }
      const e = el('div', 'booking' + (b.conflict ? ' bad' : ''));
      e.style.cssText = 'top:' + ((b.start - d.start) / 60 * H) + 'px;height:' + ((b.end - b.start) / 60 * H) +
        'px;left:' + left + ';width:' + width;
      e.appendChild(el('div', 't', '#' + b.id));
      e.appendChild(el('div', 's', fmt(b.start) + '\\u2013' + fmt(b.end)));
      if (b.conflict) e.appendChild(el('span', 'x', '\\u2715'));
      e.title = '#' + b.id + ' ' + r.name + ' ' + fmt(b.start) + '\\u2013' + fmt(b.end) +
        (b.conflict ? ' \\u2014 conflicts with ' + b.with.map(i => '#' + i).join(', ') : '');
      col.appendChild(e);
    });
    grid.appendChild(col);
  });
  $('cal').replaceChildren(grid);

  listInto('conflicts', d.conflicts.map(p => '#' + p[0] + ' and #' + p[1]), 'None on this day');
  listInto('invalid', d.invalid.map(r => r.label + ': ' + r.reason), 'None');
}

$('prev').onclick = () => shift(-1);
$('next').onclick = () => shift(1);
$('date').onchange = e => e.target.value && load(e.target.value);
load();
</script></body></html>
"""


if __name__ == "__main__":
    sys.exit(main())
    