from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

app = Flask(__name__)

# ===============================================
# 🔐 API KEY DATABASE
# ===============================================
API_KEYS = {
    "ZEXX_PAID8DAYS": "2026-02-25",
    "ZEXX_PAID30DAYS": "2026-11-15",
    "FREE1X_TRY": "2026-03-18",
    "OWNER_TEST": "2030-12-31" 
}

# ===============================================
# ⚙️ CONFIGURATION
# ===============================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
}

def clean_text(text):
    if not text:
        return "NA"
    return text.strip()

# ===============================================
# 🔍 GST SCRAPING LOGIC
# ===============================================
def get_gst_data(gst_number):
    gst = gst_number.strip().upper()
    url = f"https://www.pinelabs.com/gst-number-search?gstin={gst}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=9)
        if response.status_code != 200:
            return {"error": "Source website unreachable"}
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        return {"error": str(e)}

    # This part depends on the HTML structure of Pinelabs GST search
    # For demo, let's assume a JSON response is embedded in a <pre> or script tag
    import json
    try:
        # Try to find JSON in <pre> tag
        pre_tag = soup.find("pre")
        if pre_tag:
            gst_json = json.loads(pre_tag.text)
        else:
            # fallback: empty
            gst_json = {}
    except:
        gst_json = {}

    # Map to your output structure
    gst_details = {
        "legal_name": gst_json.get("legal_name", "NA"),
        "trade_name": gst_json.get("trade_name", "NA"),
        "legal_type": gst_json.get("legal_type", "NA"),
        "business_type": gst_json.get("business_type", "NA"),
        "taxpayer_type": gst_json.get("taxpayer_type", "NA"),
        "gst_status": gst_json.get("gst_status", "NA"),
        "is_active": gst_json.get("is_active", False),
        "registration_date": gst_json.get("registration_date", "NA"),
        "registration_year": gst_json.get("registration_year", "NA"),
        "gstin": gst_json.get("gstin", gst),
        "pan_number": gst_json.get("pan_number", "NA"),
        "state_code": gst_json.get("state_code", "NA"),
        "principal_place": gst_json.get("principal_place", "NA"),
        "other_office": gst_json.get("other_office", "NA"),
        "office_count": gst_json.get("office_count", 1),
        "principal_address": gst_json.get("principal_address", {}),
        "data_source": "Pinelabs GST Search",
        "last_checked": datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d %H:%M:%S")
    }

    return {
        "status": "success",
        "gst_details": gst_details
    }

# ===============================================
# 🌐 API ROUTE WITH KEY AUTH
# ===============================================
@app.route('/', methods=['GET'])
def home():
    gst_number = request.args.get('gst') or request.args.get('num')
    user_key = request.args.get('key')

    if not user_key:
        return jsonify({"error": "API Key missing!", "status": "Failed"}), 401
    
    if user_key not in API_KEYS:
        return jsonify({"error": "Invalid API Key!", "status": "Failed"}), 401

    # Expiry Logic
    expiry_str = API_KEYS[user_key]
    tz_india = pytz.timezone('Asia/Kolkata')
    today = datetime.now(tz_india).date()
    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
    delta = expiry_date - today
    days_left = delta.days

    if days_left < 0:
        return jsonify({
            "error": "Key Expired!",
            "expiry_date": expiry_str,
            "status": "Expired",
            "message": f"Aapki key {expiry_str} ko khatam ho chuki hai."
        }), 403

    if not gst_number:
        return jsonify({
            "error": "GST Number missing. Use ?gst=NUMBER&key=YOURKEY",
            "key_details": {
                "expiry_date": expiry_str,
                "days_remaining": f"{days_left} Days" if days_left > 0 else "Last Day Today",
                "status": "Active"
            }
        }), 400

    data = get_gst_data(gst_number)
    if "error" in data:
        return jsonify(data), 500

    data["key_details"] = {
        "expiry_date": expiry_str,
        "days_remaining": f"{days_left} Days" if days_left > 0 else "Last Day Today",
        "status": "Active"
    }
    data["source"] = "@ZEXX_CYBER"
    data["powered_by"] = "@ZEXX_CYBER"

    return jsonify(data)

# Local testing
if __name__ == '__main__':
    app.run(debug=True)
