"""
EARLYBIRDIE — Crawler v3 (requests + BeautifulSoup)
Portale: Flatfox API, ImmoScout24, Homegate, Anibis
"""

import hashlib
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("earlybirdie")

MIN_AREA  = 50
MAX_AREA  = 120
RADIUS_KM = 5

CITIES = {
    "Luzern":     (47.0502, 8.3093),
    "Zug":        (47.1661, 8.5158),
    "Solothurn":  (47.2088, 7.5323),
    "Basel":      (47.5596, 7.5886),
    "Bern":       (46.9480, 7.4474),
    "Thun":       (46.7580, 7.6280),
    "Winterthur": (47.5001, 8.7501),
    "Frauenfeld": (47.5574, 8.8986),
}

CEILING_KEYWORDS = [
    "raumhöhe", "deckenhöhe", "lichte höhe", "3 m", "3m",
    "3.0m", "3,0m", "3.5m", "hohe decke", "hallencharakter", "loft",
]

# Realistischer Browser-Header
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-CH,de;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
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
    # crawl_log mit TEXT-Feldern (kein INTEGER für run_id)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS crawl_log (
            run_id    TEXT,
            found     TEXT,
            inserted  TEXT,
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
        listing.get("description_snippet"),
        datetime.now(timezone.utc).isoformat(),
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
    m = re.search(r"(?:CHF|Fr\.?)[\s]?(\d[\d'.,]*)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"(\d{3,})", text)
    if m:
        try:
            return float(m.group(1).replace("'","").replace(",",""))
        except:
            return None
    return None

def in_range(area: Optional[float]) -> bool:
    return area is None or MIN_AREA <= area <= MAX_AREA

def fetch_html(url: str, timeout=20) -> Optional[BeautifulSoup]:
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        r = session.get(url, timeout=timeout, allow_redirects=True)
        log.debug("GET %s → %d", url, r.status_code)
        if r.status_code == 200:
            return BeautifulSoup(r.text, "html.parser")
        else:
            log.warning("HTTP %d für %s", r.status_code, url)
    except Exception as e:
        log.warning("Fetch-Fehler %s: %s", url, e)
    return None


# ─────────────────────────────────────────────
# PORTAL 1: FLATFOX (JSON-API)
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
        headers = {**HEADERS, "Accept": "application/json"}
        r = requests.get(url, headers=headers, timeout=15)
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
# PORTAL 2: ANIBIS (Schweizer Kleinanzeigen)
# ─────────────────────────────────────────────
def scrape_anibis(city: str, lat: float, lon: float) -> list[dict]:
    results = []
    try:
        url = f"https://www.anibis.ch/de/immobilien-gewerbe--406?q={city}&r={RADIUS_KM}"
        soup = fetch_html(url)
        if not soup:
            return []
        cards = soup.find_all("div", class_=re.compile(r"listing|ad-item|result", re.I))
        if not cards:
            cards = soup.find_all("article")[:20]
        for card in cards[:20]:
            text = card.get_text(" ", strip=True)
            if not text or len(text) < 20:
                continue
            a    = card.find("a", href=True)
            href = a["href"] if a else ""
            if href and not href.startswith("http"):
                href = "https://www.anibis.ch" + href
            img     = card.find("img")
            img_url = img.get("src", "") if img else ""
            area    = parse_area(text)
            price   = parse_price(text)
            if not in_range(area):
                continue
            results.append({
                "id":                  make_id(href or text[:80]),
                "portal":              "Anibis",
                "title":               text[:80],
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
        log.error("[Anibis] %s: %s", city, e)
    log.info("[Anibis] %s: %d gefunden", city, len(results))
    return results


# ─────────────────────────────────────────────
# PORTAL 3: IMMOSCOUT24
# ─────────────────────────────────────────────
def scrape_immoscout(city: str, lat: float, lon: float) -> list[dict]:
    results = []
    slug = city.lower().replace("ü","ue").replace("ä","ae").replace("ö","oe")
    url  = (
        f"https://www.immoscout24.ch/de/gewerbe/mieten/ort-{slug}"
        f"?r={RADIUS_KM}&nrf={MIN_AREA}&prf={MAX_AREA}"
    )
    soup = fetch_html(url)
    if not soup:
        return []
    try:
        # Suche nach JSON-LD Daten (strukturierte Daten im HTML)
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                import json
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") not in ("Apartment", "RealEstateListing", "Product"):
                        continue
                    name  = item.get("name", "Gewerbefläche")
                    url_l = item.get("url", "")
                    img   = item.get("image", "")
                    if isinstance(img, list):
                        img = img[0] if img else ""
                    desc  = item.get("description", "")
                    area  = parse_area(str(item.get("floorSize", "")))
                    price = parse_price(str(item.get("price", "")))
                    if not in_range(area):
                        continue
                    results.append({
                        "id":                  make_id(url_l or name),
                        "portal":              "ImmoScout24",
                        "title":               str(name)[:120],
                        "city":                city,
                        "address":             city,
                        "area_m2":             area,
                        "price_chf":           price,
                        "ceiling_height_ok":   check_ceiling(desc),
                        "image_url":           str(img),
                        "listing_url":         url_l,
                        "description_snippet": str(desc)[:300],
                    })
            except:
                pass

        # Fallback: direkte HTML-Karten
        if not results:
            cards = soup.find_all("article")[:20]
            for card in cards:
                text = card.get_text(" ", strip=True)
                if not text or len(text) < 20:
                    continue
                a    = card.find("a", href=True)
                href = a["href"] if a else ""
                if href and not href.startswith("http"):
                    href = "https://www.immoscout24.ch" + href
                img     = card.find("img")
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
                    "title":               text[:80],
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
# PORTAL 4: HOMEGATE
# ─────────────────────────────────────────────
def scrape_homegate(city: str, lat: float, lon: float) -> list[dict]:
    results = []
    url = (
        f"https://www.homegate.ch/mieten/gewerbeobjekte/ort-{city.lower()}"
        f"?ep={MAX_AREA}&sp={MIN_AREA}"
    )
    soup = fetch_html(url)
    if not soup:
        return []
    try:
        import json
        # JSON-LD zuerst versuchen
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data  = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    name  = item.get("name", "")
                    if not name:
                        continue
                    url_l = item.get("url", "")
                    desc  = item.get("description", "")
                    area  = parse_area(str(item.get("floorSize", "")))
                    price = parse_price(str(item.get("price", "")))
                    if not in_range(area):
                        continue
                    results.append({
                        "id":                  make_id(url_l or name),
                        "portal":              "Homegate",
                        "title":               str(name)[:120],
                        "city":                city,
                        "address":             city,
                        "area_m2":             area,
                        "price_chf":           price,
                        "ceiling_height_ok":   check_ceiling(desc),
                        "image_url":           "",
                        "listing_url":         url_l,
                        "description_snippet": str(desc)[:300],
                    })
            except:
                pass
    except Exception as e:
        log.error("[Homegate] %s: %s", city, e)
    log.info("[Homegate] %s: %d gefunden", city, len(results))
    return results


# ─────────────────────────────────────────────
# HAUPT-CRAWL
# ─────────────────────────────────────────────
def run_crawl():
    run_id  = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    started = datetime.now(timezone.utc).isoformat()
    log.info("═══ Earlybirdie Crawl gestartet · %s ═══", run_id)
    init_db()

    total_found = total_inserted = 0
    scrapers = [scrape_flatfox, scrape_anibis, scrape_immoscout, scrape_homegate]

    for city, (lat, lon) in CITIES.items():
        for scraper in scrapers:
            try:
                listings = scraper(city, lat, lon)
                total_found += len(listings)
                inserted = sum(1 for lst in listings if upsert_listing(lst))
                total_inserted += inserted
                log.info("  ✓ %s/%s: %d neu von %d",
                         scraper.__name__, city, inserted, len(listings))
            except Exception as e:
                log.error("Fehler %s/%s: %s", scraper.__name__, city, e)
            time.sleep(1.5)

    # Crawl-Log (alle TEXT-Felder)
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO crawl_log VALUES (%s,%s,%s,%s,%s)",
            (run_id, str(total_found), str(total_inserted),
             started, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.warning("crawl_log Fehler (nicht kritisch): %s", e)

    log.info("═══ Fertig · %d gefunden · %d neu gespeichert ═══",
             total_found, total_inserted)


if __name__ == "__main__":
    run_crawl()
