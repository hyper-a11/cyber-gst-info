from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

app = Flask(__name__)

# ===============================================
# 🔐 API KEY DATABASE
API_KEYS = {
    "ZEXX_PAID8DAYS": "2026-02-25",
    "ZEXX_PAID30DAYS": "2026-11-15",
    "FREE1X_TRY": "2026-03-18",
    "OWNER_TEST": "2030-12-31"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.pinelabs.com/"
}

def clean_text(text):
    return text.strip() if text else "NA"

# ===============================================
# 🔹 GST SCRAPING FUNCTION
def get_gst_data(gstin):
    gstin = gstin.strip().upper()
    url = f"https://www.pinelabs.com/gst-number-search/{gstin}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code != 200:
            return {"error": "Source website unreachable"}
        soup = BeautifulSoup(response.text, "html.parser")
    except requests.exceptions.Timeout:
        return {"error": "Request timed out, try again later."}
    except Exception as e:
        return {"error": f"Internal error: {str(e)}"}

    # Helper: find <span> label
    def get_by_label(label_text):
        element = soup.find("span", string=lambda t: t and label_text.lower() in t.lower())
        if element:
            parent = element.find_parent("div")
            if parent:
                value = parent.find("p")
                if value:
                    return clean_text(value.text)
        return "NA"

    # Extract data one by one
    gst_details = {
        "gstin": gstin,
        "legal_name": get_by_label("Legal Name"),
        "trade_name": get_by_label("Trade Name"),
        "status": get_by_label("Status"),
        "state": get_by_label("State"),
        "date_of_registration": get_by_label("Date of Registration"),
        "taxpayer_type": get_by_label("Taxpayer Type"),
        "constitution": get_by_label("Constitution of Business"),
        "nature_of_business": get_by_label("Nature of Business"),
        "principal_place": get_by_label("Principal Place of Business"),
        "additional_places": get_by_label("Additional Places of Business"),
        "ime": datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%d-%m-%Y %H:%M:%S")
    }

    return gst_details

# ===============================================
# 🌐 API ROUTE
@app.route('/', methods=['GET'])
def home():
    gstin = request.args.get('gstin')
    user_key = request.args.get('key')

    # 1️⃣ Validate key
    if not user_key:
        return jsonify({"error": "API Key missing!", "status": "Failed"}), 401
    if user_key not in API_KEYS:
        return jsonify({"error": "Invalid API Key!", "status": "Failed"}), 401

    # 2️⃣ Check expiry
    expiry_str = API_KEYS[user_key]
    tz = pytz.timezone("Asia/Kolkata")
    today = datetime.now(tz).date()
    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
    days_left = (expiry_date - today).days
    if days_left < 0:
        return jsonify({"error": "Key expired", "expiry_date": expiry_str}), 403

    # 3️⃣ GSTIN check
    if not gstin:
        return jsonify({"error": "GSTIN missing. Use ?gstin=GSTIN&key=YOURKEY"}), 400

    # 4️⃣ Get data
    data = get_gst_data(gstin)

    # 5️⃣ Add key & branding info
    data["key_details"] = {
        "expiry_date": expiry_str,
        "days_remaining": f"{days_left} Days" if days_left > 0 else "Last Day Today",
        "status": "Active"
    }
    data["source"] = "@ZEXX_CYBER"
    data["powered_by"] = "@ZEXX_CYBER"

    return jsonify(data)

# Vercel serverless me app.run() nahi chahiye
