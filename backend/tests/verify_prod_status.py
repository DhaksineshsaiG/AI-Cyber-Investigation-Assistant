import urllib.request
import json
import re
import sys

def verify():
    vercel_urls = [
        "https://ai-cyber-investigation-assistant.vercel.app"
    ]
    backend_health_url = "https://ai-cyber-investigation-assistant.onrender.com/api/health"

    print("=" * 60)
    print("VERCEL PRODUCTION DEPLOYMENT & CONNECTIVITY VERIFICATION")
    print("=" * 60)

    for u in vercel_urls:
        print(f"\n[Check] URL: {u}")
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            code = resp.getcode()
            html = resp.read().decode("utf-8")
            print(f"  [OK] HTTP Status: {code}")
            print(f"  [OK] HTML Size: {len(html)} bytes")
            print(f"  [OK] HTML has <title>: {'<title>' in html}")

            scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
            print(f"  [OK] Script Tags: {scripts}")
            for s in scripts:
                asset_url = u + s if s.startswith("/") else u + "/" + s
                req_js = urllib.request.Request(asset_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req_js, timeout=25) as resp_js:
                    js_code = resp_js.getcode()
                    js_content = resp_js.read().decode("utf-8")
                    print(f"  [OK] Asset: {s} -> HTTP {js_code}, Size {len(js_content)} bytes")
                    has_backend = "https://ai-cyber-investigation-assistant.onrender.com" in js_content
                    print(f"  [OK] Contains Render Backend URL: {has_backend}")
                    assert has_backend, "Render backend URL missing from deployed JS bundle!"

    print("\n[Check] Calling Live Render Backend Health Endpoint...")
    req_health = urllib.request.Request(
        backend_health_url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Origin": "https://ai-cyber-investigation-assistant.vercel.app"
        }
    )
    with urllib.request.urlopen(req_health, timeout=25) as resp_health:
        health_code = resp_health.getcode()
        health_body = json.loads(resp_health.read().decode("utf-8"))
        cors_header = resp_health.headers.get("Access-Control-Allow-Origin")
        print(f"  [OK] Backend HTTP Status: {health_code}")
        print(f"  [OK] Backend Health Response: {health_body}")
        print(f"  [OK] CORS Access-Control-Allow-Origin: {cors_header}")
        assert health_code == 200, f"Expected 200, got {health_code}"
        assert health_body.get("status") == "healthy", "Backend not healthy"
        assert "Atlas" in health_body.get("database", ""), "Backend not connected to Atlas"
        assert health_body.get("groq_configured") is True, "Groq not configured"

    print("\n" + "=" * 60)
    print("ALL 6 VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        ok = verify()
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"\n[FAILED] Verification error: {e}")
        sys.exit(1)
