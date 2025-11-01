# Tanzania Security News Scanner

Scrapes RSS/Atom sources hourly for reports of **political violence / protests / alerts** in Northern Tanzania (Arusha / Manyara / Ngorongoro / Serengeti corridors) and publishes a simple site with **SMS-style lines** you can copy/paste to your family.

## What you get
- `web/data/latest.json` and `web/data/latest.txt` (SMS format)
- Static site at `web/index.html` that auto-refreshes and lists the latest items
- GitHub Actions workflow that runs **hourly** and deploys to **GitHub Pages**

## Quick start (GitHub Pages)
1. Create a new **private** or **public** GitHub repo and push this project.
2. Go to **Settings → Pages** and set “Build and deployment → Source: GitHub Actions”.
3. The included workflow will:
   - run the scanner hourly
   - deploy the `web/` folder to Pages
4. Share your Pages URL with family (it will look like: `https://<you>.github.io/<repo>/`).

> Tip: You can click “Run workflow” from the Actions tab to force an immediate refresh.

## Local test
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r scanner/requirements.txt
python scanner/scraper.py
open web/index.html  # on macOS
```

## Adjust the scope
- Edit locations and keywords in `scanner/scraper.py` (`LOCATIONS`, `KEYWORDS`).
- Add/remove RSS sources. Google News RSS queries are defined in `GOOGLE_NEWS_QUERIES`.
- Time window: defaults to last **72h** and stops after **Nov 8, 11:00 AM EST** (edit `COVERAGE_END`).

## Notes & Caveats
- This uses keyword + toponym filtering (no paid geofencing APIs). It aims for **high recall** with reasonable precision.
- Consider adding official channels (US/UK travel advisories, local police, park authorities) when they provide RSS/Atom.
- Social platforms (X/Telegram) require platform APIs/tokens; you can bolt those on later if desired.
