"""
╔═══════════════════════════════════════════════════════════╗
║         EARLYBIRDIE — Real Estate Aggregator              ║
║         Streamlit Dashboard · app.py                      ║
╚═══════════════════════════════════════════════════════════╝
Startet mit: streamlit run app.py
"""

import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path

# ─────────────────────────────────────────────
# KONSTANTEN
# ─────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "earlybirdie.db"
PRIMARY_COLOR = "#004225"          # British Racing Green
ACCENT_COLOR  = "#00A651"          # helles Golfgrün für Hover
TEXT_LIGHT    = "#E8F5EE"
CREDENTIALS   = {"Earlybirdie": "Raumsuche2026"}

CITIES = [
    ("Luzern",      "🏔️"),
    ("Zug",         "🏛️"),
    ("Solothurn",   "🌿"),
    ("Basel",       "🎨"),
    ("Bern",        "🐻"),
    ("Thun",        "⛰️"),
    ("Winterthur",  "🏭"),
    ("Frauenfeld",  "🌾"),
]

# ─────────────────────────────────────────────
# SEITEN-KONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Earlybirdie · Raumsuche",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# GLOBALES CSS
# ─────────────────────────────────────────────
st.markdown(f"""
<style>
  /* ── Google Font ─────────────────────────── */
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500&display=swap');

  /* ── Reset & Basis ──────────────────────── */
  html, body, [class*="css"] {{
      font-family: 'DM Sans', sans-serif;
      background-color: #ffffff;
  }}
  .stApp {{
      background: #f4f7f5;
  }}

  /* ── Header-Banner ───────────────────────── */
  .eb-header {{
      background: linear-gradient(135deg, {PRIMARY_COLOR} 0%, #006638 60%, #009150 100%);
      border-radius: 16px;
      padding: 2.5rem 3rem;
      margin-bottom: 2rem;
      display: flex;
      align-items: center;
      gap: 1.5rem;
      box-shadow: 0 8px 32px rgba(0,66,37,0.25);
  }}
  .eb-header h1 {{
      font-family: 'Playfair Display', serif;
      font-size: 2.8rem;
      font-weight: 900;
      color: {TEXT_LIGHT};
      margin: 0;
      letter-spacing: -0.02em;
  }}
  .eb-header p {{
      color: rgba(232,245,238,0.75);
      font-size: 1rem;
      margin: 0.25rem 0 0;
      font-weight: 300;
  }}
  .eb-logo {{
      font-size: 3.5rem;
      line-height: 1;
  }}

  /* ── Stadt-Buttons ───────────────────────── */
  .city-grid {{
      display: grid;
      grid-template-columns: repeat(8, 1fr);
      gap: 0.75rem;
      margin-bottom: 2rem;
  }}
  .city-btn {{
      background: #ffffff;
      border: 2px solid {PRIMARY_COLOR};
      border-radius: 12px;
      padding: 1rem 0.5rem;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s ease;
      text-decoration: none;
      color: {PRIMARY_COLOR};
      font-weight: 500;
      font-size: 0.85rem;
  }}
  .city-btn:hover, .city-btn.active {{
      background: {PRIMARY_COLOR};
      color: white;
      transform: translateY(-3px);
      box-shadow: 0 6px 20px rgba(0,66,37,0.3);
  }}
  .city-btn .city-icon {{
      font-size: 1.8rem;
      display: block;
      margin-bottom: 0.4rem;
  }}

  /* ── Listing-Karte ───────────────────────── */
  .listing-card {{
      background: #ffffff;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 2px 16px rgba(0,0,0,0.08);
      transition: transform 0.25s ease, box-shadow 0.25s ease;
      height: 100%;
      display: flex;
      flex-direction: column;
      border: 1px solid rgba(0,66,37,0.08);
  }}
  .listing-card:hover {{
      transform: translateY(-5px);
      box-shadow: 0 12px 40px rgba(0,66,37,0.18);
  }}
  .card-img-wrap {{
      width: 100%;
      height: 190px;
      overflow: hidden;
      background: #e8f0eb;
      position: relative;
  }}
  .card-img-wrap img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
  }}
  .card-img-placeholder {{
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #e8f0eb, #c8ddd0);
      font-size: 3rem;
      color: {PRIMARY_COLOR};
  }}
  .card-badge {{
      position: absolute;
      top: 10px;
      right: 10px;
      background: {PRIMARY_COLOR};
      color: white;
      font-size: 0.72rem;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 20px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
  }}
  .card-body {{
      padding: 1.1rem 1.2rem 1.3rem;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
  }}
  .card-title {{
      font-family: 'Playfair Display', serif;
      font-size: 1.05rem;
      font-weight: 700;
      color: #1a1a1a;
      line-height: 1.3;
      margin: 0;
  }}
  .card-location {{
      font-size: 0.82rem;
      color: #666;
      display: flex;
      align-items: center;
      gap: 0.3rem;
  }}
  .card-meta {{
      display: flex;
      gap: 1rem;
      margin-top: 0.5rem;
  }}
  .card-chip {{
      background: #f0f7f3;
      border: 1px solid #c8ddd0;
      border-radius: 8px;
      padding: 0.25rem 0.7rem;
      font-size: 0.8rem;
      font-weight: 500;
      color: {PRIMARY_COLOR};
  }}
  .card-price {{
      font-size: 1.15rem;
      font-weight: 700;
      color: {PRIMARY_COLOR};
      margin-top: auto;
      padding-top: 0.6rem;
  }}
  .card-link-btn {{
      display: block;
      background: {PRIMARY_COLOR};
      color: white !important;
      text-align: center;
      padding: 0.7rem;
      text-decoration: none !important;
      font-weight: 600;
      font-size: 0.88rem;
      border-radius: 0 0 14px 14px;
      transition: background 0.2s;
      letter-spacing: 0.03em;
  }}
  .card-link-btn:hover {{
      background: #006638;
      color: white !important;
  }}
  .card-high-ceiling {{
      background: #fffbe6;
      border: 1px solid #f0c040;
      border-radius: 6px;
      padding: 0.2rem 0.6rem;
      font-size: 0.75rem;
      color: #7a5c00;
      font-weight: 500;
  }}

  /* ── Sidebar ──────────────────────────────── */
  [data-testid="stSidebar"] {{
      background: {PRIMARY_COLOR} !important;
  }}
  [data-testid="stSidebar"] * {{
      color: {TEXT_LIGHT} !important;
  }}
  [data-testid="stSidebar"] .stSlider > div > div > div > div {{
      background: {ACCENT_COLOR} !important;
  }}
  [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
      font-family: 'Playfair Display', serif !important;
  }}

  /* ── Login-Maske ─────────────────────────── */
  .login-wrap {{
      max-width: 400px;
      margin: 6rem auto 0;
      background: white;
      border-radius: 20px;
      padding: 2.5rem;
      box-shadow: 0 8px 40px rgba(0,66,37,0.18);
      border-top: 6px solid {PRIMARY_COLOR};
  }}
  .login-wrap h2 {{
      font-family: 'Playfair Display', serif;
      color: {PRIMARY_COLOR};
      font-size: 1.8rem;
      margin-bottom: 0.3rem;
  }}

  /* ── Status-Bar ───────────────────────────── */
  .status-bar {{
      background: white;
      border: 1px solid #dde8e2;
      border-radius: 10px;
      padding: 0.7rem 1.2rem;
      display: flex;
      align-items: center;
      gap: 1rem;
      margin-bottom: 1.5rem;
      font-size: 0.88rem;
      color: #444;
  }}
  .status-dot {{
      width: 10px; height: 10px;
      border-radius: 50%;
      background: {ACCENT_COLOR};
      animation: pulse 2s infinite;
  }}
  @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50%       {{ opacity: 0.6; transform: scale(1.3); }}
  }}

  /* Streamlit Buttons überschreiben */
  .stButton > button {{
      background: {PRIMARY_COLOR} !important;
      color: white !important;
      border: none !important;
      border-radius: 10px !important;
      font-weight: 600 !important;
  }}
  .stButton > button:hover {{
      background: #006638 !important;
  }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────────
def get_db_connection():
    """Öffnet eine SQLite-Verbindung und gibt sie zurück."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_listings(city: str | None = None,
                  min_area: float = 0,
                  max_area: float = 500,
                  min_price: float = 0,
                  max_price: float = 20000,
                  sort_by: str = "scraped_at") -> list[dict]:
    """Lädt Inserate aus SQLite mit Filterparametern."""
    if not DB_PATH.exists():
        return []
    conn = get_db_connection()
    query = """
        SELECT id, title, city, address, area_m2, price_chf,
               ceiling_height_ok, image_url, listing_url,
               portal, scraped_at, description_snippet
        FROM listings
        WHERE area_m2 BETWEEN ? AND ?
          AND (price_chf BETWEEN ? AND ? OR price_chf IS NULL)
    """
    params: list = [min_area, max_area, min_price, max_price]
    if city:
        query += " AND city = ?"
        params.append(city)
    sort_map = {
        "Neueste zuerst":   "scraped_at DESC",
        "Fläche aufsteig.": "area_m2 ASC",
        "Fläche absteig.":  "area_m2 DESC",
        "Preis aufsteig.":  "price_chf ASC",
        "Preis absteig.":   "price_chf DESC",
    }
    query += f" ORDER BY {sort_map.get(sort_by, 'scraped_at DESC')}"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_listings() -> int:
    if not DB_PATH.exists():
        return 0
    conn = get_db_connection()
    n = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
    conn.close()
    return n


