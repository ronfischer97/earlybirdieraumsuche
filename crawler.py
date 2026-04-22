"""
╔═══════════════════════════════════════════════════════════╗
║         EARLYBIRDIE — Crawler · PostgreSQL Edition        ║
╚═══════════════════════════════════════════════════════════╝
"""

import asyncio
import psycopg2
import psycopg2.extras
import hashlib
import logging
import re
import os
import time
from datetime import datetime
from typing import Optional
from playwright.async_api import async_playwright, Page, BrowserContext

# ─────────────────────────────────────────────
# KONFIGURATION
# ─────────────────────────────────────────────
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:axkMSXDLCFvMxpeByNRDjrPYuEvIwKsR@shinkansen.proxy.rlwy.net:26608/railway"
)

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

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("earlybirdie")


# ─────────────────────────────────────────────
# DATENBANK
# ─────────────────────────────────────────────
def init_db():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id                  TEXT PRIMARY KEY,
            portal              TEXT,
            title               TEXT,
            city                TEXT,
            address             TEXT,
            area_m2             REAL,
            price_chf           REAL,
            ceiling_height_ok   BOOLEAN DEFAULT FALSE,
            image_url           TEXT,
            listing_url         TEXT,
            description_snippet TEXT,
            scraped_at          TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS crawl_log (
            run_id   TEXT,
            portal   TEXT,
            city     TEXT,
            found    INTEGER,
            inserted INTEGER,
            started  TIMESTAMP,
            finished TIMESTAMP
        )
    """)
    conn.close()
    log.info("Datenbank bereit (PostgreSQL)")


def make_id(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:16]


def upsert_listing(listing: dict) -> bool:
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
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
        listing.get("price_chf"), bool(listing.get("ceiling_height_ok")),
        listing.get("image_url"), listing.get("listing_url"),
        listing.get("description_snippet"), datetime.utcnow(),
    ))
    is_new = cur.rowcount > 0
    conn.commit()
    conn.close()
    return is_new


# ─────────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────────
def check_ceiling_height(text: str) -> bool:
    return any(kw in text.lower() for kw in CEILING_KEYWORDS)

def parse_area(text: str) -> Optional[float]:
    text = text.replace("'", "").replace(" ", "")
    m = re.search(r"(\d+[\.,]?\d*)\s*m[²2]?", text, re.IGNORECASE)
    return float(m.group(1).replace(",", ".")) if m else None

def parse_price(text: str) -> Optional[float]:
    text = text.replace("'", "").replace(" ", "")
    m = re.search(r"(?:CHF|Fr\.?)[\s]?(\d+[\.,]?\d*)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"(\d{3,}[\.,]?\d*)", text)
    return float(m.group(1).replace(",", ".")) if m else None

def in_area_range(area: Optional[float]) -> bool:
    if area is None:
        return True
    return MIN_AREA <= area <= MAX_AREA

async def slow_scroll(page: Page, steps: int = 5, delay: float = 0.6):
    for _ in range(steps):
        await page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
        await asyncio.sleep(delay)


# ─────────────────────────────────────────────
# SCRAPER
# ─────────────────────────────────────────────
class ImmoScoutScraper:
    PORTAL = "ImmoScout24"
    def __init__(self, ctx): self.ctx = ctx

    async def scrape_city(self, city, lat, lon):
        results = []
        slug = city.lower().replace("ü","ue").replace("ä","ae")
        url  = (f"https://www.immoscout24.ch/de/gewerbe/mieten/ort-{slug}"
                f"?r={RADIUS_KM}&nrf={MIN_AREA}&prf={MAX_AREA}")
        page = await self.ctx.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            await slow_scroll(page)
            try: await page.click('[id*="cookie"] button', timeout=3000)
            except: pass
            cards = await page.query_selector_all("article, div[class*='ResultList__listItem']")
            for card in cards[:30]:
                try:
                    raw     = await card.inner_text()
                    href_el = await card.query_selector("a[href]")
                    href    = await href_el.get_attribute("href") if href_el else ""
                    if href and not href.startswith("http"):
                        href = "https://www.immoscout24.ch" + href
                    img_el  = await card.query_selector("img")
                    img_url = ""
                    if img_el:
                        img_url = await img_el.get_attribute("data-src") or await img_el.get_attribute("src") or ""
                    area  = parse_area(raw)
                    price = parse_price(raw)
                    if not in_area_range(area): continue
                    results.append({
                        "id": make_id(href or raw[:80]),
                        "portal": self.PORTAL, "title": raw.split("\n")[0][:120],
                        "city": city, "address": city, "area_m2": area,
                        "price_chf": price, "ceiling_height_ok": check_ceiling_height(raw),
                        "image_url": img_url, "listing_url": href,
                        "description_snippet": raw[:300],
                    })
                except: pass
        except Exception as e:
            log.error("[%s] %s: %s", self.PORTAL, city, e)
        finally:
            await page.close()
        log.info("[%s] %s: %d gefunden", self.PORTAL, city, len(results))
        return results


class HomegateScraper:
    PORTAL = "Homegate"
    def __init__(self, ctx): self.ctx = ctx

    async def scrape_city(self, city, lat, lon):
        results = []
        url  = (f"https://www.homegate.ch/mieten/gewerbeobjekte/ort-{city.lower()}"
                f"?ep={MAX_AREA}&sp={MIN_AREA}")
        page = await self.ctx.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            await slow_scroll(page)
            try: await page.click('button[id*="accept"]', timeout=3000)
            except: pass
            cards = await page.query_selector_all("div[data-test='result-list-item'], article")
            for card in cards[:30]:
                try:
                    raw     = await card.inner_text()
                    href_el = await card.query_selector("a")
                    href    = await href_el.get_attribute("href") if href_el else ""
                    if href and not href.startswith("http"):
                        href = "https://www.homegate.ch" + href
                    img_el  = await card.query_selector("img")
                    img_url = ""
                    if img_el:
                        img_url = await img_el.get_attribute("data-src") or await img_el.get_attribute("src") or ""
                    area  = parse_area(raw)
                    price = parse_price(raw)
                    if not in_area_range(area): continue
                    results.append({
                        "id": make_id(href or raw[:80]),
                        "portal": self.PORTAL, "title": raw.split("\n")[0][:120],
                        "city": city, "address": city, "area_m2": area,
                        "price_chf": price, "ceiling_height_ok": check_ceiling_height(raw),
                        "image_url": img_url, "listing_url": href,
                        "description_snippet": raw[:300],
                    })
                except: pass
        except Exception as e:
            log.error("[%s] %s: %s", self.PORTAL, city, e)
        finally:
            await page.close()
        log.info("[%s] %s: %d gefunden", self.PORTAL, city, len(results))
        return results


class FlatfoxScraper:
    PORTAL = "Flatfox"
    def __init__(self, ctx): self.ctx = ctx

    async def scrape_city(self, city, lat, lon):
        results = []
        url  = (f"https://flatfox.ch/api/v1/listing/"
                f"?latitude={lat}&longitude={lon}&radius={RADIUS_KM*1000}"
                f"&listing_type=COMMERCIAL&floor_space_from={MIN_AREA}&floor_space_to={MAX_AREA}")
        page = await self.ctx.new_page()
        try:
            resp = await page.goto(url, wait_until="load", timeout=20000)
            if resp and resp.status == 200:
                data = await page.evaluate("() => JSON.parse(document.body.innerText)")
                for item in data.get("results", [])[:30]:
                    area  = item.get("floor_space")
                    price = item.get("rent_net")
                    if isinstance(price, str): price = parse_price(price)
                    if not in_area_range(area): continue
                    href    = f"https://flatfox.ch/de/wohnung/{item.get('pk','')}/"
                    desc    = item.get("description", "")
                    imgs    = item.get("images", [])
                    img_url = imgs[0].get("url","") if imgs else ""
                    results.append({
                        "id": make_id(str(item.get("pk", href))),
                        "portal": self.PORTAL, "title": item.get("title","Gewerbefläche")[:120],
                        "city": city, "address": item.get("street", city),
                        "area_m2": float(area) if area else None,
                        "price_chf": float(price) if price else None,
                        "ceiling_height_ok": check_ceiling_height(desc),
                        "image_url": img_url, "listing_url": href,
                        "description_snippet": desc[:300],
                    })
        except Exception as e:
            log.error("[%s] %s: %s", self.PORTAL, city, e)
        finally:
            await page.close()
        log.info("[%s] %s: %d gefunden", self.PORTAL, city, len(results))
        return results


# ─────────────────────────────────────────────
# HAUPT-CRAWL
# ─────────────────────────────────────────────
async def run_crawl():
    log.info("═══ Earlybirdie Crawl gestartet ═══")
    init_db()
    total_found = total_inserted = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-setuid-sandbox",
                  "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 900},
            locale="de-CH", timezone_id="Europe/Zurich",
        )
        await context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        )

        scrapers = [
            ImmoScoutScraper(context),
            HomegateScraper(context),
            FlatfoxScraper(context),
        ]

        for city, (lat, lon) in CITIES.items():
            for scraper in scrapers:
                try:
                    listings = await scraper.scrape_city(city, lat, lon)
                    total_found += len(listings)
                    for lst in listings:
                        if upsert_listing(lst):
                            total_inserted += 1
                    await asyncio.sleep(2.5)
                except Exception as e:
                    log.error("%s/%s: %s", scraper.PORTAL, city, e)

        await browser.close()

    log.info("═══ Fertig · %d gefunden · %d neu ═══", total_found, total_inserted)


if __name__ == "__main__":
    asyncio.run(run_crawl())
