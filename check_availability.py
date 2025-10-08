import requests
from bs4 import BeautifulSoup
import os
import json

ARTIFACT_FILE = "previous_availability.json"

def get_product_availability():
    url = "https://komunacoffee.com/collections/coffee-beans"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    products = {}
    for product_card in soup.select("div.product-card, div.card__content"):
        # Grab product name
        name_tag = product_card.find(["h3", "a"], class_=lambda c: c and "card__heading" in c or c == "product-card__title")
        if not name_tag:
            continue
        name = name_tag.get_text(strip=True)

        # Check if any <span> inside .card__badge.bottom.left contains "Sold out"
        sold_out_badge = product_card.select_one("div.card__badge.bottom.left span")
        if sold_out_badge and "Sold out" in sold_out_badge.get_text(strip=True):
            availability = "Sold out"
        else:
            availability = "Available"

        products[name] = availability
    return products

def load_previous():
    if os.path.exists(ARTIFACT_FILE):
        with open(ARTIFACT_FILE, "r") as f:
            return json.load(f)
    return {}

def save_current(data):
    with open(ARTIFACT_FILE, "w") as f:
        json.dump(data, f, indent=2)

def format_slack_message(current, previous):
    available = [f"☕ *{p}*" for p, status in current.items() if status == "Available"]
    sold_out = [f"❌ *{p}*" for p, status in current.items() if status == "Sold out"]

    # Detect changes
    changes = []
    for p, status in current.items():
        if p in previous and previous[p] != status:
            changes.append(f"{p}: {previous[p]} → {status}")
        elif p not in previous:
            changes.append(f"{p}: added ({status})")

    # Build message
    msg_lines = ["*Komuna Coffee Daily Availability:*"]
    if available:
        msg_lines.append("\n*Available:*")
        msg_lines.extend(available)
    if sold_out:
        msg_lines.append("\n*Sold Out:*")
        msg_lines.extend(sold_out)
    
    if changes:
        # Tag everyone if there are changes
        msg_lines.insert(0, "<!channel> ⚡ *Changes detected!*")
        msg_lines.insert(1, "*Change summary:*")
        for change in changes:
            msg_lines.insert(2, f"• {change}")  # Insert before detailed lists

    return "\n".join(msg_lines)

def send_to_slack(message):
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
        print("No Slack webhook configured.")
        return
    requests.post(webhook, json={"text": message})

if __name__ == "__main__":
    current = get_product_availability()
    previous = load_previous()
    message = format_slack_message(current, previous)
    send_to_slack(message)
    save_current(current)
    print(message)
