"""
EARLYBIRDIE — Crawler ohne Browser (requests + BeautifulSoup)
Kein Playwright, kein Chromium — läuft auf jedem Server!
"""

import hashlib
import logging
import os
import re
import time
from datetime import datetime
from typing import Optional

import psycopg2
import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("earlybirdie")

# ─────────────────────────────────────────────
# KONFIGURATION
# ─────────────────────────────────────────────
MIN_AREA  = 50
MAX_AREA  = 120
RADIUS_KM = 5

CITIES = {
    "Luzern":      (47.0502, 8.3093),
    "Zug":         (47.1661, 8.5158),
    "Solothurn":   (47.2088, 7.5323),
    "Basel":       (47.5596, 7.5886),
    "Bern":        (46.9480, 7.4474),
    "Thun":        (46.7580, 7.6280),
    "Winterthur":  (47.5001, 8.7501),
    "Frauenfeld":  (47.5574, 8.8986),
}

CEILING_KEYWORDS = [
    "raumhöhe", "deckenhöhe", "lichte höhe", "3 m", "3m",
    "3.0m", "3,0m", "3.5m", "3,5m", "4m", "hohe decke",
    "hallencharakter", "industrie", "loft",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-CH,de;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ─────────────────────────────────────────────
# DATENBANK
# ─────────────────────────────────────────────
def get_connection():
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        raise RuntimeError("DATABASE_URL nicht gesetzt!")
    return psycopg2.connect(db_url, sslmode="require")


def init_db():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id                  TEXT PRIMARY KEY,
            portal              TEXT,
            title               TEXT,
            city                TEXT,
            address             TEXT,
            area_m2             REAL,
            price_chf           REAL,
            ceiling_height_ok   INTEGER DEFAULT 0,
            image_url           TEXT,
            listing_url         TEXT,
            description_snippet TEXT,
            scraped_at          TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS crawl_log (
            run_id    TEXT,
            found     INTEGER,
            inserted  INTEGER,
            started   TEXT,
            finished  TEXT
        )
    """)
    conn.commit()
    conn.close()
    log.info("Datenbank bereit.")


def make_id(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:16]


def upsert_listing(listing: dict) -> bool:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO listings
          (id, portal, title, city, address, area_m2, price_chf,
           ceiling_height_ok, image_url, listing_url, description_snippet, scraped_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO NOTHING
    """, (
        listing["id"], listing.get("portal"), listing.get("title"),
        listing.get("city"), listing.get("address"), listing.get("area_m2"),
        listing.get("price_chf"), 1 if listing.get("ceiling_height_ok") else 0,
        listing.get("image_url"), listing.get("listing_url"),
        listing.get("description_snippet"), datetime.utcnow().isoformat(),
    ))
    is_new = cur.rowcount > 0
    conn.commit()
    conn.close()
    return is_new


# ─────────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────────
def check_ceiling(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in CEILING_KEYWORDS)

def parse_area(text: str) -> Optional[float]:
    text = text.replace("'", "").replace("\u2019", "")
    m = re.search(r"(\d+[\.,]?\d*)\s*m[²2]?", text, re.IGNORECASE)
    return float(m.group(1).replace(",", ".")) if m else None

