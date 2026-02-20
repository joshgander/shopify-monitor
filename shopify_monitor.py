import requests, os
from bs4 import BeautifulSoup
from datetime import datetime, timezone

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
STATUS_PAGE_URL   = "https://shopstatus.shopifyapps.com/"
BAD_STATUSES      = ["major outage", "partial outage", "degraded performance", "maintenance"]
STATE_FILE        = "state.txt"

def is_shopify_down():
    headers = {"User-Agent": "ShopifyMonitor/1.0"}
    resp = requests.get(STATUS_PAGE_URL, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    page_text = soup.get_text(separator=" ", strip=True).lower()
    for bad in BAD_STATUSES:
        if bad in page_text:
            return True, bad
    return False, None

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return f.read().strip()
    return "operational"

def save_state(value):
    with open(STATE_FILE, "w") as f:
        f.write(value)

def send_slack(text):
    payload = {"text": text}
    requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
    print(f"Slack sent: {text}")

def main():
    down, status = is_shopify_down()
    last_state   = load_state()
    time_now     = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if down and last_state == "operational":
        # 🔴 First detection — send down alert
        send_slack(
            f"🔴 *Shopify is DOWN!*\n"
            f"*Status:* {status.title()}\n"
            f"*Time:* {time_now}\n"
            f"*Check:* {STATUS_PAGE_URL}"
        )
        save_state("down")

    elif down and last_state == "down":
        # Already notified — skip
        print("Shopify still down. Already notified. Skipping.")

    elif not down and last_state == "down":
        # ✅ Recovered — send recovery alert
        send_slack(
            f"✅ *Shopify has RECOVERED!*\n"
            f"*Status:* Operational\n"
            f"*Time:* {time_now}\n"
            f"*Check:* {STATUS_PAGE_URL}"
        )
        save_state("operational")

    else:
        # All clear — do nothing
        print("Shopify is operational. No alert sent.")

if __name__ == "__main__":
    main()
