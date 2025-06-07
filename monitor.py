import os
import requests
from bs4 import BeautifulSoup
from email.message import EmailMessage
import smtplib
import datetime
import re

# --- SETTINGS ---
URL = "https://www.trasparenzascuole.it/Public/APDPublic_ExtV2.aspx?CF=91040430190"
KEYWORDS = ["madrelingua", "inglese", "bando"]

EMAIL_SENDER = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
EMAIL_RECEIVER = os.environ["EMAIL_RECEIVER"]

# --- FUNCTIONS ---
def get_form_fields(soup):
    viewstate = soup.select_one("input[name='__VIEWSTATE']")
    if not viewstate:
        raise RuntimeError("Could not find __VIEWSTATE. Page structure may have changed or response is invalid.")
    
    return {
        "__VIEWSTATE": viewstate["value"],
        "__VIEWSTATEGENERATOR": soup.select_one("input[name='__VIEWSTATEGENERATOR']")["value"],
        "__EVENTVALIDATION": soup.select_one("input[name='__EVENTVALIDATION']")["value"],
    }

def parse_and_collect(soup):
    """Collect keyword matches from page text."""
    matches = []
    for text in soup.find_all(text=True):
        if any(keyword.lower() in text.lower() for keyword in KEYWORDS):
            cleaned = text.strip()
            if cleaned and cleaned not in matches:
                matches.append(cleaned)
    return matches

def paginate_and_scrape():
    """Iterate over all pages and collect results."""
    session = requests.Session()
    results = []

    resp = session.get(URL)

    """This saves the page content to a file during the first request. This can be viewed via GitHub Actions' logs or use it locally to inspect what the page actually returned."""
    with open("debug.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    
    with open("debug.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    soup = BeautifulSoup(resp.text, "html.parser")
    results.extend(parse_and_collect(soup))

    while True:
        # Extract form data for POST
        form_data = get_form_fields(soup)
        # Target "Successivo" button's ID — this may need to be adjusted if structure changes
        form_data["__EVENTTARGET"] = "ctl00$ContentPlaceHolder1$gvDocumenti$ctl23$ctl01"
        form_data["__EVENTARGUMENT"] = ""

        # POST request to go to next page
        resp = session.post(URL, data=form_data)
        soup = BeautifulSoup(resp.text, "html.parser")

        page_results = parse_and_collect(soup)
        if not page_results:
            break
        results.extend(page_results)

        # Stop if "Successivo" button no longer exists (last page)
        next_button = soup.find("a", string=re.compile("Successivo", re.IGNORECASE))
        if not next_button or "disabled" in next_button.get("class", []):
            break

    return list(set(results))  # Remove duplicates

def send_email(matches):
    """Send matches via email."""
    if not matches:
        return

    msg = EmailMessage()
    msg["Subject"] = f"[Monitor] Keyword Matches – {datetime.datetime.now():%Y-%m-%d %H:%M}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg.set_content("\n\n".join(matches))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)

# --- MAIN ---
if __name__ == "__main__":
    found_matches = paginate_and_scrape()
    send_email(found_matches)
