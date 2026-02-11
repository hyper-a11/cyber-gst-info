from flask import Flask, request, jsonify
import requests
from datetime import datetime
import pytz
import json

app = Flask(__name__)

# ===============================================
# 🔐 API KEYS
# ===============================================
API_KEYS = {
    "ZEXX_PAID8DAYS": "2026-02-25",
    "ZEXX_PAID30DAYS": "2026-11-15",
    "FREE1X_TRY": "2026-03-18",
    "OWNER_TEST": "2030-12-31"
}

# ===============================================
# ⚙️ CONFIG
# ===============================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Referer": "https://www.pinelabs.com/"
}

def clean_text(text):
    if not text:
        return "NA"
    return text.strip()

# ===============================================
# 🔍 GST SCRAPING
# ===============================================
def get_gst_data(gst_number):
    gst = gst_number.strip().upper()
    url = f"https://gstapi.charteredinfo.com/commonapi/gstreturntracker.ashx?gstin={gst}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        response.raise_for_status()
        gst_json = response.json()
    except Exception as e:
        return {"status": "failed", "error": str(e)}

    # Mapping output
    gst_details = {
        "gstin": gst,
        "legal_name": gst_json.get("LegalName", "NA"),
        "trade_name": gst_json.get("TradeName", "NA"),
        "legal_type": gst_json.get("LegalType", "NA"),
        "business_type": gst_json.get("BusinessType", "NA"),
        "taxpayer_type": gst_json.get("TaxpayerType", "NA"),
        "gst_status": gst_json.get("GSTStatus", "NA"),
        "is_active": gst_json.get("IsActive", False),
        "registration_date": gst_json.get("RegistrationDate", "NA"),
        "registration_year": gst_json.get("RegistrationYear", "NA"),
        "pan_number": gst_json.get("PANNumber", "NA"),
        "state_code": gst_json.get("StateCode", "NA"),
        "principal_place": gst_json.get("PrincipalPlace", "NA"),
        "other_office": gst_json.get("OtherOffice", "NA"),
        "office_count": gst_json.get("OfficeCount", 0),
        "principal_address": gst_json.get("PrincipalAddress", {}),
        "data_source": "CYBER_ZEXX",
        "last_checked": datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d %H:%M:%S")
    }

    return {"status": "success", "gst_details": gst_details}

# ===============================================
# 🌐 API ROUTE
# ===============================================
@app.route("/", methods=["GET"])
def home():
    try:
        gst = request.args.get("gst")
        user_key = request.args.get("key")

        # 1️⃣ Key validation
        if not user_key:
            return jsonify({"error": "API Key missing!", "status": "Failed"}), 401
        if user_key not in API_KEYS:
            return jsonify({"error": "Invalid API Key!", "status": "Failed"}), 401

        # 2️⃣ Key expiry check
        expiry_str = API_KEYS[user_key]
        tz = pytz.timezone("Asia/Kolkata")
        today = datetime.now(tz).date()
        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
        days_left = (expiry_date - today).days

        if days_left < 0:
            return jsonify({
                "error": "Key Expired!",
                "expiry_date": expiry_str,
                "status": "Expired",
                "message": f"Aapki key {expiry_str} ko khatam ho chuki hai."
            }), 403

        # 3️⃣ GST check
        if not gst:
            return jsonify({
                "error": "GST Number missing. Use ?gst=NUMBER&key=YOURKEY",
                "key_details": {
                    "expiry_date": expiry_str,
                    "days_remaining": f"{days_left} Days" if days_left > 0 else "Last Day Today",
                    "status": "Active"
                }
            }), 400

        # 4️⃣ Fetch GST Data
        data = get_gst_data(gst)

        # 5️⃣ Add branding & key info
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

    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500
