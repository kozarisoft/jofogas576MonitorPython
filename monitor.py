import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import sys

URL = "https://www.jofogas.hu/magyarorszag?q=576%20kbyte"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
}

MAGYAR_HONAPOK = {
    "jan": 1, "feb": 2, "már": 3, "ápr": 4, "máj": 5, "jún": 6,
    "júl": 7, "aug": 8, "szep": 9, "okt": 10, "nov": 11, "dec": 12
}

GMAIL_USER  = os.environ["GMAIL_USER"]
GMAIL_PASS  = os.environ["GMAIL_PASS"]
NOTIFY_TO   = os.environ["NOTIFY_TO"]
DAYS_LIMIT  = int(os.environ.get("DAYS_LIMIT", "7"))


def parse_date(date_str):
    """'ápr 16., 07:39' -> datetime"""
    m = re.match(r"(\w+)\s+(\d+)\.,\s+\d+:\d+", date_str.strip())
    if not m:
        return None
    honap_str = m.group(1)[:3].lower()
    nap = int(m.group(2))
    honap = MAGYAR_HONAPOK.get(honap_str)
    if not honap:
        return None
    ev = datetime.now().year
    return datetime(ev, honap, nap)


def scrape():
    """Visszaadja az első találat (cím, link, dátum_str, datetime) tuple-t."""
    r = requests.get(URL, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # --- első hirdetés linkje + címe ---
    first_link_tag = soup.select_one("a[href*='/baranya/'], a[href*='/budapest/'], "
                                     "a[href*='/heves/'], a[href*='/pest/'], "
                                     "a[href*='/gyor'], a[href*='.jofogas.hu/']")
    # Általánosabb fallback: bármely hirdetés-link (tartalmaz .htm-et)
    if not first_link_tag:
        first_link_tag = soup.find("a", href=re.compile(r"jofogas\.hu/.+\.htm"))

    title = first_link_tag.get_text(strip=True) if first_link_tag else "N/A"
    link  = URL #first_link_tag["href"] if first_link_tag else URL #ez szar kiszedtem

    # --- első dátum az oldalon ---
    # Formátum: "ápr 16., 07:39" vagy "több, mint egy hónapja"
    date_pattern = re.compile(r"[a-záéíóöőúüű]+\s+\d+\.,\s+\d+:\d+")
    date_match = date_pattern.search(r.text)
    date_str = date_match.group(0) if date_match else None
    parsed   = parse_date(date_str) if date_str else None

    return title, link, date_str, parsed


def send_email(title, link, date_str, parsed):
    days_ago = (datetime.now() - parsed).days if parsed else "?"

    # subject = f"[Jófogás SCRIPT] Friss 576 Kbyte hirdetés: {title[:60]}"
    subject = "[Jófogás SCRIPT] Friss 576 Kbyte magazin hirdetés!"
    body = f"""Szia!

Új hirdetést találtam a Jófogáson, ami {days_ago} napos (határon belül van).

Cím:   {title}
Link:  {link}
Dátum: {date_str}

---
(Automatikus értesítő – GitHub Actions)
"""
    msg = MIMEMultipart()
    msg["From"]    = GMAIL_USER
    msg["To"]      = NOTIFY_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_USER, GMAIL_PASS)
        s.sendmail(GMAIL_USER, NOTIFY_TO, msg.as_string())
    print(f"✅ Email elküldve: {subject}")


def main():
    print(f"Lekérés: {URL}")
    title, link, date_str, parsed = scrape()
    print(f"Első találat: {title}")
    print(f"Link:         {link}")
    print(f"Dátum string: {date_str}")
    print(f"Parsed dátum: {parsed}")

    if not parsed:
        print("⚠️  Nem sikerült dátumot értelmezni – nincs riasztás.")
        sys.exit(0)

    days_diff = (datetime.now() - parsed).days
    print(f"Dátum kora:   {days_diff} nap")

    if days_diff <= DAYS_LIMIT:
        print(f"🔔 Dátumon belül ({DAYS_LIMIT} napon belül) – email küldése...")
        send_email(title, link, date_str, parsed)
    else:
        print(f"ℹ️  Dátum régebbi mint {DAYS_LIMIT} nap – nincs riasztás.")


if __name__ == "__main__":
    main()
