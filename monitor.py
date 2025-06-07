import os
import asyncio
import datetime
import smtplib
from bs4 import BeautifulSoup
from email.message import EmailMessage
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# --- CONFIGURATION ---
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

# --- HTML SCRAPING & MATCHING ---
def parse_and_collect(html):
    soup = BeautifulSoup(html, "html.parser")
    matches = []

    print("\n--- PAGE TEXT START ---\n")
    print(soup.get_text(strip=True)[:2000])  # Show first 2000 chars
    print("\n--- PAGE TEXT END ---\n")

    for text in soup.find_all(string=True):
        if any(k.lower() in text.lower() for k in KEYWORDS):
            cleaned = text.strip()
            if cleaned and cleaned not in matches:
                matches.append(cleaned)

    print(f"✔️ Found {len(matches)} match(es): {matches}")
    return matches

# --- SCRAPER FUNCTION ---
async def scrape_pages():
    all_matches = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await stealth_async(page)  # 👈 Cloudflare stealth bypass

        print("▶️ Navigating to site...")
        await page.goto(URL, timeout=90000)

        try:
            # Wait for real page content
            await page.wait_for_selector("text=Protocollo", timeout=20000)
        except:
            print("⚠️ Timed out waiting for page content. Cloudflare may still be blocking.")

        html = await page.content()
        all_matches.extend(parse_and_collect(html))
        await browser.close()

    return list(set(all_matches))

# --- EMAIL SENDER ---
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
