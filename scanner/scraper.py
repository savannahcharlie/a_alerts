#!/usr/bin/env python3
"""
Tanzania Security News Scanner
- Pulls relevant items from RSS/Atom sources for Northern Tanzania (Kilimanjaro/Arusha/Manyara/Ngorongoro/Serengeti/Tarangire)
- Filters for political violence / unrest keywords
- Outputs:
  web/data/latest.json  -> structured entries for the site
  web/data/latest.txt   -> SMS-style lines (for copy/paste to SMS)
Time zone: America/New_York (EST/EDT)
Coverage window: up to Nov 8, 11:00 AM America/New_York (adjust as needed)
"""

import os, re, json, time, hashlib
from datetime import datetime, timedelta
from dateutil import parser as dateparser
import pytz
import feedparser
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
WEB_DATA_DIR = os.path.join(PROJECT_ROOT, "web", "data")
os.makedirs(WEB_DATA_DIR, exist_ok=True)

TZ_EST = pytz.timezone("America/New_York")
NOW_EST = datetime.now(TZ_EST)

# --- Coverage window (edit if needed) ---
# Stop scanning after this time (to avoid stale updates)
COVERAGE_END = TZ_EST.localize(datetime(NOW_EST.year, 11, 8, 11, 0, 0))  # Nov 8, 11:00 AM local
if NOW_EST > COVERAGE_END:
    print("⚠️  Outside the configured coverage window; exiting without changes.")
    exit(0)

# --- Locations ---
LOCATIONS = [
    "Kilimanjaro International Airport", "Kilimanjaro Airport", "JRO",
    "Arusha National Park", "Arusha",
    "A23", "A104", "B144", "B 144",
    "Tloma", "Karatu",
    "Ngorongoro", "Ngorongoro Crater",
    "Tarangire National Park", "Lake Manyara",
    "Serengeti", "Mbali Mbali Soroi Serengeti Lodge", "Soroi Serengeti"
]

# 15-mile radius constraint is approximated by requiring a specific toponym mention.
# (True geofencing usually requires a geocoding/places API; here we use a robust keyword list.)

# --- Keywords for political unrest / alerts ---
KEYWORDS = [
    "protest", "protests", "protester", "demonstration", "demonstrations",
    "unrest", "clashes", "clash", "riot", "rioting",
    "violence", "violent", "attack", "attacks", "assault", "arson",
    "political", "election", "campaign rally", "march",
    "security alert", "travel advisory", "travel warning", "curfew",
    "roadblock", "road block", "road blockade", "blockade", "closure", "closed",
    "disruption", "disturbance"
]

KEYWORD_RE = re.compile(r"|".join([re.escape(k) for k in KEYWORDS]), re.IGNORECASE)
LOC_RE = re.compile(r"|".join([re.escape(l) for l in LOCATIONS]), re.IGNORECASE)

# --- RSS sources ---
# Google News RSS scoped to Tanzania and Northern regions. Feel free to add/remove sources.
GOOGLE_NEWS_QUERIES = [
    # General Tanzania security
    'site:gov.uk travel advice Tanzania OR Arusha OR Ngorongoro OR Serengeti',
    'site:tz.usembassy.gov security alert Tanzania OR Arusha OR Ngorongoro OR Serengeti',
    'Tanzania protest OR unrest OR clashes OR violence',
    # Specific corridors / parks / towns
    'Arusha protest OR unrest OR violence OR alert',
    'Kilimanjaro Airport protest OR unrest OR violence OR alert',
    'Ngorongoro protest OR unrest OR violence OR alert',
    'Serengeti protest OR unrest OR violence OR alert',
    'Tarangire protest OR unrest OR violence OR alert',
    'Lake Manyara protest OR unrest OR violence OR alert',
    'Karatu protest OR unrest OR violence OR alert',
    'A23 Tanzania protest OR unrest OR violence OR alert',
    'A104 Tanzania protest OR unrest OR violence OR alert',
]

def google_news_rss_url(query:str, days:int=7) -> str:
    # Google News RSS: https://news.google.com/rss/search?q=<query>&hl=en-US&gl=US&ceid=US:en
    # Use recent window by adding "when" operator in query if desired, but RSS has its own recency.
    from urllib.parse import quote_plus
    q = quote_plus(query)
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

