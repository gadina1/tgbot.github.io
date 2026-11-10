"""Parse Google Sheets 'htmlview' HTML into a grid with merged-cell info."""
import html
import re
from html.parser import HTMLParser


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []  # list of list of (text, rowspan, colspan)
        self._in_tbody = False
        self._cell = None
        self._row = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tbody":
            self._in_tbody = True
        elif not self._in_tbody:
            return
        elif tag == "tr":
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = {
                "text": [],
                "rs": int(a.get("rowspan", 1)),
                "cs": int(a.get("colspan", 1)),
            }
        elif tag == "br" and self._cell is not None:
            self._cell["text"].append("\n")

    def handle_endtag(self, tag):
        if not self._in_tbody:
            return
        if tag == "td" and self._cell is not None:
            txt = "".join(self._cell["text"])
            self._row.append((txt, self._cell["rs"], self._cell["cs"]))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None
        elif tag == "tbody":
            self._in_tbody = False

    def handle_data(self, data):
        if self._cell is not None:
            self._cell["text"].append(data)


def clean(s):
    s = s.replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in s.split("\n")]
    return "\n".join(l for l in lines if l)


def parse_grid(page):
    """Return grid[r][c] = {'text', 'r0', 'c0', 'rs', 'cs'} (merged cells share one dict)."""
    p = _TableParser()
    p.feed(page)
    grid = {}
    for r, row in enumerate(p.rows):
        c = 0
        for txt, rs, cs in row:
            while (r, c) in grid:
                c += 1
            cell = {"text": clean(txt), "r0": r, "c0": c, "rs": rs, "cs": cs}
            for dr in range(rs):
                for dc in range(cs):
                    grid[(r + dr, c + dc)] = cell
            c += cs
    nrows = max((k[0] for k in grid), default=-1) + 1
    ncols = max((k[1] for k in grid), default=-1) + 1
    empty = {"text": "", "rs": 1, "cs": 1}
    out = []
    for r in range(nrows):
        out.append([grid.get((r, c)) or dict(empty, r0=r, c0=c) for c in range(ncols)])
    return out
