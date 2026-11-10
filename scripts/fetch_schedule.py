#!/usr/bin/env python3
"""Download the schedule Google Sheet and convert it to data/schedule.json.

Run:  python3 scripts/fetch_schedule.py
Uses only the standard library. The sheet must be viewable by link.
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sheetgrid import parse_grid  # noqa: E402

SHEET_ID = os.environ.get("SHEET_ID", "1LcYeEJxRtrv38BGrNm6XGdgtxAVlq9zSemTH3QWS_qo")
BASE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "schedule.json")
# Monday of study week 1 (1 Sept 2026 is a Tuesday).
SEMESTER_START = os.environ.get("SEMESTER_START", "2026-08-31")

DAY_NAMES = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ"]
TIME_RE = re.compile(r"^\s*(\d{1,2})[.:](\d{2})\s*[-–]\s*(\d{1,2})[.:](\d{2})\s*$")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 schedule-sync"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8")


def list_sheets():
    page = get(f"{BASE}/htmlview")
    items = re.findall(r'\{name: "((?:[^"\\]|\\.)*)", pageUrl: "[^"]*", gid: "(\d+)"', page)
    if not items:
        raise RuntimeError("Не удалось найти листы таблицы (таблица закрыта?)")
    return [(json.loads(f'"{n}"').strip(), gid) for n, gid in items]


# ---------- lesson text parsing ----------

TYPE_PATTERNS = [
    ("lab", r"лаб"),
    ("lecture", r"лекц"),
    ("practice", r"практ|семинар|тренинг"),
]


def parse_weeks(text):
    """Return (list of week numbers or None, parity 'odd'/'even'/None)."""
    t = re.sub(r"-+", "-", text.lower().replace("–", "-").replace("—", "-"))
    weeks = set()
    # sequences like "1-3 нед. 10-18нед", "2 -17 нед", "11 нед", "3-14 нед (1-8 нед в ...)"
    for m in re.finditer(r"((?:\d{1,2}\s*(?:-\s*\d{1,2})?\s*[,и]?\s*)+)-?\s*н(?:ед|\.|/)", t):
        seq = m.group(1)
        # Ignore the inner "(1-8 нед в 307 ауд)" style clarifications: only first-level ones
        before = t[: m.start()]
        if before.count("(") > before.count(")"):
            continue
        for a, b in re.findall(r"(\d{1,2})(?:\s*-\s*(\d{1,2}))?", seq):
            a = int(a)
            b = int(b) if b else a
            if 1 <= a <= b <= 25:
                weeks.update(range(a, b + 1))
    if not weeks:
        # "3-18 ауд410" — range right before "ауд" without "нед"
        m = re.search(r"(\d{1,2})\s*-\s*(\d{1,2})\s*(?:ауд|\(|$)", t)
        if m and 1 <= int(m.group(1)) <= int(m.group(2)) <= 25:
            weeks.update(range(int(m.group(1)), int(m.group(2)) + 1))
    parity = None
    if re.search(r"(?<![а-я])(н/н|неч[её]т)", t):
        parity = "odd"
    elif re.search(r"(?<![а-я])(ч/н|ч[её]тн)", t):
        parity = "even"
    return (sorted(weeks) or None), parity


def detect_type(line):
    low = line.lower()
    if "лекц" in low and "практ" in low:
        return "mixed"
    for k, pat in TYPE_PATTERNS:
        if re.search(pat, low):
            return k
    return None


def find_teacher(line):
    m = re.search(r"преп\.?\s*(?:преп\.?\s*)?([А-ЯЁ][а-яё]+(?:\.)?\s*(?:[А-ЯЁ]\.?\s*){0,2})", line)
    if not m:  # "Хузина Д. Я." without "преп"
        m = re.search(r"([А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.?)", line)
    if not m:
        return None
    t = re.sub(r"\s+", " ", m.group(1)).strip(" ,")
    return re.sub(r"\.(?=[А-ЯЁ])", ". ", t)


def find_room(line):
    m = re.search(r"ауд\.?\s*(\d[\dА-Яа-я/\-]*)", line, re.I) or re.search(r"(\d{3}[а-я]?)\s*ауд", line, re.I)
    return m.group(1) if m else None


def find_place(line):
    m = re.search(r"(СЦ\s*\([^)]*\)|СК\s*«[^»]+»(?:\s*проезд[^,]*,\s*\d+)?|(?:ул\.\s*)?Кремл[её]вская\s*\d+\s*[аА]?)", line)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else None


GROUP_PREFIX = re.compile(
    r"^\s*(?:у\s+)?((?:(?:гр\.?\s*)?(?:16-)?\d{3}\s*(?:гр\.?)?\s*,?\s*)+)(?=\D)", re.I)


def split_group_prefix(line):
    """'у гр 16-631 17 нед ...' -> (['631'], '17 нед ...'). Only when the line starts with у/гр."""
    if not re.match(r"^\s*(у\s|гр\s*\.?\s*\d)", line, re.I):
        return None, line
    m = GROUP_PREFIX.match(line)
    if not m:
        return None, line
    nums = re.findall(r"\d{3}", m.group(1))
    return nums, line[m.end():].strip()


def subject_of(line):
    subj = re.split(r"\(|\bпреп\.?|\s\d{1,2}\s*-+\s*\d|\s\d{1,2}\s*нед|\s[сc]\s*\d|недпреп|\sСК\s*«|\sлекци[яи]\s"
                    r"|\s[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]", line, maxsplit=1)[0]
    subj = re.sub(r"\s+(лекци[яи]|практика|лаб\w*)$", "", subj.strip(" .,-"), flags=re.I)
    return subj.strip(" .,-")


LEAD_JUNK = re.compile(
    r"^(?:\s*(?:\((?:лекци\w*|практик\w*|лаб\w*)[^)]*\)|лекци\w*|практик\w*|лаб\w*\.?|семинар\w*|"
    r"[сc]\s*(?=\d)|\d{1,2}(?:\s*-+\s*\d{1,2})?\s*(?:нед\.?|н\.)?|[,.])\s*)+", re.I)


def own_subject(body):
    """Subject named in this line, or None if the line only adds weeks/type/room to the previous one."""
    rest = LEAD_JUNK.sub("", body).strip()
    if not re.match(r"^[А-ЯЁA-Z]", rest):
        return None
    if re.match(r"^(СЦ|СК|Кремл|Ауд)", rest) or re.match(r"^[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.", rest):
        return None
    return subject_of(rest) or None


def is_continuation(line):
    return own_subject(line) is None


def parse_cell(text):
    """Split a cell into separate lessons. Returns list of dicts with optional 'only' (group numbers)."""
    lines = [l.strip(" !") for l in text.split("\n") if l.strip(" !")]
    parts = []
    header = None  # subject-only line like "Безопасность жизнедеятельности"
    for i, line in enumerate(lines):
        only, body = split_group_prefix(line)
        weeks, parity = parse_weeks(body)
        prev = parts[-1] if parts else None
        cont = is_continuation(body)
        nxt_cont = i + 1 < len(lines) and is_continuation(split_group_prefix(lines[i + 1])[1])
        if not cont and weeks is None and nxt_cont and not only and len(lines) > 1:
            header = {"subject": subject_of(body), "type": detect_type(body), "teacher": find_teacher(body)}
            continue
        base = prev if (cont and prev) else (header if cont and header else None)
        part = {
            "subject": own_subject(body) if not cont else (base["subject"] if base else subject_of(body) or body),
            "type": detect_type(body) or (base["type"] if base else None),
            "teacher": find_teacher(body) or (base["teacher"] if base else None),
            "room": find_room(body),
            "place": find_place(body),
            "weeks": weeks,
            "parity": parity,
            "line": line,
        }
        if cont and base and part["room"] is None and part["place"] is None:
            part["room"], part["place"] = base.get("room"), base.get("place")
        if only:
            part["only"] = only
        elif cont and prev and prev.get("only"):
            part["only"] = prev["only"]
        # a bare "17-18 нед" line just adds weeks to the previous lesson
        if cont and prev and re.fullmatch(r"[\d\s\-,.]*нед\.?", body) and weeks:
            prev["weeks"] = sorted(set(prev["weeks"] or []) | set(weeks))
            prev["line"] += "\n" + line
            continue
        if not part["subject"]:
            part["subject"] = body
        parts.append(part)
    if not parts and header:
        parts.append(dict(header, room=None, place=None, weeks=None, parity=None, line=text))
    parts.sort(key=lambda p: (p["weeks"] or [0])[0])
    return parts


# ---------- sheet parsing ----------

def parse_sheet(name, gid):
    grid = parse_grid(get(f"{BASE}/htmlview/sheet?headers=false&gid={gid}"))
    title = ""
    groups, lessons_by_group = [], {}
    days = {}  # day index -> {time -> {group: [entries]}}
    times_by_day = {}

    for hr, row in enumerate(grid):
        starts = [c for c, cell in enumerate(row)
                  if cell["r0"] == hr and cell["c0"] == c and cell["text"].strip().lower() == "дни недели"]
        if not starts:
            continue
        for bi, c0 in enumerate(starts):
            c_end = starts[bi + 1] if bi + 1 < len(starts) else len(row)
            if not title and hr > 0:
                t = grid[hr - 1][c0]["text"]
                m = re.search(r"РАСПИСАНИЕ[^\n]*", t)
                title = m.group(0) if m else ""
            block_groups = []
            for c in range(c0 + 2, c_end):
                code = re.sub(r"\s+", "", grid[hr][c]["text"])
                if not code or grid[hr][c]["c0"] != c:
                    continue
                direction = grid[hr + 1][c]["text"].replace("\n", " ") if hr + 1 < len(grid) else ""
                block_groups.append((c, code, direction))
                if code not in lessons_by_group:
                    groups.append({"id": code, "direction": direction.strip()})
                    lessons_by_group[code] = True
            col_to_group = {c: code for c, code, _ in block_groups}
            day_idx = None
            for r in range(hr + 2, len(grid)):
                dcell = grid[r][c0]["text"].strip().upper()
                if dcell in DAY_NAMES:
                    day_idx = DAY_NAMES.index(dcell)
                elif dcell.lower() == "дни недели":
                    break
                tm = TIME_RE.match(grid[r][c0 + 1]["text"])
                if day_idx is None or not tm:
                    continue
                time = "%02d:%s–%02d:%s" % (int(tm.group(1)), tm.group(2), int(tm.group(3)), tm.group(4))
                times_by_day.setdefault(day_idx, [])
                if time not in times_by_day[day_idx]:
                    times_by_day[day_idx].append(time)
                slot = days.setdefault(day_idx, {}).setdefault(time, {})
                for c, code, _ in block_groups:
                    cell = grid[r][c]
                    text = cell["text"].strip()
                    if not text:
                        continue
                    span = [col_to_group[x] for x in range(cell["c0"], cell["c0"] + cell["cs"]) if x in col_to_group]
                    entries = []
                    for part in parse_cell(text):
                        only = part.pop("only", None)
                        applies = [g for g in span if not only or g[-3:] in only]
                        if code not in applies:
                            continue
                        entry = {"text": text, **part}
                        if len(applies) > 1:
                            entry["shared"] = applies
                        entries.append(entry)
                    if entries:
                        slot[code] = entries
        break  # all blocks of a sheet share one header row

    out_days = []
    for d in sorted(times_by_day):
        times = sorted(times_by_day[d])
        out_days.append({
            "day": d,
            "name": DAY_NAMES[d].capitalize(),
            "slots": [{"time": t, "lessons": days[d].get(t, {})} for t in times],
        })
    return {"name": name, "gid": gid, "title": title, "groups": groups, "days": out_days}


def main():
    sheets = list_sheets()
    courses = []
    for name, gid in sheets:
        course = parse_sheet(name, gid)
        if course["groups"]:
            courses.append(course)
        print(f"{name}: {len(course['groups'])} групп", file=sys.stderr)
    if not courses:
        raise RuntimeError("Не найдено ни одного расписания")
    data = {
        "source": f"{BASE}/edit",
        "semesterStart": SEMESTER_START,
        "courses": courses,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    old = None
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    unchanged = old and {k: v for k, v in old.items() if k not in ("updated", "checked")} == data
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    data["updated"] = old.get("updated", now) if unchanged else now
    data["checked"] = now
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("без изменений" if unchanged else "расписание обновлено", file=sys.stderr)


if __name__ == "__main__":
    main()
