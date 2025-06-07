import requests
from bs4 import BeautifulSoup
import smtplib
from email.message import EmailMessage
import datetime

# SETTINGS
URL = "https://www.trasparenzascuole.it/Public/APDPublic_ExtV2.aspx?CF=91040430190"
KEYWORDS = ["PNRR", "STEM", "bando", "liquidazione", "compensi"]
EMAIL_SENDER = "your.email@example.com"
EMAIL_PASSWORD = "your_app_password"
EMAIL_RECEIVER = "recipient@example.com"

def fetch_and_check():
    response = requests.get(URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    matches = []

    # Loop through visible text and find matches
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
    msg["Subject"] = f"Keyword Matches on Trasparenza Scuole – {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg.set_content("\n\n".join(matches))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    results = fetch_and_check()
    send_email(results)
