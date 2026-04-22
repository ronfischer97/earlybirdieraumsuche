"""
EARLYBIRDIE — Indoorgolf Raumsuche Schweiz
Smart Link Hub · app.py v2
"""

import streamlit as st

PRIMARY   = "#004225"
LIGHT     = "#E8F5EE"
ACCENT    = "#00A651"
CREDENTIALS = {"Earlybirdie": "Raumsuche2026"}

CITIES = [
    {
        "name": "Luzern", "icon": "🏔️",
        "portale": [
            {"name": "ImmoScout24", "color": "#E8041B", "url": "https://www.immoscout24.ch/de/gewerbe/mieten/ort-luzern?r=5&nrf=50&prf=120"},
            {"name": "Homegate",    "color": "#FF6600", "url": "https://www.homegate.ch/mieten/gewerbeobjekte/ort-luzern?ep=120&sp=50"},
            {"name": "Flatfox",     "color": "#0066CC", "url": "https://flatfox.ch/de/suche/?east=8.4&west=8.2&north=47.1&south=47.0&listing_type=COMMERCIAL"},
            {"name": "Comparis",    "color": "#009FE3", "url": "https://www.comparis.ch/immobilien/mieten/gewerbe?ort=Luzern&umkreis=5"},
        ],
    },
    {
        "name": "Zug", "icon": "🏛️",
        "portale": [
            {"name": "ImmoScout24", "color": "#E8041B", "url": "https://www.immoscout24.ch/de/gewerbe/mieten/ort-zug?r=5&nrf=50&prf=120"},
            {"name": "Homegate",    "color": "#FF6600", "url": "https://www.homegate.ch/mieten/gewerbeobjekte/ort-zug?ep=120&sp=50"},
            {"name": "Flatfox",     "color": "#0066CC", "url": "https://flatfox.ch/de/suche/?east=8.6&west=8.4&north=47.2&south=47.1&listing_type=COMMERCIAL"},
            {"name": "Comparis",    "color": "#009FE3", "url": "https://www.comparis.ch/immobilien/mieten/gewerbe?ort=Zug&umkreis=5"},
        ],
    },
    {
        "name": "Solothurn", "icon": "🌿",
        "portale": [
            {"name": "ImmoScout24", "color": "#E8041B", "url": "https://www.immoscout24.ch/de/gewerbe/mieten/ort-solothurn?r=5&nrf=50&prf=120"},
            {"name": "Homegate",    "color": "#FF6600", "url": "https://www.homegate.ch/mieten/gewerbeobjekte/ort-solothurn?ep=120&sp=50"},
            {"name": "Flatfox",     "color": "#0066CC", "url": "https://flatfox.ch/de/suche/?east=7.6&west=7.4&north=47.3&south=47.1&listing_type=COMMERCIAL"},
            {"name": "Comparis",    "color": "#009FE3", "url": "https://www.comparis.ch/immobilien/mieten/gewerbe?ort=Solothurn&umkreis=5"},
        ],
    },
    {
        "name": "Basel", "icon": "🎨",
        "portale": [
            {"name": "ImmoScout24", "color": "#E8041B", "url": "https://www.immoscout24.ch/de/gewerbe/mieten/ort-basel?r=5&nrf=50&prf=120"},
            {"name": "Homegate",    "color": "#FF6600", "url": "https://www.homegate.ch/mieten/gewerbeobjekte/ort-basel?ep=120&sp=50"},
            {"name": "Flatfox",     "color": "#0066CC", "url": "https://flatfox.ch/de/suche/?east=7.7&west=7.5&north=47.6&south=47.5&listing_type=COMMERCIAL"},
            {"name": "Comparis",    "color": "#009FE3", "url": "https://www.comparis.ch/immobilien/mieten/gewerbe?ort=Basel&umkreis=5"},
        ],
    },
    {
        "name": "Bern", "icon": "🐻",
        "portale": [
            {"name": "ImmoScout24", "color": "#E8041B", "url": "https://www.immoscout24.ch/de/gewerbe/mieten/ort-bern?r=5&nrf=50&prf=120"},
            {"name": "Homegate",    "color": "#FF6600", "url": "https://www.homegate.ch/mieten/gewerbeobjekte/ort-bern?ep=120&sp=50"},
            {"name": "Flatfox",     "color": "#0066CC", "url": "https://flatfox.ch/de/suche/?east=7.5&west=7.3&north=47.0&south=46.9&listing_type=COMMERCIAL"},
            {"name": "Comparis",    "color": "#009FE3", "url": "https://www.comparis.ch/immobilien/mieten/gewerbe?ort=Bern&umkreis=5"},
        ],
    },
    {
        "name": "Thun", "icon": "⛰️",
        "portale": [
            {"name": "ImmoScout24", "color": "#E8041B", "url": "https://www.immoscout24.ch/de/gewerbe/mieten/ort-thun?r=5&nrf=50&prf=120"},
            {"name": "Homegate",    "color": "#FF6600", "url": "https://www.homegate.ch/mieten/gewerbeobjekte/ort-thun?ep=120&sp=50"},
            {"name": "Flatfox",     "color": "#0066CC", "url": "https://flatfox.ch/de/suche/?east=7.7&west=7.5&north=46.8&south=46.7&listing_type=COMMERCIAL"},
            {"name": "Comparis",    "color": "#009FE3", "url": "https://www.comparis.ch/immobilien/mieten/gewerbe?ort=Thun&umkreis=5"},
        ],
    },
    {
        "name": "Winterthur", "icon": "🏭",
        "portale": [
            {"name": "ImmoScout24", "color": "#E8041B", "url": "https://www.immoscout24.ch/de/gewerbe/mieten/ort-winterthur?r=5&nrf=50&prf=120"},
            {"name": "Homegate",    "color": "#FF6600", "url": "https://www.homegate.ch/mieten/gewerbeobjekte/ort-winterthur?ep=120&sp=50"},
            {"name": "Flatfox",     "color": "#0066CC", "url": "https://flatfox.ch/de/suche/?east=8.8&west=8.6&north=47.6&south=47.4&listing_type=COMMERCIAL"},
            {"name": "Comparis",    "color": "#009FE3", "url": "https://www.comparis.ch/immobilien/mieten/gewerbe?ort=Winterthur&umkreis=5"},
        ],
    },
    {
        "name": "Frauenfeld", "icon": "🌾",
        "portale": [
            {"name": "ImmoScout24", "color": "#E8041B", "url": "https://www.immoscout24.ch/de/gewerbe/mieten/ort-frauenfeld?r=5&nrf=50&prf=120"},
            {"name": "Homegate",    "color": "#FF6600", "url": "https://www.homegate.ch/mieten/gewerbeobjekte/ort-frauenfeld?ep=120&sp=50"},
            {"name": "Flatfox",     "color": "#0066CC", "url": "https://flatfox.ch/de/suche/?east=9.0&west=8.8&north=47.6&south=47.5&listing_type=COMMERCIAL"},
            {"name": "Comparis",    "color": "#009FE3", "url": "https://www.comparis.ch/immobilien/mieten/gewerbe?ort=Frauenfeld&umkreis=5"},
        ],
    },
]