# Additional direct feeds (edit/extend as needed)
RSS_FEEDS = [
    # UK Travel Advice (site has RSS per country, but if unavailable, Google News above will catch updates)
    # Add reputable local outlets if they have RSS
]

def iterate_items_from_rss(url):
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            yield {
                "source": feed.feed.get("title", url),
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", entry.get("updated", "")),
                "summary": entry.get("summary", ""),
            }
    except Exception as e:
        print(f"RSS error for {url}: {e}")

def normalize_time(s):
    if not s:
        return NOW_EST
    try:
        dt = dateparser.parse(s)
    except Exception:
        return NOW_EST
    if not dt.tzinfo:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(TZ_EST)

def make_id(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]

def looks_relevant(item_text:str) -> bool:
    if not KEYWORD_RE.search(item_text):
        return False
    if not LOC_RE.search(item_text):
        return False
    return True

def summarize_location(text:str) -> str:
    # Return the first location token matched, as a compact "LOC" for the SMS line
    m = LOC_RE.search(text)
    if m:
        return m.group(0)
    return "Northern TZ"

def as_sms_line(dt_est:datetime, loc:str, title:str, source:str, short:str):
    # SMS format: "HH:MM EST | LOC | ALERT | src"
    hhmm = dt_est.strftime("%-I:%M %p") if hasattr(dt_est, "strftime") else "—"
    return f"{hhmm} EST | {loc} | {title} | {short}"

def shorten_source(link_or_source:str) -> str:
    # Keep domain only for brevity
    from urllib.parse import urlparse
    try:
        u = urlparse(link_or_source)
        if u.netloc:
            return u.netloc.replace("www.", "")
    except Exception:
        pass
    return link_or_source[:40]

def main():
    items = []

    # Google News feeds
    for q in GOOGLE_NEWS_QUERIES:
        url = google_news_rss_url(q)
        for it in iterate_items_from_rss(url):
            items.append(it)

    # Static RSS list
    for url in RSS_FEEDS:
        for it in iterate_items_from_rss(url):
            items.append(it)

    # De-dup and filter
    seen = set()
    relevant = []
    for it in items:
        text = " ".join([it.get("title",""), it.get("summary","")])
        uid = make_id(it.get("link","") + it.get("title",""))
        if uid in seen:
            continue
        seen.add(uid)

        if looks_relevant(text):
            dt_est = normalize_time(it.get("published"))
            # Only keep last 72h to reduce noise
            if (NOW_EST - dt_est) > timedelta(days=3):
                continue

            loc = summarize_location(text)
            src = it.get("link") or it.get("source","")
            short_src = shorten_source(src)
            sms = as_sms_line(dt_est, loc, it.get("title","").strip(), it.get("source",""), short_src)

            relevant.append({
                "id": uid,
                "when_est_iso": dt_est.isoformat(),
                "when_est_hhmm": dt_est.strftime("%-I:%M %p EST"),
                "location": loc,
                "alert": it.get("title","").strip(),
                "source": src,
                "source_short": short_src,
                "summary": it.get("summary","").strip(),
            })

    # Sort newest first
    relevant.sort(key=lambda x: x["when_est_iso"], reverse=True)

    # Write JSON
    json_path = os.path.join(WEB_DATA_DIR, "latest.json")
    with open(json_path, "w") as f:
        json.dump({
            "generated_at_est": NOW_EST.isoformat(),
            "count": len(relevant),
            "entries": relevant
        }, f, indent=2)

    # Write SMS-style lines (top 20)
    lines_path = os.path.join(WEB_DATA_DIR, "latest.txt")
    with open(lines_path, "w") as f:
        for e in relevant[:20]:
            f.write(f'{e["when_est_hhmm"]} | {e["location"]} | {e["alert"]} | {e["source_short"]}\n')

    print(f"Wrote {len(relevant)} relevant items.")
    print(f"- {json_path}")
    print(f"- {lines_path}")

if __name__ == "__main__":
    main()
