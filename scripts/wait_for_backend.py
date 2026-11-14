#!/usr/bin/env python3
"""
ClairFinance Backend Health Waiter
Pings the backend health endpoint until it responds 200 OK or times out.
"""
import sys
import time
import urllib.request

def wait_for_backend(url="http://127.0.0.1:8000/api/health", max_seconds=30):
    print(f"⏳ Waiting for backend to become healthy at {url} ", end="", flush=True)
    start_time = time.time()
    while time.time() - start_time < max_seconds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ClairFinance-HealthCheck"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    print(" ✅ Ready!")
                    return 0
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(0.5)

    print("\n⚠️ Warning: Backend health check timed out after 30 seconds.")
    print("Please check the 'ClairFinance Backend' console window for logs.")
    return 1

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/api/health"
    sys.exit(wait_for_backend(url))
