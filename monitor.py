import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.message import EmailMessage
import datetime

URL = "https://www.trasparenzascuole.it/Public/APDPublic_ExtV2.aspx?CF=91040430190"
KEYWORDS = ["madrelingua", "inglese", "bando", "liquidazione", "compensi"]

EMAIL_SENDER = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
EMAIL_RECEIVER = os.environ["EMAIL_RECEIVER"]

def fetch_and_check():
    response = requests.get(URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    matches = []
    for item in soup.find_all(text=True):
        if any(keyword.lower() in item.lower() for keyword in KEYWORDS):
            parent = item.strip()
            if parent and parent not in matches:
                matches.append(parent)
    return matches

def send_email(matches):
    if not matches:
        return
    msg = EmailMessage()
    msg["Subject"] = f"Keyword Matches – {datetime.datetime.now():%Y-%m-%d %H:%M}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg.set_content("\n\n".join(matches))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    results = fetch_and_check()
    send_email(results)
