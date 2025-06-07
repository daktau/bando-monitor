import os
import asyncio
from bs4 import BeautifulSoup
from email.message import EmailMessage
import smtplib
import datetime
from playwright.async_api import async_playwright

# --- SETTINGS ---
URL = "https://www.trasparenzascuole.it/Public/APDPublic_ExtV2.aspx?CF=91040430190"
KEYWORDS = [
    "madrelingua",
    "inglese",
    "liquidazione",
    "compensi",
    "DETERMINA_A_CONTRARRE_PER_ACQUISTO_N._24_PC_PER_LAB._6.pdf"
]

EMAIL_SENDER = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
EMAIL_RECEIVER = os.environ["EMAIL_RECEIVER"]

# --- PARSE & MATCH ---
def parse_and_collect(html):
    matches = []
    soup = BeautifulSoup(html, "html.parser")

    # DEBUG: dump the first 2000 characters of text seen by the scraper
    print("\n--- PAGE TEXT START ---\n")
    print(soup.get_text(strip=True)[:2000])
    print("\n--- PAGE TEXT END ---\n")

    for text in soup.find_all(string=True):
        if any(keyword.lower() in text.lower() for keyword in KEYWORDS):
            cleaned = text.strip()
            if cleaned and cleaned not in matches:
                matches.append(cleaned)

    print(f"✔️ Found {len(matches)} match(es): {matches}")
    return matches

# --- SCRAPE FUNCTION ---
async def scrape_pages():
    all_matches = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        # Wait 5 seconds to allow JS to render the table
        await page.wait_for_timeout(5000)

        html = await page.content()
        all_matches.extend(parse_and_collect(html))

        # Pagination logic can go here if needed — skipping for now

        await browser.close()
    return list(set(all_matches))

# --- EMAIL FUNCTION ---
def send_email(matches):
    if matches:
        subject = f"[Monitor] FOUND matches – {datetime.datetime.now():%Y-%m-%d %H:%M}"
        body = "\n\n".join(matches)
    else:
        subject = f"[Monitor] No matches found – {datetime.datetime.now():%Y-%m-%d %H:%M}"
        body = "The monitoring script ran successfully, but found no keyword matches on the site."

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)

    print(f"📧 Email sent to {EMAIL_RECEIVER}. Matches: {len(matches)}")

# --- MAIN ---
if __name__ == "__main__":
    try:
        found_matches = asyncio.run(scrape_pages())
        send_email(found_matches)
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
