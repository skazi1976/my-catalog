"""
Migrate remaining Yupoo images to Cloudflare R2.
Downloads from Yupoo, uploads to R2, updates data.json.
Usage: python migrate_yupoo_to_r2.py
"""
import json, os, re, time, hashlib, mimetypes
import requests
import boto3
from botocore.config import Config
from concurrent.futures import ThreadPoolExecutor, as_completed

# R2 Config
ACCOUNT_ID = "84c63f0f65cabb8e5b611913c03a1188"
ACCESS_KEY = "76c38d1b2be9f17ef7dd5749ee3eb579"
SECRET_KEY = "6993eccb46218cf76d20ad6e30885222dc482eade993ffb318fac3efb5c7b05e"
BUCKET = "yupoo-images"
PUBLIC_URL = "https://pub-0ad199860b5a4ce0b3fb483660b8a4ca.r2.dev"
ENDPOINT = f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"

DATA_FILE = "data.json"
WORKERS = 10
BATCH_SAVE = 200  # save progress every N images

s3 = boto3.client('s3',
    endpoint_url=ENDPOINT,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=Config(retries={'max_attempts': 3}, s3={'addressing_style': 'path'}),
    region_name='auto'
)

session = requests.Session()
session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120'


def url_to_r2_key(url):
    """Generate R2 key from Yupoo URL."""
    # Extract hash from URL like https://photo.yupoo.com/xuxuxuxux/fa774b8d/origin.jpg
    m = re.search(r'yupoo\.com/(\w+)/(\w+)/(\w+)\.(jpg|jpeg|png|webp|gif)', url)
    if m:
        store, img_hash, size, ext = m.groups()
        return f"images/{store}/{img_hash}_{size}.{ext}"
    # Fallback: hash the URL
    h = hashlib.md5(url.encode()).hexdigest()
    return f"images/yupoo/{h}.jpg"


def migrate_image(url):
    """Download from Yupoo, upload to R2. Returns (old_url, new_url) or (old_url, None)."""
    try:
        r = session.get(url, timeout=15)
        if r.status_code != 200 or len(r.content) < 100:
            return (url, None)

        r2_key = url_to_r2_key(url)
        ct = r.headers.get('Content-Type', 'image/jpeg')

        s3.put_object(
            Bucket=BUCKET,
            Key=r2_key,
            Body=r.content,
            ContentType=ct
        )

        new_url = f"{PUBLIC_URL}/{r2_key}"
        return (url, new_url)
    except Exception as e:
        return (url, None)


def main():
    with open(DATA_FILE, encoding='utf-8') as f:
        products = json.load(f)

    # Collect unique Yupoo URLs
    yupoo_urls = set()
    for p in products:
        for img in p.get('i', []):
            if 'yupoo.com' in img:
                yupoo_urls.add(img)

    total = len(yupoo_urls)
    print(f"Found {total} unique Yupoo images to migrate")

    # Migrate in parallel
    url_map = {}  # old -> new
    done = 0
    errors = 0

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(migrate_image, url): url for url in yupoo_urls}

        for future in as_completed(futures):
            old_url, new_url = future.result()
            done += 1

            if new_url:
                url_map[old_url] = new_url
            else:
                errors += 1

            if done % 100 == 0:
                print(f"  Progress: {done}/{total} ({len(url_map)} ok, {errors} errors)")

    print(f"\nMigration done: {len(url_map)} uploaded, {errors} errors")

    # Update data.json
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

    print(f"Updated {updated} products in data.json")

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False)
    print("Saved!")


if __name__ == "__main__":
    main()
