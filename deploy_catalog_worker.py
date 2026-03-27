"""
Deploy Catalog Analytics Worker to Cloudflare
Usage:
    python deploy_catalog_worker.py all      # Create KV + seed + deploy
    python deploy_catalog_worker.py deploy   # Deploy worker only
    python deploy_catalog_worker.py kv       # Create KV namespace only
    python deploy_catalog_worker.py seed     # Seed initial data
"""

import requests
import json
import hashlib
import sys

# Cloudflare config (same account as Ali Find Me)
CF_API_TOKEN = "gk7OelebzzelJyAILtM6bgQ4qxajObcnYQOBYwJD"
CF_ACCOUNT_ID = "84c63f0f65cabb8e5b611913c03a1188"
SCRIPT_NAME = "catalog-analytics"
KV_TITLE = "CATALOG_ANALYTICS_KV"

HEADERS = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json"
}

BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}"


def create_kv():
    """Create KV namespace"""
    print("📦 Creating KV namespace...")

    # Check if exists
    r = requests.get(f"{BASE_URL}/storage/kv/namespaces", headers=HEADERS)
    namespaces = r.json().get("result", [])

    for ns in namespaces:
        if ns["title"] == KV_TITLE:
            print(f"  ✅ KV already exists: {ns['id']}")
            return ns["id"]

    # Create new
    r = requests.post(f"{BASE_URL}/storage/kv/namespaces",
                      headers=HEADERS,
                      json={"title": KV_TITLE})

    if r.json().get("success"):
        kv_id = r.json()["result"]["id"]
        print(f"  ✅ Created KV: {kv_id}")
        return kv_id
    else:
        print(f"  ❌ Error: {r.json()}")
        return None


def get_kv_id():
    """Get existing KV namespace ID"""
    r = requests.get(f"{BASE_URL}/storage/kv/namespaces", headers=HEADERS)
    for ns in r.json().get("result", []):
        if ns["title"] == KV_TITLE:
            return ns["id"]
    return None


def seed_data():
    """Seed initial settings"""
    kv_id = get_kv_id()
    if not kv_id:
        print("❌ KV namespace not found. Run 'kv' first.")
        return

    print("🌱 Seeding initial data...")

    # Default password: admin123
    pw_hash = hashlib.sha256("admin123".encode()).hexdigest()
    settings = {
        "siteName": "קטלוג מותגים",
        "passwordHash": pw_hash
    }

    # Write settings
    url = f"{BASE_URL}/storage/kv/namespaces/{kv_id}/values/settings"
    r = requests.put(url,
                     headers={"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"},
                     data=json.dumps(settings))
    print(f"  Settings: {'✅' if r.json().get('success') else '❌'}")

    # Empty search logs
    url = f"{BASE_URL}/storage/kv/namespaces/{kv_id}/values/search_logs"
    r = requests.put(url,
                     headers={"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"},
                     data="[]")
    print(f"  Search logs: {'✅' if r.json().get('success') else '❌'}")

    # Empty daily stats
    url = f"{BASE_URL}/storage/kv/namespaces/{kv_id}/values/daily_stats"
    r = requests.put(url,
                     headers={"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"},
                     data="{}")
    print(f"  Daily stats: {'✅' if r.json().get('success') else '❌'}")

    print("  ✅ Seeding complete!")


def deploy():
    """Deploy worker"""
    kv_id = get_kv_id()
    if not kv_id:
        print("❌ KV namespace not found. Run 'kv' first.")
        return

    print(f"🚀 Deploying {SCRIPT_NAME}...")

    # Read worker code
    with open("catalog-worker.js", "r", encoding="utf-8") as f:
        worker_code = f.read()

    # Metadata with KV binding
    metadata = {
        "main_module": "worker.js",
        "bindings": [
            {
                "type": "kv_namespace",
                "name": "CATALOG_KV",
                "namespace_id": kv_id
            }
        ]
    }

    # Multipart upload
    url = f"{BASE_URL}/workers/scripts/{SCRIPT_NAME}"

    files = {
        'metadata': ('metadata.json', json.dumps(metadata), 'application/json'),
        'worker.js': ('worker.js', worker_code, 'application/javascript+module'),
    }

    r = requests.put(url,
                     headers={"Authorization": f"Bearer {CF_API_TOKEN}"},
                     files=files)

    result = r.json()
    if result.get("success"):
        print(f"  ✅ Worker deployed!")

        # Enable workers.dev subdomain
        r2 = requests.post(f"{BASE_URL}/workers/scripts/{SCRIPT_NAME}/subdomain",
                          headers=HEADERS,
                          json={"enabled": True})
        if r2.json().get("success"):
            print(f"  ✅ Subdomain enabled")

        print(f"  🌐 URL: https://{SCRIPT_NAME}.ohadf1976.workers.dev")
    else:
        print(f"  ❌ Error: {json.dumps(result, indent=2)}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "all":
        create_kv()
        seed_data()
        deploy()
    elif cmd == "kv":
        create_kv()
    elif cmd == "seed":
        seed_data()
    elif cmd == "deploy":
        deploy()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
