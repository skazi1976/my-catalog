"""
FlyLink Price Updater
Fetches real ILS prices from FlyLink API and updates data.json.
Run anytime to refresh prices: python update_flylink_prices.py
"""
import json
import re
import time
import requests

API_URL = "https://api.flylinking.com/trade/web/goods/buyer/priceByCurrencyQry"
DATA_FILE = "data.json"
DELAY = 0.3  # seconds between API calls


def extract_code(url):
    """Extract product code from FlyLink URL."""
    m = re.search(r'flylinking\.com/g/(\w+)', url)
    return m.group(1) if m else None


def fetch_price(code):
    """Fetch ILS price from FlyLink API. Returns rounded price or None."""
    try:
        r = requests.get(API_URL, params={"goodsNo": code, "currency": "ILS"}, timeout=10)
        data = r.json()
        if data.get("success") and data.get("data"):
            prices = [sku["paymentUnitPrice"] for sku in data["data"] if sku.get("paymentUnitPrice")]
            if prices:
                return round(min(prices))
    except Exception as e:
        print(f"  Error fetching {code}: {e}")
    return None


def main():
    with open(DATA_FILE, encoding="utf-8") as f:
        products = json.load(f)

    # Collect unique FlyLink codes
    code_to_indices = {}
    for i, p in enumerate(products):
        url = p.get("l", "")
        code = extract_code(url)
        if code:
            code_to_indices.setdefault(code, []).append(i)

    total = len(code_to_indices)
    print(f"Found {total} unique FlyLink products to update")

    updated = 0
    errors = 0
    unchanged = 0

    for idx, (code, indices) in enumerate(code_to_indices.items()):
        if idx > 0 and idx % 50 == 0:
            print(f"  Progress: {idx}/{total} ({updated} updated, {errors} errors)")

        price = fetch_price(code)
        time.sleep(DELAY)

        if price is None:
            errors += 1
            continue

        price_str = f"₪{price}"
        for i in indices:
            old = products[i].get("p", "")
            if old != price_str:
                products[i]["p"] = price_str
                updated += 1
            else:
                unchanged += 1

    print(f"\nDone! {updated} updated, {unchanged} unchanged, {errors} errors out of {total} products")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False)
    print("Saved data.json")


if __name__ == "__main__":
    main()
