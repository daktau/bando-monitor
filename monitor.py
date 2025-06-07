import os
import requests
from bs4 import BeautifulSoup
from email.message import EmailMessage
import smtplib
import datetime
import re

# --- SETTINGS ---
URL = "https://www.trasparenzascuole.it/Public/APDPublic_ExtV2.aspx?CF=91040430190"
KEYWORDS = ["madrelingua", "inglese", "bando", "liquidazione", "compensi"]

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
    matches = []
    for text in soup.find_all(string=True):
        if any(keyword.lower() in text.lower() for keyword in KEYWORDS):
            cleaned = text.strip()
            if cleaned and cleaned not in matches:
                matches.append(cleaned)
    return matches

def paginate_and_scrape():
    session = requests.Session()
    results = []

    # First page request
    resp = session.get(URL)

    # Print first part of the HTML for debugging in Actions log
    print("\n--- DEBUG HTML RESPONSE START ---\n")
    print(resp.text[:1500])
    print("\n--- DEBUG HTML RESPONSE END ---\n")

    soup = BeautifulSoup(resp.text, "html.parser")
    results.extend(parse_and_collect(soup))

    # Try navigating pages via POST
    while True:
        try:
            form_data = get_form_fields(soup)
        except RuntimeError as e:
            print(f"Form field extraction error: {e}")
            break

        # ASP.NET postback event for "Successivo"
        form_data["__EVENTTARGET"] = "ctl00$ContentPlaceHolder1$gvDocumenti$ctl23$ctl01"
        form_data["__EVENTARGUMENT"] = ""

        resp = session.post(URL, data=form_data)
        soup = BeautifulSoup(resp.text, "html.parser")
        page_results = parse_and_collect(soup)

        if not page_results:
            break
        results.extend(page_results)

        next_button = soup.find("a", string=re.compile("Successivo", re.IGNORECASE))
        if not next_button or "disabled" in next_button.get("class", []):
            break

    return list(set(results))  # Remove duplicates

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

# --- MAIN ---
if __name__ == "__main__":
    try:
        found_matches = paginate_and_scrape()
        send_email(found_matches)
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
