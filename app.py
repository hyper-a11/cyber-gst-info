from flask import Flask, request, jsonify
import requests
from datetime import datetime
import pytz
import json

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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
    "Referer": "https://charteredinfo.com/",
    "Origin": "https://charteredinfo.com",
    "Connection": "keep-alive"
}

IST = pytz.timezone("Asia/Kolkata")

def na(val):
    return val if val not in [None, "", []] else "NA"

# ===============================================
# 🔍 GST DATA FETCH LOGIC
# ===============================================
def get_gst_data(gstin):
    gstin = gstin.strip().upper()
    url = f"https://gstapi.charteredinfo.com/commonapi/gstreturntracker.ashx?gstin={gstin}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return {"error": f"GST source unreachable (Status {r.status_code})"}
        raw = r.json()
    except Exception as e:
        return {"error": str(e)}

    pradr = raw.get("pradr", {})
    addr = pradr.get("addr", {})

    gst_details = {
        "gstin": gstin,
        "legal_name": na(raw.get("lgnm")),
        "trade_name": na(raw.get("tradeNam")),
        "constitution_of_business": na(raw.get("ctb")),
        "taxpayer_type": na(raw.get("dty")),
        "gst_status": na(raw.get("sts")),
        "is_active": raw.get("sts") == "Active",
        "registration_date": na(raw.get("rgdt")),
        "registration_year": raw.get("rgdt")[:4] if raw.get("rgdt") else "NA",
        "pan_number": gstin[2:12],
        "state_code": gstin[:2],
        "business_nature": na(pradr.get("ntr")),
        "principal_place": {
            "building_name": na(addr.get("bnm")),
            "street": na(addr.get("st")),
            "location": na(addr.get("loc")),
            "district": na(addr.get("dst")),
            "state": na(addr.get("stcd")),
            "pincode": na(addr.get("pncd"))
        },
        "data_source": "CharteredInfo GST API",
        "last_checked": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    }

    return {"status": "success", "gst_details": gst_details}

# ===============================================
# 🌐 API ROUTE WITH KEY AUTH
# ===============================================
@app.route("/", methods=["GET"])
def home():
    gstin = request.args.get("gst") or request.args.get("num")
    user_key = request.args.get("key")

    # 🔑 Key validation
    if not user_key:
        return jsonify({"status": "Failed", "error": "API Key missing"}), 401

    if user_key not in API_KEYS:
        return jsonify({"status": "Failed", "error": "Invalid API Key"}), 401

    # ⏳ Expiry check
    expiry_str = API_KEYS[user_key]
    today = datetime.now(IST).date()
    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
    days_left = (expiry_date - today).days

    if days_left < 0:
        return jsonify({
            "status": "Expired",
            "error": "Key Expired",
            "expiry_date": expiry_str
        }), 403

    if not gstin:
        return jsonify({
            "status": "Failed",
            "error": "GST number missing. Use ?gst=GSTIN&key=YOURKEY",
            "key_details": {
                "expiry_date": expiry_str,
                "days_remaining": f"{days_left} Days",
                "status": "Active"
            }
        }), 400

    # 📡 Fetch GST data
    data = get_gst_data(gstin)

    if "error" in data:
        return jsonify(data), 500

    # 🔖 Branding, key info, and ime field
    data["ime"] = "GST"
    data["key_details"] = {
        "expiry_date": expiry_str,
        "days_remaining": f"{days_left} Days" if days_left > 0 else "Last Day Today",
        "status": "Active"
    }
    data["source"] = "@ZEXX_CYBER"
    data["powered_by"] = "@CYBER×CHAT"

    return jsonify(data)

# ===============================================
# ▶️ Local Run (for testing)
# ===============================================
if __name__ == "__main__":
    app.run(debug=True)
