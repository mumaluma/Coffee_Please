import requests
from bs4 import BeautifulSoup
import json
import os
import subprocess

def get_current_availability():
    url = "https://komunacoffee.com/collections/coffee-beans"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    products = []
    for product_card in soup.select("div.product-card, div.card__information"):
        name_tag = product_card.find(["h3", "a"], class_=lambda c: c and "card__heading" in c or c == "product-card__title")
        if not name_tag:
            continue
        name = name_tag.get_text(strip=True)

        badge = product_card.select_one("div.card__badge.bottom.left span.badge.badge--bottom-left.color-scheme-3")
        if badge and "Sold out" in badge.get_text():
            products.append({"product_name": name, "availability": "Sold out"})
        else:
            products.append({"product_name": name, "availability": "Available"})
    return products


def load_previous():
    if not os.path.exists("availability.json"):
        return []
    with open("availability.json", "r") as f:
        return json.load(f)


def save_current(data):
    with open("availability.json", "w") as f:
        json.dump(data, f, indent=2)


def summarize_changes(old, new):
    changes = []
    old_map = {p["product_name"]: p["availability"] for p in old}
    for item in new:
        old_status = old_map.get(item["product_name"])
        if old_status and old_status != item["availability"]:
            changes.append(f"{item['product_name']}: {old_status} → {item['availability']}")
        elif old_status is None:
            changes.append(f"{item['product_name']}: added ({item['availability']})")
    return changes


def send_slack_message(message):
    import requests
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
        print("No Slack webhook configured.")
        return
    payload = {"text": message}
    requests.post(webhook, json=payload)


if __name__ == "__main__":
    print("Fetching current product data...")
    current = get_current_availability()
    previous = load_previous()
    changes = summarize_changes(previous, current)

    if not changes:
        print("No changes detected.")
        exit(0)

    print("Changes detected:\n" + "\n".join(changes))
    save_current(current)

    message = "*Komuna Coffee Stock Update:*\n" + "\n".join(changes)
    send_slack_message(message)

