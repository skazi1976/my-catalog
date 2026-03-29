#!/usr/bin/env python3
"""
HaCatalog - Send Push Notifications
====================================
Send push notifications to all PWA subscribers.

Usage:
    python send_push.py "כותרת" "תוכן ההודעה" [URL]
    python send_push.py --count                          # Show subscriber count

Examples:
    python send_push.py "מוצרים חדשים!" "50 מוצרים חדשים נוספו לקטלוג" "https://hacatalog.com"
    python send_push.py "מבצע UGG" "מחירים מטורפים על UGG - רק היום!" "https://hacatalog.com/#product=x230447391"
"""

import sys, requests, json

sys.stdout.reconfigure(encoding='utf-8')

API = "https://ali-findme-api.ohadf1976.workers.dev"
SECRET = "hacatalog2026"

def send_notification(title, body, url="https://hacatalog.com"):
    resp = requests.post(f"{API}/push/send", json={
        "title": title,
        "body": body,
        "url": url,
        "site": "hacatalog",
        "secret": SECRET
    }, timeout=30)
    data = resp.json()
    if data.get("success"):
        print(f"✅ נשלח! {data['sent']} הצליחו, {data['failed']} נכשלו (מתוך {data['total']})")
    else:
        print(f"❌ שגיאה: {data.get('error', 'Unknown')}")
    return data

def get_count():
    resp = requests.get(f"{API}/push/subscribers?site=hacatalog", timeout=10)
    data = resp.json()
    print(f"📱 מנויים להתראות: {data.get('count', 0)}")
    return data

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--count":
        get_count()
    else:
        title = sys.argv[1]
        body = sys.argv[2] if len(sys.argv) > 2 else ""
        url = sys.argv[3] if len(sys.argv) > 3 else "https://hacatalog.com"
        send_notification(title, body, url)
