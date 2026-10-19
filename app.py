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
# Strictly relying on environment variables now. No hardcoded APIs.
TARGET_NUM2INFO = os.environ.get("TARGET_NUM2INFO")
TARGET_TG2NUM   = os.environ.get("TARGET_TG2NUM")

# Global Cloudscraper session (solves challenge once, reuses cookies)
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

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
    max-width: 620px;
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
  h1 {{ font-size: 26px; font-weight: 700; margin-bottom: 8px; color: #fff; }}
  .sub {{ color: #888; font-size: 14px; margin-bottom: 24px; }}
  .endpoint {{
    background: rgba(0, 0, 0, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 16px;
    border-radius: 10px;
    margin-bottom: 16px;
    text-align: left;
  }}
  .endpoint h3 {{ color: #7fa8ff; font-size: 16px; margin-bottom: 8px; }}
  .endpoint code {{ color: #00ff80; word-break: break-all; font-size: 13px; }}
  .endpoint .desc {{ color: #aaa; font-size: 12px; margin-top: 6px; }}
  .row {{ display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 14px; }}
  .row:last-of-type {{ border-bottom: none; }}
  .label {{ color: #888; }}
  .value {{ color: #fff; font-weight: 500; }}
  .value a {{ color: #7fa8ff; text-decoration: none; }}
  .footer {{ margin-top: 28px; font-size: 12px; color: #555; }}
</style>
</head>
<body>
  <div class="card">
    <div class="badge">● ONLINE</div>
    <h1>OSINT Proxy API</h1>
    <p class="sub">Secure data-fetching middleware</p>

    <div class="endpoint">
      <h3>📱 Num2Info API</h3>
      <code>GET /api/num2info?num=123456789</code>
      <div class="desc">Fetches mobile number details.</div>
    </div>

    <div class="endpoint">
      <h3>💬 TG2Num API</h3>
      <code>GET /api/tg2num?query=1234567890</code>
      <div class="desc">Fetches Telegram ID from a 10-digit number.</div>
    </div>

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
# Helpers
# ============================================================
def _brand_response(data: dict) -> dict:
    """Strips sensitive target API info and forces our branding."""
    if not isinstance(data, dict):
        return data

    data["owner"]             = YOUR_OWNER
    data["powered_by"]        = YOUR_POWERED_BY
    data["powered_by_store"]  = YOUR_POWERED_BY_URL

    # Remove sensitive target keys
    for junk_key in ("key_info", "key", "Key", "api_key", "expires", "limit", "remaining", "used", "credits"):
        data.pop(junk_key, None)

    data.setdefault("success", True)
    data.setdefault("version", "69")
    return data


def _fetch_with_fallback(target_url: str):
    """
    Attempts to fetch the target URL using cloudscraper, 
    then Jina.ai. Returns parsed JSON or raises Exception.
    """
    # Strategy 1: Cloudscraper (persistent session)
    try:
        response = scraper.get(target_url, timeout=20)
        # Check if we got HTML (blocked) or JSON
        if response.status_code == 200 and "<html" not in response.text.lower():
            return response.json()
    except Exception:
        pass  # Fall through to Jina

    # Strategy 2: Jina.ai Reader (bypasses WAF)
    try:
        jina_url = f"https://r.jina.ai/{target_url}"
        response = httpx.get(jina_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
        if response.status_code == 200:
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
    except Exception:
        pass

    raise Exception("Both cloudscraper and Jina failed to retrieve valid JSON")


# ============================================================
# ENDPOINT 1: Num2Info
# ============================================================
@app.route('/api/num2info', methods=['GET'])
def proxy_num2info():
    num = request.args.get('num')
    if not num:
        return jsonify({"success": False, "error": "Missing 'num' parameter"}), 400

    # Check if ENV is set
    if not TARGET_NUM2INFO:
        return jsonify({"success": False, "error": "Server config error: TARGET_NUM2INFO is missing."}), 500

    target_url = f"{TARGET_NUM2INFO}{num}"

    try:
        parsed = _fetch_with_fallback(target_url)
        return jsonify(_brand_response(parsed))
    except Exception as e:
        # HARD FAIL-SAFE: Guarantee JSON error, never HTML
        return jsonify({
            "success": False,
            "error": "Upstream API temporarily unreachable. Please try again.",
            "debug": str(e)
        }), 503


# ============================================================
# ENDPOINT 2: TG2Num
# ============================================================
@app.route('/api/tg2num', methods=['GET'])
def proxy_tg2num():
    query = request.args.get('query')
    if not query:
        return jsonify({"success": False, "error": "Missing 'query' parameter"}), 400

    # Check if ENV is set
    if not TARGET_TG2NUM:
        return jsonify({"success": False, "error": "Server config error: TARGET_TG2NUM is missing."}), 500

    target_url = f"{TARGET_TG2NUM}{query}"

    try:
        parsed = _fetch_with_fallback(target_url)
        return jsonify(_brand_response(parsed))
    except Exception as e:
        # HARD FAIL-SAFE: Guarantee JSON error, never HTML
        return jsonify({
            "success": False,
            "error": "Upstream API temporarily unreachable. Please try again.",
            "debug": str(e)
        }), 503


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
