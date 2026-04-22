# ⛳ Earlybirdie — Indoorgolf Raumsuche Schweiz

**Real Estate Aggregator · Playwright + Streamlit + SQLite**

---

## 📁 Projektstruktur

```
earlybirdie/
├── app.py            ← Streamlit-Dashboard (UI)
├── crawler.py        ← Playwright-Scraper (Datenbeschaffung)
├── requirements.txt  ← Python-Abhängigkeiten
├── earlybirdie.db    ← SQLite-Datenbank (wird automatisch erstellt)
└── crawler.log       ← Logfile (wird automatisch erstellt)
```

---

## 🚀 Installation (Ubuntu/Linux)

### 1. Python-Pakete installieren

```bash
cd /pfad/zu/earlybirdie
pip install -r requirements.txt
```

### 2. Playwright-Browser installieren

```bash
playwright install chromium
playwright install-deps chromium
```

### 3. Ersten Crawl starten (Datenbank befüllen)

```bash
python3 crawler.py
```

### 4. Dashboard starten

```bash
streamlit run app.py
```

Browser öffnet sich automatisch auf `http://localhost:8501`

---

## 🔐 Login-Daten

| Feld       | Wert           |
|------------|----------------|
| Benutzer   | `Earlybirdie`  |
| Passwort   | `Raumsuche2026`|

---

## ⏰ Cron-Job einrichten (täglich 12:00 Uhr)

### Schritt 1: Crontab öffnen

```bash
crontab -e
```

### Schritt 2: Diese Zeile am Ende hinzufügen

```bash
00 12 * * * /usr/bin/python3 /pfad/zu/earlybirdie/crawler.py >> /pfad/zu/earlybirdie/crawler.log 2>&1
```

**Erklärung der Cron-Syntax:**

| Teil         | Bedeutung                                |
|--------------|------------------------------------------|
| `00`         | Minute 0                                 |
| `12`         | Stunde 12 (= 12:00 Uhr Mittag)          |
| `* * *`      | Jeden Tag, jeden Monat, jeden Wochentag |
| `/usr/bin/python3` | Python-Interpreter                |
| `>> .../crawler.log 2>&1` | Log-Output anhängen         |

### Schritt 3: Pfad anpassen!

Ersetze `/pfad/zu/earlybirdie/` mit dem echten Pfad, z. B.:

```bash
00 12 * * * /usr/bin/python3 /home/ubuntu/earlybirdie/crawler.py >> /home/ubuntu/earlybirdie/crawler.log 2>&1
```

### Schritt 4: Python-Pfad prüfen

```bash
which python3
# Ausgabe z.B.: /usr/bin/python3
```

### Schritt 5: Cron-Job testen

```bash
# Manuell starten:
/usr/bin/python3 /pfad/zu/earlybirdie/crawler.py

# Log prüfen:
tail -f /pfad/zu/earlybirdie/crawler.log
```

---

## 🏙️ Gesuchte Städte

Luzern · Zug · Solothurn · Basel · Bern · Thun · Winterthur · Frauenfeld

---

## 🔍 Suchkriterien

- **Fläche:** 50 – 120 m²
- **Typ:** Gewerbeflächen
- **Radius:** 5 km ab Stadtzentrum
- **Deckenhöhe:** Keyword-Analyse (≥ 3 m bevorzugt)
- **Portale:** ImmoScout24 · Homegate · Flatfox · Comparis

---

## 💡 Tipps

- Die Datenbank wird automatisch mit dem ersten `python3 crawler.py` erstellt
- Das Dashboard kann auch laufen, wenn die DB noch leer ist
- Der Crawler speichert **keine Bilder lokal** — nur die Bild-URLs
- Für Server-Betrieb: `streamlit run app.py --server.port 8501 --server.headless true`

---

## 🛡️ Rechtlicher Hinweis

Dieser Crawler liest öffentlich zugängliche Informationen. 
Bitte prüfe die `robots.txt` und die AGB der jeweiligen Portale.
Setze angemessene Pausen zwischen den Requests (bereits im Code eingebaut: ~2,5 s).
