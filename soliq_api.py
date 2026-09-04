import requests
import hashlib
import hmac
import time
import json
from urllib.parse import urlparse, parse_qs
import logging

API = "https://new-ofd.soliq.uz/api/payment"
SECRET = "thisIsPaymentSecretKey123@#"

def get_value(data, *keys, default="-"):
    """Ищет значение по нескольким возможным ключам."""
    for key in keys:
        if isinstance(data, dict) and key in data:
            return data[key]
    return default

def get_receipt_data(url: str) -> dict | None:
    """
    Parses the Soliq URL and fetches receipt data from the API.
    Returns the parsed JSON dictionary or None if it fails.
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    terminal_id = params.get("t", [None])[0]
    payment_no = params.get("r", [None])[0]
    payment_date = params.get("c", [None])[0]
    fiscal_sign = params.get("s", [None])[0]
    fiscal_sign_hash = params.get("h", [None])[0]

    if not terminal_id or not payment_no or not payment_date:
        logging.error("Failed to find required params (t, r, c) in URL")
        return None

    data = {
        "terminalId": terminal_id,
        "paymentNo": payment_no,
        "paymentDate": payment_date,
        "paymentType": "CHECK",
    }

    if fiscal_sign:
        data["fiscalSign"] = fiscal_sign
    if fiscal_sign_hash:
        data["fiscalSignHash"] = fiscal_sign_hash

    timestamp = str(int(time.time()))
    message = f"{terminal_id}:{payment_no}:{timestamp}"

    signature = hmac.new(
        SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Timestamp": timestamp,
        "X-Signature": signature,
    }

    try:
        response = requests.post(API, json=data, headers=headers, timeout=20)
        if response.status_code != 200:
            logging.error(f"Soliq API returned status {response.status_code}: {response.text}")
            return None
            
        result = response.json()
        receipt = result.get("data", result)
        if not isinstance(receipt, dict):
            logging.error(f"Unexpected response format: {result}")
            return None
            
        return receipt
    except Exception as e:
        logging.error(f"Error fetching from Soliq API: {e}")
        return None
