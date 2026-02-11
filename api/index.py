from flask import Flask, request, jsonify
import requests
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
# ⚙️ CONFIG
# ===============================================
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

IST = pytz.timezone("Asia/Kolkata")

# ===============================================
# 🔍 REAL GST DATA FETCH (JSON SOURCE)
# ===============================================
def get_gst_data(gstin):
    gstin = gstin.upper().strip()

    url = f"https://gstapi.charteredinfo.com/commonapi/gstreturntracker.ashx?gstin={gstin}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            raise Exception("GST source down")

        raw = r.json()
    except:
        raw = {}

    gst_details = {
        "legal_name": raw.get("lgnm", "NA"),
        "trade_name": raw.get("tradeNam", "NA"),
        "legal_type": raw.get("ctb", "NA"),
        "business_type": raw.get("nba", "NA"),
        "taxpayer_type": raw.get("dty", "NA"),
        "gst_status": raw.get("sts", "NA"),
        "is_active": True if raw.get("sts") == "Active" else False,
        "registration_date": raw.get("rgdt", "NA"),
        "registration_year": raw.get("rgdt", "NA")[:4] if raw.get("rgdt") else "NA",
        "gstin": gstin,
        "pan_number": gstin[2:12] if len(gstin) >= 12 else "NA",
        "state_code": gstin[:2],
        "principal_place": raw.get("pradr", {}).get("addr", {}).get("loc", "NA"),
        "other_office": "NA",
        "office_count": 1,
        "principal_address": raw.get("pradr", {}),
        "data_source": "Public GST JSON Source",
        "last_checked": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    }

    return {
        "status": "success",
        "gst_details": gst_details
    }

# ===============================================
# 🌐 API ROUTE
# ===============================================
@app.route("/", methods=["GET"])
def gst_api():
    gstin = request.args.get("gst") or request.args.get("num")
    key = request.args.get("key")

    if not key:
        return jsonify({"status": "Failed", "error": "API Key missing"}), 401

    if key not in API_KEYS:
        return jsonify({"status": "Failed", "error": "Invalid API Key"}), 401

    expiry = datetime.strptime(API_KEYS[key], "%Y-%m-%d").date()
    today = datetime.now(IST).date()
    days_left = (expiry - today).days

    if days_left < 0:
        return jsonify({
            "status": "Expired",
            "error": "Key Expired",
            "expiry_date": API_KEYS[key]
        }), 403

    if not gstin:
        return jsonify({
            "status": "Failed",
            "error": "GST Number missing",
            "usage": "?gst=27AAPFU0939F1ZV&key=YOURKEY"
        }), 400

    data = get_gst_data(gstin)

    data["key_details"] = {
        "expiry_date": API_KEYS[key],
        "days_remaining": f"{days_left} Days" if days_left > 0 else "Last Day",
        "status": "Active"
    }

    data["source"] = "@ZEXX_CYBER"
    data["powered_by"] = "@CYBER×CHAT"

    return jsonify(data)