st.set_page_config(page_title="Earlybirdie · Raumsuche", page_icon="⛳", layout="wide")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif; }}
.stApp {{ background: #f4f7f5; }}
.eb-header {{
    background: linear-gradient(135deg, {PRIMARY} 0%, #006638 60%, #009150 100%);
    border-radius: 20px; padding: 2.5rem 3rem; margin-bottom: 2rem;
    display: flex; align-items: center; gap: 1.5rem;
    box-shadow: 0 8px 32px rgba(0,66,37,0.25);
}}
.eb-header h1 {{
    font-family: 'Playfair Display', serif; font-size: 2.8rem;
    font-weight: 900; color: {LIGHT}; margin: 0;
}}
.eb-header p {{ color: rgba(232,245,238,0.75); font-size: 1rem; margin: 0.25rem 0 0; }}
.eb-logo {{ font-size: 3.5rem; line-height: 1; }}
.criteria-box {{
    background: white; border-radius: 14px; padding: 1.2rem 1.5rem;
    margin-bottom: 2rem; display: flex; gap: 2rem; flex-wrap: wrap;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06); border: 1px solid #e0ede6;
}}
.criteria-item {{ text-align: center; }}
.criteria-value {{ font-family: 'Playfair Display', serif; font-size: 1.5rem; font-weight: 700; color: {PRIMARY}; }}
.criteria-label {{ font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; }}
.info-banner {{
    background: white; border-left: 4px solid {ACCENT};
    border-radius: 10px; padding: 1rem 1.5rem; margin-bottom: 2rem;
    font-size: 0.9rem; color: #444; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}}
.city-card {{
    background: white; border-radius: 18px; padding: 1.5rem;
    box-shadow: 0 2px 16px rgba(0,0,0,0.07); border: 1px solid rgba(0,66,37,0.08);
    margin-bottom: 1.5rem;
}}
.city-header {{
    display: flex; align-items: center; gap: 0.75rem;
    margin-bottom: 1rem; padding-bottom: 0.8rem; border-bottom: 2px solid #f0f7f3;
}}
.city-icon {{ font-size: 1.8rem; }}
.city-name {{ font-family: 'Playfair Display', serif; font-size: 1.2rem; font-weight: 700; color: {PRIMARY}; margin: 0; }}
[data-testid="stSidebar"] {{ background: {PRIMARY} !important; }}
[data-testid="stSidebar"] * {{ color: {LIGHT} !important; }}
.stButton > button {{
    background: {PRIMARY} !important; color: white !important;
    border: none !important; border-radius: 10px !important; font-weight: 600 !important;
}}
</style>
""", unsafe_allow_html=True)


def show_login():
    st.markdown(f"""
    <div style="max-width:400px;margin:6rem auto 0;background:white;border-radius:20px;
                padding:2.5rem;box-shadow:0 8px 40px rgba(0,66,37,0.18);border-top:6px solid {PRIMARY}">
      <div style="font-size:2.5rem;text-align:center">⛳</div>
      <h2 style="text-align:center;font-family:'Playfair Display',serif;color:{PRIMARY}">Earlybirdie</h2>
      <p style="text-align:center;color:#888;font-size:0.9rem">Indoorgolf-Raumsuche Schweiz</p>
    </div>
    """, unsafe_allow_html=True)
    with st.form("login"):
        user = st.text_input("Benutzername")
        pw   = st.text_input("Passwort", type="password")
        if st.form_submit_button("Einloggen", use_container_width=True):
            if CREDENTIALS.get(user) == pw:
                st.session_state["logged_in"] = True
                st.rerun()
            else:
                st.error("Ungültige Zugangsdaten.")


def show_app():
    st.markdown("""
    <div class="eb-header">
      <div class="eb-logo">⛳</div>
      <div>
        <h1>Earlybirdie</h1>
        <p>Indoorgolf-Flächen Aggregator · Schweiz · Direkt zu den Inseraten</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="criteria-box">
      <div class="criteria-item"><div class="criteria-value">50–120</div><div class="criteria-label">m² Fläche</div></div>
      <div class="criteria-item"><div class="criteria-value">≥ 3m</div><div class="criteria-label">Deckenhöhe</div></div>
      <div class="criteria-item"><div class="criteria-value">5 km</div><div class="criteria-label">Radius</div></div>
      <div class="criteria-item"><div class="criteria-value">8</div><div class="criteria-label">Städte</div></div>
      <div class="criteria-item"><div class="criteria-value">4</div><div class="criteria-label">Portale</div></div>
    </div>
    <div class="info-banner">
      💡 <strong>So funktioniert's:</strong> Klicke auf einen Portal-Button — die Suche öffnet sich direkt mit den richtigen Filtern. Du siehst immer die <strong>aktuellsten Inserate</strong>.
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("## ⛳ Earlybirdie")
        st.markdown("---")
        st.markdown("**Fläche:** 50–120 m²")
        st.markdown("**Typ:** Gewerbe / Büro")
        st.markdown("**Radius:** 5 km")
        st.markdown("**Deckenhöhe:** ≥ 3 m")
        st.markdown("---")
        if st.button("🚪 Logout"):
            st.session_state["logged_in"] = False
            st.rerun()

    st.markdown("### 🏙️ Stadt wählen — Portal öffnen")

    cols = st.columns(4)
    for i, city in enumerate(CITIES):
        with cols[i % 4]:
            # Stadt-Header
            st.markdown(f"""
            <div class="city-card">
              <div class="city-header">
                <span class="city-icon">{city['icon']}</span>
                <p class="city-name">{city['name']}</p>
              </div>
            </div>
            """, unsafe_allow_html=True)
            # Portal-Buttons mit st.link_button (native Streamlit)
            for p in city["portale"]:
                st.link_button(
                    f"● {p['name']}  ↗",
                    p["url"],
                    use_container_width=True,
                )
            st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 💡 Tipps")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("**🏗️ Deckenhöhe prüfen**\n\nSuche nach: *Raumhöhe, Deckenhöhe, Hallencharakter, Loft*")
    with c2:
        st.info("**📐 Fläche**\n\n1 Bahn: ~32 m²\n2 Bahnen: ~65 m²\n3 Bahnen: ~95 m²")
    with c3:
        st.info("**💰 Preise CH**\n\nGünstig: CHF 80–120/m²/Jahr\nMittel: CHF 120–200/m²/Jahr")


if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if st.session_state["logged_in"]:
    show_app()
else:
    show_login()
