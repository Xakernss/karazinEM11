#!/usr/bin/env python3
"""Скачивает расписание группы с online.karazin.ua и сохраняет schedule.json."""
import re, sys, json, html, ssl, datetime, urllib.request, urllib.parse
from zoneinfo import ZoneInfo

# ==== НАСТРОЙКИ ====
GROUP_NAME, GROUP_ID = "ЕМ-11", "-4791"
FACULTY, COURSE = "1002", "1"
DAYS_AHEAD = 28
BASE = "https://online.karazin.ua:1443/cgi-bin/timetable.cgi"
# ===================

def open_url(req):
    try:
        return urllib.request.urlopen(req, timeout=60).read()
    except ssl.SSLError as e:  # публичные данные: при проблеме с сертификатом пробуем без проверки
        print("SSL warning:", e)
        ctx = ssl._create_unverified_context()
        return urllib.request.urlopen(req, timeout=60, context=ctx).read()

def download():
    ua = {"User-Agent": "Mozilla/5.0 (group-schedule-bot)"}
    today = datetime.datetime.now(ZoneInfo("Europe/Kyiv")).date()
    f = lambda d: d.strftime("%d.%m.%Y")
    data = urllib.parse.urlencode({
        "faculty": FACULTY, "teacher": "", "course": COURSE, "group": GROUP_NAME,
        "sdate": f(today), "edate": f(today + datetime.timedelta(days=DAYS_AHEAD)), "n": "700"
    }, encoding="cp1251").encode()
    pages = [urllib.request.Request(BASE + "?n=700", data=data, headers=ua),
             urllib.request.Request(f"{BASE}?n=700&group={GROUP_ID}", headers=ua)]
    for req in pages:
        try:
            raw = open_url(req)
            days = parse(raw.decode("cp1251", errors="replace"))
            if days:
                return days
        except Exception as e:
            print("Не удалось:", e)
    sys.exit("Расписание не получено — schedule.json не изменён")

def parse(t):
    out = []
    heads = list(re.finditer(r"<h4>(\d\d)\.(\d\d)\.(\d{4}) <small>([^<]*)</small></h4>", t))
    for i, h in enumerate(heads):
        seg = t[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(t)]
        lessons = []
        for r in re.finditer(r"<tr><td>(\d+)</td><td>(\d\d:\d\d)<br>(\d\d:\d\d)</td><td[^>]*>(.*?)</td></tr>", seg, re.S):
            num, start, end, cell = r.groups()
            remote = "remote_work" in cell
            cell = re.sub(r"<img[^>]*>|<span class=\"remote_work\">.*?</span>", "", cell)
            lines = [html.unescape(x).replace("\xa0", " ").strip() for x in cell.split("<br>")]
            entries, cur = [], []
            for ln in lines + [""]:
                if ln: cur.append(ln)
                elif cur: entries.append({"group": cur[0] if len(cur) > 1 else "", "text": cur[-1]}); cur = []
            if entries:
                lessons.append({"num": int(num), "start": start, "end": end, "remote": remote, "entries": entries})
        out.append({"date": f"{h[3]}-{h[2]}-{h[1]}", "weekday": h[4].strip(), "lessons": lessons})
    return out

if __name__ == "__main__":
    days = parse(open(sys.argv[1], encoding="cp1251").read()) if len(sys.argv) > 1 else download()
    now = datetime.datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%Y-%m-%d %H:%M")
    json.dump({"group": GROUP_NAME, "updated": now, "days": days}, open("schedule.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("Дней:", len(days), "Пар:", sum(len(d["lessons"]) for d in days))
