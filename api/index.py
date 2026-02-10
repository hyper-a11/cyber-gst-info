
from fastapi import FastAPI, Query, HTTPException
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re

app = FastAPI()

# 🔐 API KEYS
API_KEYS = {
    "ZEXX_PAID8DAYS": "2026-02-25",
    "ZEXX_PAID30DAYS": "2026-11-15",
    "FREE1X_TRY": "2026-03-18",
    "OWNER_TEST": "2030-12-31"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.pinelabs.com/"
}

# ================= HELPERS =================

def gst_active(status):
    return status.upper() == "ACTIVE"

def extract_pan(gstin):
    return gstin[2:12] if len(gstin) >= 12 else "NA"

def extract_state_code(gstin):
    return gstin[:2] if len(gstin) >= 2 else "NA"

def parse_address(addr, state_code):
    return {
        "full_address": addr,
        "street": addr.split(",")[0] if "," in addr else "NA",
        "locality": addr.split(",")[1] if "," in addr else "NA",
        "landmark": addr.split(",")[2] if "," in addr else "NA",
        "floor": "3RD FLOOR" if "FLOOR" in addr.upper() else "NA",
        "city": "HOWRAH" if "HOWRAH" in addr.upper() else "NA",
        "district": "Howrah",
        "state": "West Bengal",
        "pincode": re.findall(r"\b\d{6}\b", addr)[0] if re.findall(r"\b\d{6}\b", addr) else "NA",
        "state_code": state_code,
        "country": "India"
    }

# ================= GST SCRAPER =================

def fetch_gst_data(gstin):
    url = f"https://www.pinelabs.com/gst-number-search?gstin={gstin}"
    r = requests.get(url, headers=HEADERS, timeout=10)

    soup = BeautifulSoup(r.text, "html.parser")
    data = {}

    for row in soup.find_all("div"):
        if row.find("span") and row.find("p"):
            key = row.find("span").text.strip()
            val = row.find("p").text.strip()
            data[key] = val

    if not data:
        raise Exception("GST data not found")

    gst_status = data.get("GSTIN / UIN Status", "NA")
    reg_date = data.get("Effective Date of Registration", "NA")
    state_code = extract_state_code(gstin)
    principal_place = data.get("Principal Place of Business", "NA")

    return {
        "status": "success",
        "gst_details": {
            "legal_name": data.get("Legal Name of Business", "NA"),
            "trade_name": data.get("Trade Name", "NA"),

            "legal_type": data.get("Constitution of Business", "NA"),
            "business_type": data.get("Constitution of Business", "NA"),
            "taxpayer_type": data.get("Taxpayer Type", "NA"),

            "gst_status": gst_status,
            "is_active": gst_active(gst_status),

            "registration_date": reg_date,
            "registration_year": reg_date.split("/")[-1] if "/" in reg_date else "NA",

            "gstin": gstin,
            "pan_number": extract_pan(gstin),
            "state_code": state_code,

            "principal_place": principal_place,
            "other_office": data.get("Other Office 1", "NA"),
            "office_count": 2 if data.get("Other Office 1") else 1,

            "principal_address": parse_address(principal_place, state_code),

            "data_source": "Pinelabs GST Search",
            "last_checked": datetime.now(
                pytz.timezone("Asia/Kolkata")
            ).strftime("%Y-%m-%d %H:%M:%S")
        }
    }

# ================= API ROUTE =================

@app.get("/")
def gst_api(
    gst: str = Query(None),
    key: str = Query(None)
):
    if not key or key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    expiry = datetime.strptime(API_KEYS[key], "%Y-%m-%d").date()
    today = datetime.now(pytz.timezone("Asia/Kolkata")).date()
    days_left = (expiry - today).days

    if days_left < 0:
        raise HTTPException(status_code=403, detail="API key expired")

    if not gst:
        raise HTTPException(status_code=400, detail="GSTIN missing")

    result = fetch_gst_data(gst.upper())

    result["key_details"] = {
        "expiry_date": API_KEYS[key],
        "days_remaining": f"{days_left} Days",
        "status": "Active"
    }

    result["source"] = "@ZEXX_CYBER"
    result["powered_by"] = "@ZEXX_CYBER"

    return result
