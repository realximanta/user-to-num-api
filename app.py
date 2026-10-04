import os
import json
import re
from flask import Flask, request, jsonify
import cloudscraper
import httpx

app = Flask(__name__)

# ============================================================
# YOUR BRANDING — Edit these any time
# ============================================================
YOUR_OWNER          = "@b4nzw"
YOUR_POWERED_BY     = "编码者 𝗧𝘂𝗸𝘂"
YOUR_POWERED_BY_URL = "https://t.me/tukuexe"

# ============================================================
# ENV
# ============================================================
TARGET_API_BASE = os.environ.get("TARGET_API_URL", "")


# ============================================================
# ROOT — Landing page for visitors
# ============================================================
@app.route('/', methods=['GET'])
def landing():
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>OSINT Proxy API Tuku</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: radial-gradient(circle at 20% 20%, #1a1a2e 0%, #0f0f1a 60%, #000 100%);
    color: #e6e6e6;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }}
  .card {{
    max-width: 520px;
    width: 100%;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 40px 32px;
    backdrop-filter: blur(12px);
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
    text-align: center;
  }}
  .badge {{
    display: inline-block;
    padding: 6px 14px;
    background: rgba(0, 255, 128, 0.1);
    color: #00ff80;
    border: 1px solid rgba(0, 255, 128, 0.3);
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1px;
    margin-bottom: 20px;
  }}
  h1 {{
    font-size: 26px;
    font-weight: 700;
    margin-bottom: 8px;
    background: linear-gradient(90deg, #fff, #9f9fff);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }}
  .sub {{
    color: #888;
    font-size: 14px;
    margin-bottom: 32px;
  }}
  .row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    text-align: left;
    font-size: 14px;
  }}
  .row:last-of-type {{ border-bottom: none; }}
  .label {{ color: #888; }}
  .value {{ color: #fff; font-weight: 500; }}
  .value a {{
    color: #7fa8ff;
    text-decoration: none;
  }}
  .value a:hover {{ text-decoration: underline; }}
  .footer {{
    margin-top: 28px;
    font-size: 12px;
    color: #555;
  }}
</style>
</head>
<body>
  <div class="card">
    <div class="badge">● ONLINE</div>
    <h1>OSINT Proxy API</h1>
    <p class="sub">Secure data-fetching middleware</p>

    <div class="row">
      <span class="label">Owner</span>
      <span class="value">{YOUR_OWNER}</span>
    </div>
    <div class="row">
      <span class="label">Powered by</span>
      <span class="value">{YOUR_POWERED_BY}</span>
    </div>
    <div class="row">
      <span class="label">Store</span>
      <span class="value"><a href="{YOUR_POWERED_BY_URL}" target="_blank">{YOUR_POWERED_BY_URL}</a></span>
    </div>
    <div class="row">
      <span class="label">Version</span>
      <span class="value">69</span>
    </div>

    <p class="footer">© {YOUR_OWNER} — All rights reserved</p>
  </div>
</body>
</html>"""
    return html, 200


# ============================================================
# HEALTH — for UptimeRobot
# ============================================================
@app.route('/health', methods=['GET', 'HEAD'])
def health_check():
    return "", 200


# ============================================================
# API — proxy endpoint
# ============================================================
def _brand_response(data: dict) -> dict:
    """
    Overwrite branding fields and strip sensitive sections
    so the bot (and anyone inspecting traffic) only ever sees
    YOUR identity.
    """
    if not isinstance(data, dict):
        return data

    # --- Force your branding ---
    data["owner"]             = YOUR_OWNER
    data["powered_by"]        = YOUR_POWERED_BY
    data["powered_by_store"]  = YOUR_POWERED_BY_URL

    # --- Remove anything sensitive / not yours ---
    for junk_key in (
        "key_info", "key", "Key", "api_key", "expires",
        "limit", "remaining", "used", "credits",
    ):
        data.pop(junk_key, None)

    # --- Keep these clean defaults if missing ---
    data.setdefault("success", True)
    data.setdefault("version", "69")
    data.setdefault("time", "1.0s")

    return data


@app.route('/api', methods=['GET'])
def proxy_api():
    num = request.args.get('num')

    if not num:
        return jsonify({"error": "Missing 'num' parameter"}), 400

    if not TARGET_API_BASE:
        return jsonify({"error": "Server configuration error."}), 500

    # Build the target URL
    if TARGET_API_BASE.endswith("=") or TARGET_API_BASE.endswith("&"):
        target_url = f"{TARGET_API_BASE}{num}"
    else:
        target_url = f"{TARGET_API_BASE}{num}"

    # ---------- Strategy 1: Cloudscraper ----------
    try:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True,
            }
        )
        response = scraper.get(target_url, timeout=20)

        if response.status_code == 200 and "<html" not in response.text.lower():
            parsed = response.json()
            return jsonify(_brand_response(parsed))
    except Exception:
        pass  # fall through to Jina

    # ---------- Strategy 2: Jina.ai Reader ----------
    try:
        jina_url = f"https://r.jina.ai/{target_url}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = httpx.get(jina_url, headers=headers, timeout=25)

        if response.status_code == 200:
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                return jsonify(_brand_response(parsed))
    except Exception:
        pass

    # ---------- Both failed ----------
    return jsonify({
        "error": "Upstream API temporarily unreachable. Please try again in a moment."
    }), 503


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
