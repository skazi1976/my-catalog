"""
Migrate Yupoo images to R2 using Selenium (bypasses anti-bot).
Downloads images via Chrome, uploads to Cloudflare R2, updates data.json.

Usage: python migrate_yupoo_selenium.py
"""
import json, os, re, time, hashlib, base64
import boto3
from botocore.config import Config
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# R2 Config
ACCOUNT_ID = "84c63f0f65cabb8e5b611913c03a1188"
ACCESS_KEY = "76c38d1b2be9f17ef7dd5749ee3eb579"
SECRET_KEY = "6993eccb46218cf76d20ad6e30885222dc482eade993ffb318fac3efb5c7b05e"
BUCKET = "yupoo-images"
PUBLIC_URL = "https://pub-0ad199860b5a4ce0b3fb483660b8a4ca.r2.dev"
ENDPOINT = f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"

DATA_FILE = "data.json"
BATCH_SAVE = 500  # save data.json every N images
BATCH_SIZE = 20   # images per browser batch (fetch via JS)

s3 = boto3.client('s3',
    endpoint_url=ENDPOINT,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=Config(retries={'max_attempts': 3}, s3={'addressing_style': 'path'}),
    region_name='auto'
)


def url_to_r2_key(url):
    """Generate R2 key from Yupoo URL."""
    m = re.search(r'yupoo\.com/(\w+)/(\w+)/(\w+)\.(jpg|jpeg|png|webp|gif)', url)
    if m:
        store, img_hash, size, ext = m.groups()
        return f"images/{store}/{img_hash}_{size}.{ext}"
    h = hashlib.md5(url.encode()).hexdigest()
    return f"images/yupoo/{h}.jpg"


def create_driver():
    """Create Chrome driver for image fetching."""
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=800,600')
    opts.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    driver = webdriver.Chrome(options=opts)
    return driver


def fetch_images_via_browser(driver, urls):
    """Fetch multiple images via browser fetch API. Returns dict {url: base64_data}."""
    # Build JS that fetches all URLs and returns base64 data
    js_code = """
    const urls = arguments[0];
    const results = {};
    const promises = urls.map(async (url) => {
        try {
            const resp = await fetch(url, {credentials: 'include'});
            if (!resp.ok) { results[url] = null; return; }
            const blob = await resp.blob();
            const reader = new FileReader();
            const base64 = await new Promise((resolve) => {
                reader.onloadend = () => resolve(reader.result);
                reader.readAsDataURL(blob);
            });
            results[url] = base64;
        } catch(e) {
            results[url] = null;
        }
    });
    await Promise.all(promises);
    return results;
    """
    try:
        result = driver.execute_async_script(f"""
            const callback = arguments[arguments.length - 1];
            const urls = {json.dumps(urls)};
            const results = {{}};
            const promises = urls.map(async (url) => {{
                try {{
                    const resp = await fetch(url, {{credentials: 'include'}});
                    if (!resp.ok) {{ results[url] = null; return; }}
                    const blob = await resp.blob();
                    const reader = new FileReader();
                    const base64 = await new Promise((resolve) => {{
                        reader.onloadend = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                    }});
                    results[url] = base64;
                }} catch(e) {{
                    results[url] = null;
                }}
            }});
            Promise.all(promises).then(() => callback(results));
        """)
        return result or {}
    except Exception as e:
        print(f"  JS fetch error: {e}")
        return {}


def main():
    with open(DATA_FILE, encoding='utf-8') as f:
        products = json.load(f)

    # Collect unique Yupoo URLs
    yupoo_urls = []
    seen = set()
    for p in products:
        for img in p.get('i', []):
            if 'yupoo.com' in img and img not in seen:
                yupoo_urls.append(img)
                seen.add(img)

    total = len(yupoo_urls)
    print(f"Found {total} unique Yupoo images to migrate")

    # Setup browser
    print("Starting Chrome...")
    driver = create_driver()
    driver.set_script_timeout(120)

    # First navigate to yupoo to get cookies
    print("Loading Yupoo homepage for cookies...")
    driver.get("https://photo.yupoo.com")
    time.sleep(3)

    url_map = {}  # old_url -> new_r2_url
    uploaded = 0
    errors = 0

    # Process in batches
    for batch_start in range(0, total, BATCH_SIZE):
        batch_urls = yupoo_urls[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1

        results = fetch_images_via_browser(driver, batch_urls)

        for url in batch_urls:
            b64_data = results.get(url)
            if not b64_data or ',' not in b64_data:
                errors += 1
                continue

            try:
                # Extract binary from data:image/jpeg;base64,xxxxx
                header, encoded = b64_data.split(',', 1)
                img_bytes = base64.b64decode(encoded)

                if len(img_bytes) < 500:  # too small = error page
                    errors += 1
                    continue

                # Determine content type
                ct = 'image/jpeg'
                if 'png' in header:
                    ct = 'image/png'
                elif 'webp' in header:
                    ct = 'image/webp'

                r2_key = url_to_r2_key(url)
                s3.put_object(Bucket=BUCKET, Key=r2_key, Body=img_bytes, ContentType=ct)

                new_url = f"{PUBLIC_URL}/{r2_key}"
                url_map[url] = new_url
                uploaded += 1
            except Exception as e:
                errors += 1

        done = batch_start + len(batch_urls)
        if done % 100 <= BATCH_SIZE:
            print(f"  Progress: {done}/{total} ({uploaded} uploaded, {errors} errors)")

        # Save progress periodically
        if uploaded > 0 and uploaded % BATCH_SAVE < BATCH_SIZE:
            save_progress(products, url_map)
            print(f"  Saved progress ({uploaded} images so far)")

    driver.quit()
    print(f"\nDone! {uploaded} uploaded, {errors} errors out of {total}")

    # Final save
    if url_map:
        save_progress(products, url_map)
        print(f"Updated data.json with {uploaded} new R2 URLs")


def save_progress(products, url_map):
    """Update product image URLs and save."""
    updated = 0
    for p in products:
        imgs = p.get('i', [])
        new_imgs = []
        changed = False
        for img in imgs:
            if img in url_map:
                new_imgs.append(url_map[img])
                changed = True
            else:
                new_imgs.append(img)
        if changed:
            p['i'] = new_imgs
            updated += 1

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False)


if __name__ == "__main__":
    main()
