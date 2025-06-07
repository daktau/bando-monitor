import os
import asyncio
from bs4 import BeautifulSoup
from email.message import EmailMessage
import smtplib
import datetime
from playwright.async_api import async_playwright

# --- SETTINGS ---
URL = "https://www.trasparenzascuole.it/Public/APDPublic_ExtV2.aspx?CF=91040430190"
KEYWORDS = ["madrelingua", "inglese", "bando", "liquidazione", "compensi"]

EMAIL_SENDER = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
EMAIL_RECEIVER = os.environ["EMAIL_RECEIVER"]


def parse_and_collect(html):
    matches = []
    soup = BeautifulSoup(html, "html.parser")
    for text in soup.find_all(string=True):
        if any(keyword.lower() in text.lower() for keyword in KEYWORDS):
            cleaned = text.strip()
            if cleaned and cleaned not in matches:
                matches.append(cleaned)
    return matches


async def scrape_pages():
    all_matches = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        # First page
        html = await page.content()
        all_matches.extend(parse_and_collect(html))

        while True:
            try:
                # Try clicking "Successivo" (Next)
                next_button = await page.query_selector('a:has-text("Successivo")')
                if not next_button:
                    break
                is_disabled = await next_button.get_attribute("class")
                if is_disabled and "disabled" in is_disabled:
                    break
                await next_button.click()
                await page.wait_for_timeout(2000)  # wait for page to load

                html = await page.content()
                matches = parse_and_collect(html)
                if not matches:
                    break
                all_matches.extend(matches)
            except Exception as e:
                print(f"Error during pagination: {e}")
                break

        await browser.close()
    return list(set(all_matches))


def send_email(matches):
    if not matches:
        print("No matches found. No email sent.")
        return

    msg = EmailMessage()
    msg["Subject"] = f"[Monitor] Keyword Matches – {datetime.datetime.now():%Y-%m-%d %H:%M}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg.set_content("\n\n".join(matches))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)

    print(f"Email sent to {EMAIL_RECEIVER} with {len(matches)} matches.")


if __name__ == "__main__":
    try:
        found_matches = asyncio.run(scrape_pages())
        send_email(found_matches)
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
