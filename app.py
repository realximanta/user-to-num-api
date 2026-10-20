import os
import json
import re
from flask import Flask, request, jsonify, render_template
import httpx

# Try importing the dedicated InfinityFree bypass module
try:
    from infinityfree import Bypasse
    HAS_INFINITYFREE = True
except ImportError:
    HAS_INFINITYFREE = False

app = Flask(__name__)

# ============================================================
# YOUR BRANDING
# ============================================================
YOUR_OWNER          = "@b4nzw"
YOUR_POWERED_BY     = "编码者 𝗧𝘂𝗸𝘂"
YOUR_POWERED_BY_URL = "https://t.me/tukuexe"

# ============================================================
# ENV
# ============================================================
TARGET_NUM2INFO = os.environ.get("TARGET_NUM2INFO")
TARGET_TG2NUM   = os.environ.get("TARGET_TG2NUM")

# ============================================================
# ROOT — Landing page
# ============================================================
@app.route('/', methods=['GET'])
def landing():
    return render_template(
        'index.html', 
        owner=YOUR_OWNER, 
        powered_by=YOUR_POWERED_BY, 
        powered_by_url=YOUR_POWERED_BY_URL
    )

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
    Attempts to fetch the target URL using InfinityFree Bypass, 
    then Jina.ai. Returns parsed JSON or raises Exception.
    """
    error_log = []

    # Strategy 1: InfinityFree Dedicated Bypass
    if HAS_INFINITYFREE:
        try:
            response = Bypasse.get(target_url)
            if response.status_code == 200 and "<html" not in response.text.lower():
                return response.json()
            else:
                error_log.append(f"InfinityFree Bypass returned non-JSON (Status: {response.status_code})")
        except Exception as e:
            error_log.append(f"InfinityFree Bypass Error: {str(e)}")
    else:
        error_log.append("infinityfree module not installed.")

    # Strategy 2: Jina.ai Reader
    try:
        jina_url = f"https://r.jina.ai/{target_url}"
        response = httpx.get(jina_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
        if response.status_code == 200:
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            else:
                error_log.append("Jina returned 200 but no JSON found.")
        else:
            error_log.append(f"Jina failed with status {response.status_code}")
    except Exception as e:
        error_log.append(f"Jina Error: {str(e)}")

    raise Exception(" | ".join(error_log))

# ============================================================
# ENDPOINT 1: Num2Info
# ============================================================
@app.route('/api/num2info', methods=['GET'])
def proxy_num2info():
    num = request.args.get('num')
    if not num:
        return jsonify({"success": False, "error": "Missing 'num' parameter"}), 400

    if not TARGET_NUM2INFO:
        return jsonify({"success": False, "error": "Server config error: TARGET_NUM2INFO is missing."}), 500

    target_url = f"{TARGET_NUM2INFO}{num}"

    try:
        parsed = _fetch_with_fallback(target_url)
        return jsonify(_brand_response(parsed))
    except Exception as e:
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

    if not TARGET_TG2NUM:
        return jsonify({"success": False, "error": "Server config error: TARGET_TG2NUM is missing."}), 500

    target_url = f"{TARGET_TG2NUM}{query}"

    try:
        parsed = _fetch_with_fallback(target_url)
        return jsonify(_brand_response(parsed))
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Upstream API temporarily unreachable. Please try again.",
            "debug": str(e)
        }), 503

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
