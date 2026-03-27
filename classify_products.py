"""
Classify catalog products into categories using Claude Vision (Haiku).
Analyzes the first image of each product and assigns a category.
Categories: shoes, bags, watches, clothing, accessories, other
Saves results to data.json with new 'c' (category) field.
"""
import json
import time
import base64
import urllib.request
import ssl
import sys
import os

# Fix Windows encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-haiku-4-5-20251001"
CATEGORIES = ["shoes", "bags", "watches", "clothing", "accessories", "other"]
BATCH_SIZE = 10  # images per batch request
SAVE_EVERY = 50  # save progress every N products

# SSL context for HTTPS
ctx = ssl.create_default_context()

def classify_image_url(image_url):
    """Send image URL to Claude Vision and get category."""
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 20,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "url", "url": image_url}
                },
                {
                    "type": "text",
                    "text": "What product is in this image? Reply with ONLY one word: shoes, bags, watches, clothing, accessories, or other. Nothing else."
                }
            ]
        }]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            result = json.loads(resp.read())
            text = result["content"][0]["text"].strip().lower()
            # Extract category from response
            for cat in CATEGORIES:
                if cat in text:
                    return cat
            return "other"
    except Exception as e:
        print(f"  Error: {e}")
        return None


def main():
    data_file = os.path.join(os.path.dirname(__file__), "data.json")

    with open(data_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    total = len(products)
    # Count already classified
    already = sum(1 for p in products if p.get("c"))
    print(f"Total products: {total}, Already classified: {already}")

    classified = 0
    errors = 0
    start_time = time.time()

    for i, product in enumerate(products):
        # Skip if already classified
        if product.get("c"):
            continue

        # Skip if no images
        if not product.get("i") or not product["i"]:
            product["c"] = "other"
            classified += 1
            continue

        img_url = product["i"][0]

        # Quick classify by title for known brands/categories
        title = (product.get("t") or "").lower()
        fname = (product.get("f") or "").lower()
        combined = title + " " + fname

        # Watches
        if any(w in combined for w in ["rolex", "patek", "philippe", "rado", "hublot", "role",
                "omega", "cartier", "iwc", "tudor", "breitling", "longines", "tissot",
                "watches", "watch"]):
            product["c"] = "watches"
            classified += 1
            continue

        # UGG = always shoes/boots
        if title.strip() == "ugg" or "ugg" in combined:
            product["c"] = "shoes"
            classified += 1
            continue

        # Use Claude Vision
        cat = classify_image_url(img_url)
        if cat:
            product["c"] = cat
            classified += 1
        else:
            errors += 1
            # Retry once after delay
            time.sleep(2)
            cat = classify_image_url(img_url)
            if cat:
                product["c"] = cat
                classified += 1
                errors -= 1

        # Progress
        done = already + classified
        elapsed = time.time() - start_time
        rate = classified / elapsed if elapsed > 0 else 0
        remaining = (total - done) / rate if rate > 0 else 0
        print(f"  [{done}/{total}] {product.get('t','?')[:25]:25s} → {product.get('c','?'):12s} ({rate:.1f}/s, ~{remaining/60:.0f}m left)")

        # Save progress periodically
        if classified % SAVE_EVERY == 0:
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(products, f, ensure_ascii=False)
            print(f"  --- Saved progress ({done}/{total}) ---")

        # Rate limit: ~50 requests/min for Haiku
        time.sleep(0.3)

    # Final save
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False)

    # Summary
    from collections import Counter
    cats = Counter(p.get("c", "unknown") for p in products)
    print(f"\n=== Done! Classified {classified} products, {errors} errors ===")
    for cat, count in cats.most_common():
        print(f"  {cat:15s}: {count}")


if __name__ == "__main__":
    main()
