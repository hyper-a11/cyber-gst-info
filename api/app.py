from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re

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
    "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
    "Referer": "https://www.pinelabs.com/"
}

def clean(text):
    return text.strip() if text else "NA"

def extract_pan(gstin):
    return gstin[2:12] if len(gstin) == 15 else "NA"

def extract_state_code(gstin):
    return gstin[:2] if len(gstin) >= 2 else "NA"

def split_address(address):
    parts = [p.strip() for p in address.split(",")]
    return {
        "full_address": address,
        "street": parts[0] if len(parts) > 0 else "NA",
        "locality": parts[1] if len(parts) > 1 else "NA",
        "landmark": parts[2] if len(parts) > 2 else "NA",
        "floor": parts[0] if "FLOOR" in parts[0].upper() else "NA",
        "city": parts[-4] if len(parts) >= 4 else "NA",
        "district": parts[-3] if len(parts) >= 3 else "NA",
        "state": parts[-2] if len(parts) >= 2 else "NA",
        "pincode": re.findall(r"\b\d{6}\b", address)[0] if re.findall(r"\b\d{6}\b", address) else "NA",
        "state_code": extract_state_code(gstin_global),
        "country": "India"
    }

# ===============================================
# 🧾 GST SCRAPER
# ===============================================
def get_gst_data(gstin):
    try:
        session = requests.Session()
        r = session.get(
            f"https://www.pinelabs.com/gst-number-search?gstin={gstin}",
            headers=HEADERS,
            timeout=10
        )

        if r.status_code != 200:
            return {"error": "Pinelabs unreachable"}

        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.find_all("div", class_="gst-detail-row")

        raw = {}
        for row in rows:
            label = row.find("div", class_="label")
            value = row.find("div", class_="value")
            if label and value:
                raw[clean(label.text)] = clean(value.text)

        if not raw:
            return {"error": "No GST data found"}

        principal_address = raw.get("Principal Place of Business", "NA")

        status = raw.get("GSTIN / UIN Status", "NA")
        is_active = False if status.upper() in ["SUSPENDED", "CANCELLED"] else True

        reg_date = raw.get("Effective Date of Registration", "NA")
        reg_year = reg_date.split("/")[-1] if "/" in reg_date else "NA"

        return {
            "status": "success",
            "gst_details": {
                "legal_name": raw.get("Legal Name of Business", "NA"),
                "trade_name": raw.get("Trade Name", "NA"),

                "legal_type": raw.get("Constitution of Business", "NA"),
                "business_type": raw.get("Constitution of Business", "NA"),
                "taxpayer_type": raw.get("Taxpayer Type", "NA"),

                "gst_status": status,
                "is_active": is_active,

                "registration_date": reg_date,
                "registration_year": reg_year,

                "gstin": gstin,
                "pan_number": extract_pan(gstin),
                "state_code": extract_state_code(gstin),

                "principal_place": principal_address,
                "other_office": raw.get("Other Office 1", "NA"),
                "office_count": 2 if raw.get("Other Office 1") else 1,

                "principal_address": split_address(principal_address),

                "data_source": "Pinelabs GST Search",
                "last_checked": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
            }
        }

    except Exception as e:
        return {"error": str(e)}

# ===============================================
# 🌐 API ROUTE
# ===============================================
@app.route("/", methods=["GET"])
def gst_api():
    global gstin_global

    gstin = request.args.get("gst") or request.args.get("gstin")
    key = request.args.get("key")

    if not key:
        return jsonify({"status": "Failed", "error": "API key missing"}), 401

    if key not in API_KEYS:
        return jsonify({"status": "Failed", "error": "Invalid API key"}), 401

    expiry = datetime.strptime(API_KEYS[key], "%Y-%m-%d").date()
    today = datetime.now(pytz.timezone("Asia/Kolkata")).date()
    days_left = (expiry - today).days

    if days_left < 0:
        return jsonify({"status": "Expired", "expiry_date": API_KEYS[key]}), 403

    if not gstin:
        return jsonify({"error": "GSTIN missing"}), 400

    gstin_global = gstin.upper()
    data = get_gst_data(gstin_global)

    if "error" in data:
        return jsonify(data), 500

    data["key_details"] = {
        "expiry_date": API_KEYS[key],
        "days_remaining": f"{days_left} Days",
        "status": "Active"
    }
    data["source"] = "@ZEXX_CYBER"
    data["powered_by"] = "@ZEXX_CYBER"

    return jsonify(data)