def parse_price(text: str) -> Optional[float]:
    text = text.replace("'", "").replace("\u2019", "").replace(" ", "")
    m = re.search(r"(?:CHF|Fr\.?)[\s]?(\d[\d'.]*)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"(\d{3,})", text)
    if m:
        val = m.group(1).replace("'","").replace(".","")
        try: return float(val)
        except: return None
    return None

def in_range(area: Optional[float]) -> bool:
    return area is None or MIN_AREA <= area <= MAX_AREA

def fetch(url: str, timeout=15) -> Optional[BeautifulSoup]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        log.warning("Fetch-Fehler %s: %s", url, e)
    return None


# ─────────────────────────────────────────────
# PORTAL 1: FLATFOX (JSON-API — sehr zuverlässig)
# ─────────────────────────────────────────────
def scrape_flatfox(city: str, lat: float, lon: float) -> list[dict]:
    results = []
    url = (
        f"https://flatfox.ch/api/v1/listing/"
        f"?latitude={lat}&longitude={lon}"
        f"&radius={RADIUS_KM * 1000}"
        f"&listing_type=COMMERCIAL"
        f"&floor_space_from={MIN_AREA}"
        f"&floor_space_to={MAX_AREA}"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            log.warning("[Flatfox] %s: HTTP %d", city, r.status_code)
            return []
        data = r.json()
        for item in data.get("results", [])[:30]:
            area  = item.get("floor_space")
            price = item.get("rent_net") or item.get("price_display")
            if isinstance(price, str):
                price = parse_price(price)
            if not in_range(area):
                continue
            href    = f"https://flatfox.ch/de/wohnung/{item.get('pk','')}/"
            desc    = item.get("description", "") or ""
            imgs    = item.get("images", [])
            img_url = imgs[0].get("url", "") if imgs else ""
            results.append({
                "id":                  make_id(str(item.get("pk", href))),
                "portal":              "Flatfox",
                "title":               (item.get("title") or "Gewerbefläche")[:120],
                "city":                city,
                "address":             item.get("street") or city,
                "area_m2":             float(area) if area else None,
                "price_chf":           float(price) if price else None,
                "ceiling_height_ok":   check_ceiling(desc),
                "image_url":           img_url,
                "listing_url":         href,
                "description_snippet": desc[:300],
            })
    except Exception as e:
        log.error("[Flatfox] %s: %s", city, e)
    log.info("[Flatfox] %s: %d gefunden", city, len(results))
    return results


# ─────────────────────────────────────────────
# PORTAL 2: HOMEGATE (HTML-Scraping)
# ─────────────────────────────────────────────
def scrape_homegate(city: str, lat: float, lon: float) -> list[dict]:
    results = []
    city_slug = city.lower()
    url = (
        f"https://www.homegate.ch/mieten/gewerbeobjekte/ort-{city_slug}"
        f"?ep={MAX_AREA}&sp={MIN_AREA}"
    )
    soup = fetch(url)
    if not soup:
        log.warning("[Homegate] %s: Keine Antwort", city)
        return []
    try:
        # Homegate rendert via JS — wir holen was statisch verfügbar ist
        cards = soup.find_all(["article", "div"], 
                               attrs={"data-test": re.compile("result|listing|item", re.I)})
        if not cards:
            # Fallback: alle Links die nach Inseraten aussehen
            cards = soup.find_all("a", href=re.compile(r"/mieten/\d+"))[:20]

        for card in cards[:20]:
            text = card.get_text(" ", strip=True)
            if not text or len(text) < 20:
                continue
            href = card.get("href", "") or ""
            if card.name != "a":
                a = card.find("a", href=True)
                href = a["href"] if a else ""
            if href and not href.startswith("http"):
                href = "https://www.homegate.ch" + href
            img = card.find("img")
            img_url = ""
            if img:
                img_url = img.get("data-src") or img.get("src") or ""
            area  = parse_area(text)
            price = parse_price(text)
            if not in_range(area):
                continue
            title = text[:80].split("\n")[0]
            results.append({
                "id":                  make_id(href or text[:80]),
                "portal":              "Homegate",
                "title":               title,
                "city":                city,
                "address":             city,
                "area_m2":             area,
                "price_chf":           price,
                "ceiling_height_ok":   check_ceiling(text),
                "image_url":           img_url,
                "listing_url":         href,
                "description_snippet": text[:300],
            })
    except Exception as e:
        log.error("[Homegate] %s: %s", city, e)
    log.info("[Homegate] %s: %d gefunden", city, len(results))
    return results


# ─────────────────────────────────────────────
# PORTAL 3: IMMOSCOUT24 (HTML-Scraping)
# ─────────────────────────────────────────────
def scrape_immoscout(city: str, lat: float, lon: float) -> list[dict]:
    results = []
    slug = city.lower().replace("ü","ue").replace("ä","ae").replace("ö","oe")
    url  = (
        f"https://www.immoscout24.ch/de/gewerbe/mieten/ort-{slug}"
        f"?r={RADIUS_KM}&nrf={MIN_AREA}&prf={MAX_AREA}"
    )
    soup = fetch(url)
    if not soup:
        log.warning("[ImmoScout24] %s: Keine Antwort", city)
        return []
    try:
        cards = soup.find_all("article")
        if not cards:
            cards = soup.find_all("div", class_=re.compile(r"listing|result|item", re.I))

        for card in cards[:20]:
            text = card.get_text(" ", strip=True)
            if not text or len(text) < 20:
                continue
            a    = card.find("a", href=True)
            href = a["href"] if a else ""
            if href and not href.startswith("http"):
                href = "https://www.immoscout24.ch" + href
            img = card.find("img")
            img_url = ""
            if img:
                img_url = img.get("data-src") or img.get("src") or ""
            area  = parse_area(text)
            price = parse_price(text)
            if not in_range(area):
                continue
            results.append({
                "id":                  make_id(href or text[:80]),
                "portal":              "ImmoScout24",
                "title":               text[:80].split("\n")[0],
                "city":                city,
                "address":             city,
                "area_m2":             area,
                "price_chf":           price,
                "ceiling_height_ok":   check_ceiling(text),
                "image_url":           img_url,
                "listing_url":         href,
                "description_snippet": text[:300],
            })
    except Exception as e:
        log.error("[ImmoScout24] %s: %s", city, e)
    log.info("[ImmoScout24] %s: %d gefunden", city, len(results))
    return results


# ─────────────────────────────────────────────
# PORTAL 4: COMPARIS (JSON-API)
# ─────────────────────────────────────────────
def scrape_comparis(city: str, lat: float, lon: float) -> list[dict]:
    results = []
    try:
        # Comparis hat eine interne API
        api_url = "https://api.comparis.ch/realestate/searchresult"
        payload = {
            "RequestObject": {
                "RentOrBuy": "rent",
                "PropertyType": "commercial",
                "Zip": [],
                "City": city,
                "RoomFrom": None,
                "RoomTo": None,
                "FloorSpaceFrom": MIN_AREA,
                "FloorSpaceTo": MAX_AREA,
                "PageIndex": 0,
                "PageSize": 20,
            }
        }
        headers = {**HEADERS, "Content-Type": "application/json"}
        r = requests.post(api_url, json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            items = data.get("Items") or data.get("Results") or []
            for item in items[:20]:
                area  = item.get("FloorSpace") or item.get("LivingSpace")
                price = item.get("Price") or item.get("Rent")
                if not in_range(area):
                    continue
                listing_id = str(item.get("Id", ""))
                href    = f"https://www.comparis.ch/immobilien/marktplatz/details/{listing_id}"
                desc    = item.get("Description", "") or ""
                img_url = item.get("MainImageUrl", "") or ""
                title   = item.get("Title") or item.get("PropertyType") or "Gewerbefläche"
                results.append({
                    "id":                  make_id(listing_id or href),
                    "portal":              "Comparis",
                    "title":               str(title)[:120],
                    "city":                city,
                    "address":             item.get("Street", city),
                    "area_m2":             float(area) if area else None,
                    "price_chf":           float(price) if price else None,
                    "ceiling_height_ok":   check_ceiling(desc),
                    "image_url":           img_url,
                    "listing_url":         href,
                    "description_snippet": str(desc)[:300],
                })
    except Exception as e:
        log.error("[Comparis] %s: %s", city, e)
    log.info("[Comparis] %s: %d gefunden", city, len(results))
    return results


# ─────────────────────────────────────────────
# HAUPT-CRAWL
# ─────────────────────────────────────────────
def run_crawl():
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    log.info("═══ Earlybirdie Crawl gestartet · %s ═══", run_id)
    init_db()

    total_found = total_inserted = 0
    scrapers = [scrape_flatfox, scrape_homegate, scrape_immoscout, scrape_comparis]

    for city, (lat, lon) in CITIES.items():
        for scraper in scrapers:
            try:
                listings = scraper(city, lat, lon)
                total_found += len(listings)
                inserted = sum(1 for lst in listings if upsert_listing(lst))
                total_inserted += inserted
                log.info("  ✓ %s/%s: %d neu von %d", scraper.__name__, city, inserted, len(listings))
            except Exception as e:
                log.error("Fehler %s/%s: %s", scraper.__name__, city, e)
            time.sleep(1.5)  # Höfliche Pause

    # Crawl-Log
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO crawl_log VALUES (%s,%s,%s,%s,%s)",
        (run_id, total_found, total_inserted,
         run_id, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

    log.info("═══ Fertig · %d gefunden · %d neu gespeichert ═══",
             total_found, total_inserted)


if __name__ == "__main__":
    run_crawl()
