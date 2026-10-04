import os
from flask import Flask, request, jsonify
import httpx

app = Flask(__name__)

# Load target API base URL from environment variables (set in Render)
TARGET_API_BASE = os.environ.get("TARGET_API_URL", "")

@app.route('/health', methods=['GET', 'HEAD'])
def health_check():
    """
    UptimeRobot will ping this endpoint every 5 minutes.
    Returns 200 OK to keep the Render instance awake.
    """
    return "", 200

@app.route('/api', methods=['GET'])
def proxy_api():
    # Extract the 'num' parameter sent by your Telegram bot
    num = request.args.get('num')
    
    if not num:
        return jsonify({"error": "Missing 'num' parameter"}), 400

    if not TARGET_API_BASE:
        return jsonify({"error": "Server configuration error: Target API URL is missing."}), 500

    # Build the full target URL securely
    # Assuming TARGET_API_BASE ends with "=" or "&num="
    if TARGET_API_BASE.endswith("=") or TARGET_API_BASE.endswith("&"):
        target_url = f"{TARGET_API_BASE}{num}"
    else:
        target_url = f"{TARGET_API_BASE}{num}"

    # Browser headers to help bypass basic blocks
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        # Fetch data from the hidden target API
        response = httpx.get(target_url, headers=headers, timeout=15, follow_redirects=True)
        
        # Detect anti-bot HTML challenge
        if "<html" in response.text.lower() or "<!doctype" in response.text.lower():
            return jsonify({"error": "Blocked by target anti-bot (HTML challenge)"}), 503
            
        # Return the JSON data back to your Telegram bot
        return jsonify(response.json())

    except Exception as e:
        return jsonify({"error": f"Proxy error: {str(e)}"}), 500

if __name__ == '__main__':
    # Render requires binding to 0.0.0.0 and the assigned PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
