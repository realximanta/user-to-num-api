import os
import json
import re
from flask import Flask, request, jsonify
import cloudscraper
import httpx

app = Flask(__name__)

TARGET_API_BASE = os.environ.get("TARGET_API_URL", "")

@app.route('/health', methods=['GET', 'HEAD'])
def health_check():
    return "", 200

@app.route('/api', methods=['GET'])
def proxy_api():
    num = request.args.get('num')
    
    if not num:
        return jsonify({"error": "Missing 'num' parameter"}), 400

    if not TARGET_API_BASE:
        return jsonify({"error": "Server configuration error: Target API URL is missing."}), 500

    # Build target URL
    if TARGET_API_BASE.endswith("=") or TARGET_API_BASE.endswith("&"):
        target_url = f"{TARGET_API_BASE}{num}"
    else:
        target_url = f"{TARGET_API_BASE}{num}"

    # --- STRATEGY 1: Use CloudScraper (Bypasses JS challenges) ---
    try:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        response = scraper.get(target_url, timeout=20)
        
        if response.status_code == 200 and "<html" not in response.text.lower():
            return jsonify(response.json())
    except Exception as e:
        pass # Move to fallback

    # --- STRATEGY 2: Use Jina.ai Reader (Executes JS and returns text) ---
    try:
        jina_url = f"https://r.jina.ai/{target_url}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = httpx.get(jina_url, headers=headers, timeout=25)
        
        if response.status_code == 200:
            # Jina returns Markdown. We extract the JSON block from it.
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                json_data = json.loads(match.group(0))
                return jsonify(json_data)
    except Exception as e:
        pass

    # --- FAILED ---
    return jsonify({"error": "Blocked by target anti-bot. Both CloudScraper and Jina fallback failed."}), 503

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