def render_card(listing: dict):
    """Rendert eine einzelne Listing-Karte als HTML."""
    img_tag = (
        f'<img src="{listing["image_url"]}" alt="Vorschau" loading="lazy" '
        f'onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'">'
        f'<div class="card-img-placeholder" style="display:none;">🏢</div>'
        if listing.get("image_url")
        else '<div class="card-img-placeholder">🏢</div>'
    )
    badge = f'<span class="card-badge">{listing.get("portal","Portal")}</span>'
    ceiling = (
        '<span class="card-high-ceiling">⬆️ Deckenhöhe ≥ 3 m</span>'
        if listing.get("ceiling_height_ok") else ""
    )
    area  = f'{listing["area_m2"]} m²' if listing.get("area_m2") else "–"
    price = (
        f'CHF {listing["price_chf"]:,.0f} / Mt.'
        if listing.get("price_chf") else "Preis auf Anfrage"
    )
    title   = listing.get("title", "Gewerbefläche")
    address = listing.get("address") or listing.get("city", "")
    snippet = listing.get("description_snippet", "")
    link    = listing.get("listing_url", "#")

    html = f"""
    <div class="listing-card">
      <div class="card-img-wrap">
        {img_tag}
        {badge}
      </div>
      <div class="card-body">
        <p class="card-title">{title}</p>
        <p class="card-location">📍 {address}</p>
        <div class="card-meta">
          <span class="card-chip">📐 {area}</span>
          {ceiling}
        </div>
        <p style="font-size:0.78rem;color:#888;margin-top:0.4rem;line-height:1.4">{snippet[:120]}...</p>
        <p class="card-price">{price}</p>
      </div>
      <a href="{link}" target="_blank" rel="noopener" class="card-link-btn">
        Details &amp; Link →
      </a>
    </div>
    """
    return html


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────
def show_login():
    st.markdown("""
    <div class="login-wrap">
      <div style="font-size:2.5rem;text-align:center;margin-bottom:0.5rem">⛳</div>
      <h2 style="text-align:center">Earlybirdie</h2>
      <p style="text-align:center;color:#888;margin-bottom:1.5rem;font-size:0.9rem">
        Indoorgolf-Raumsuche Schweiz
      </p>
    </div>
    """, unsafe_allow_html=True)
    with st.form("login_form"):
        username = st.text_input("Benutzername")
        password = st.text_input("Passwort", type="password")
        submit   = st.form_submit_button("Einloggen", use_container_width=True)
        if submit:
            if CREDENTIALS.get(username) == password:
                st.session_state["logged_in"] = True
                st.rerun()
            else:
                st.error("Ungültige Zugangsdaten.")


