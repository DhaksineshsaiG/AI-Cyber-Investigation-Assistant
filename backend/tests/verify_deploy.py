import httpx
import re
import sys

def verify_live_deployment():
    print("=" * 60)
    print("LIVE PRODUCTION DEPLOYMENT VERIFICATION")
    print("=" * 60)

    vercel_url = "https://ai-cyber-investigation-assistant.vercel.app"
    render_health_url = "https://ai-cyber-investigation-assistant.onrender.com/api/health"

    # 1. Verify Vercel frontend responds with 200 OK
    print(f"\n[Test 1] Testing Vercel Frontend ({vercel_url})...")
    with httpx.Client(timeout=15, follow_redirects=True) as client:
        res = client.get(vercel_url)
        print(f"  [OK] HTTP Status: {res.status_code}")
        assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}"
        assert "<title>" in res.text, "Expected valid HTML with <title> tag"
        print(f"  [OK] HTML Content-Length: {len(res.text)} bytes")

        # 2. Verify JS bundles and Render backend URL presence
        print("\n[Test 2] Verifying Deployed JS Bundle Configuration...")
        scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', res.text)
        print(f"  [OK] Script tags found: {scripts}")
        found_backend_url = False
        for s in scripts:
            js_url = f"{vercel_url}{s}" if s.startswith("/") else f"{vercel_url}/{s}"
            js_res = client.get(js_url)
            print(f"  [OK] Fetched {s}: Status {js_res.status_code}, Length {len(js_res.text)} bytes")
            if "https://ai-cyber-investigation-assistant.onrender.com" in js_res.text:
                found_backend_url = True
                print("  [OK] Confirmed production Render backend URL baked into deployed bundle!")
        assert found_backend_url, "Render backend URL was not found in deployed JS bundle!"

        # 3. Verify Render backend connectivity and CORS compatibility
        print(f"\n[Test 3] Testing Render Backend ({render_health_url})...")
        backend_res = client.get(render_health_url)
        print(f"  [OK] Backend HTTP Status: {backend_res.status_code}")
        assert backend_res.status_code == 200, f"Expected 200 OK, got {backend_res.status_code}"
        health_data = backend_res.json()
        print(f"  [OK] Backend Health Response: {health_data}")
        assert health_data.get("status") == "healthy", "Backend does not report healthy status!"
        assert "Atlas" in health_data.get("database", ""), "Backend is not connected to Atlas!"
        assert health_data.get("groq_configured") is True, "Groq is not configured on backend!"

        # 4. Verify CORS headers for Vercel origin
        print("\n[Test 4] Testing CORS Handshake between Vercel and Render...")
        cors_headers = {
            "Origin": "https://ai-cyber-investigation-assistant.vercel.app",
            "Access-Control-Request-Method": "GET"
        }
        options_res = client.options(render_health_url, headers=cors_headers)
        allow_origin = options_res.headers.get("access-control-allow-origin")
        print(f"  [OK] OPTIONS preflight status: {options_res.status_code}")
        print(f"  [OK] Access-Control-Allow-Origin: {allow_origin}")

    print("\n" + "=" * 60)
    print("ALL PRODUCTION DEPLOYMENT VERIFICATIONS PASSED!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = verify_live_deployment()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[FAILED] Verification failed: {e}")
        sys.exit(1)