# ─────────────────────────────────────────────
# HAUPT-APP
# ─────────────────────────────────────────────
def show_app():
    # ── Header ─────────────────────────────────
    st.markdown("""
    <div class="eb-header">
      <div class="eb-logo">⛳</div>
      <div>
        <h1>Earlybirdie</h1>
        <p>Indoorgolf-Flächen Aggregator · Schweiz · 50–120 m² · Gewerbeflächen</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Status-Bar ──────────────────────────────
    total = count_listings()
    st.markdown(f"""
    <div class="status-bar">
      <div class="status-dot"></div>
      <strong>{total}</strong> Inserate in der Datenbank
      &nbsp;·&nbsp; Nächster Crawl: täglich 12:00 Uhr
      &nbsp;·&nbsp; Portale: ImmoScout24, Homegate, Comparis, Flatfox
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar (Filter) ────────────────────────
    with st.sidebar:
        st.markdown("## ⛳ Filter")
        st.markdown("---")

        sort_by = st.selectbox("Sortierung", [
            "Neueste zuerst",
            "Fläche aufsteig.",
            "Fläche absteig.",
            "Preis aufsteig.",
            "Preis absteig.",
        ])
        st.markdown("### 📐 Fläche (m²)")
        area_range = st.slider("", 50, 300, (50, 120), step=5)

        st.markdown("### 💰 Mietpreis (CHF/Mt.)")
        price_range = st.slider("", 0, 15000, (0, 8000), step=250)

        st.markdown("### 🏙️ Stadt")
        city_filter = st.selectbox(
            "",
            ["Alle Städte"] + [c[0] for c in CITIES]
        )
        city_val = None if city_filter == "Alle Städte" else city_filter

        st.markdown("---")
        if st.button("🔄 Datenbank aktualisieren"):
            st.info("Starte Crawler … (siehe Terminal)")
            import subprocess
            subprocess.Popen(["python3", str(Path(__file__).parent / "crawler.py")])

        st.markdown("---")
        st.markdown("**Earlybirdie v1.0**")
        st.markdown("_Real Estate Aggregator_")
        if st.button("🚪 Logout"):
            st.session_state["logged_in"] = False
            st.rerun()

    # ── Stadtauswahl-Grid ───────────────────────
    st.markdown("### 🏙️ Stadt auswählen")
    cols = st.columns(8)
    for i, (city_name, icon) in enumerate(CITIES):
        with cols[i]:
            active = city_filter == city_name
            btn_label = f"{icon}\n{city_name}"
            if st.button(btn_label, key=f"city_{city_name}",
                         use_container_width=True,
                         type="primary" if active else "secondary"):
                # Stadtfilter via session state setzen
                st.session_state["selected_city"] = city_name
                st.rerun()

    # Session-State-City hat Vorrang vor Sidebar
    if "selected_city" in st.session_state:
        city_val = st.session_state["selected_city"]

    # ── Listings laden ──────────────────────────
    listings = load_listings(
        city=city_val,
        min_area=area_range[0],
        max_area=area_range[1],
        min_price=price_range[0],
        max_price=price_range[1],
        sort_by=sort_by,
    )

    # ── Ergebnis-Header ─────────────────────────
    city_label = city_val if city_val else "Alle Städte"
    st.markdown(f"### 🏢 {len(listings)} Ergebnis{'se' if len(listings)!=1 else ''} — {city_label}")

    if not listings:
        if total == 0:
            st.info(
                "📭 Die Datenbank ist noch leer.\n\n"
                "Starte zuerst `python3 crawler.py` um Daten zu laden,\n"
                "oder klicke auf **🔄 Datenbank aktualisieren** in der Sidebar."
            )
        else:
            st.warning("Keine Inserate passen auf deine aktuellen Filter.")
        return

    # ── Karten-Grid (3 Spalten) ─────────────────
    cols_per_row = 3
    for i in range(0, len(listings), cols_per_row):
        row_listings = listings[i:i+cols_per_row]
        cols = st.columns(cols_per_row)
        for col, listing in zip(cols, row_listings):
            with col:
                st.markdown(render_card(listing), unsafe_allow_html=True)
                st.markdown("")   # Abstand


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if st.session_state["logged_in"]:
    show_app()
else:
    show_login()
