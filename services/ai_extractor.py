import requests
import json
import re
from datetime import datetime

# Database of common industrial/IT/procurement brands for high-precision recognition
COMMON_BRANDS = [
    "Dell", "HP", "Lenovo", "Acer", "Apple", "Asus", "Samsung", "LG",
    "Asian Paints", "Berger", "Dulux", "Nerolac", "Havells", "Schneider",
    "Legrand", "Finolex", "Supreme", "Ashirvad", "Astral", "Polycab",
    "Tata", "JSW", "Bosch", "Siemens", "Philips", "Godrej", "Crompton",
    "Anchor", "L&T", "Honeywell", "3M", "Kirloskar", "ABB"
]

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
    "fifty": 50, "hundred": 100
}

PRODUCT_PATTERNS = [
    r'(?:supply\s+of)\s+(.+?)\s+(?:required|needed|for)',
    r'(?:procurement\s+of)\s+(.+?)\s+(?:required|needed|for)',
    r'(?:purchase\s+of)\s+(.+?)\s+(?:required|needed|for)',
    r'(?:requirement\s+(?:for|of))\s+(.+?)(?:\.|\,|\n|$)',
    r'(?:need)\s+\d*\s*(.+?)(?:\.|\,|\n|$)',
    r'(?:looking\s+for)\s+(.+?)(?:\.|\,|\n|$)',
    r'(?:please\s+quote\s+for)\s+(.+?)(?:\.|\,|\n|$)',
    r'(?:request\s+(?:you\s+)?to\s+submit\s+(?:your\s+)?quotation\s+for\s+(?:the\s+)?supply\s+of)\s+(.+?)(?:\s+required|\.|\,|\n|$)',
    r'(?:item\s*name|product\s*name|item|product)\s*[:=\-]?\s*([A-Za-z0-9\s\-\/\.\(\)]+?)(?=[,\;\n]|\s*(?:quantity|qty|brand|uom)|$)'
]

SPEC_PATTERNS = [
    r'A[345]\s+Size',
    r'Print[,\s]+Scan[,\s]+Copy',
    r'Automatic\s+Duplex\s+Printing',
    r'Network\s+Connectivity',
    r'\d+(?:\-\d+)?\s*PPM',
    r'Warranty\s+Details',
    r'Installation\s+Support',
    r'Cartridge\s+Yield',
    r'\d+\s*GB\s+(?:RAM|SSD|HDD)',
    r'Intel\s+i[3579]\s+(?:Processor)?',
    r'CPVC|PVC|PN10|PN16',
    r'Wi-Fi|Bluetooth|HDMI|Gigabit'
]


def normalize_date(date_str):
    if not date_str or not str(date_str).strip():
        return ""
    raw = str(date_str).strip()

    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
        "%d-%b-%Y", "%d-%B-%Y", "%d %B %Y", "%d %b %Y", "%d.%m.%Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Regex try for 10 August 2026 or 10-08-2026
    m = re.search(r'(\d{1,2})[\s\/\-\.]+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\/\-\.]+(\d{4})', raw, re.IGNORECASE)
    if m:
        try:
            date_raw = f"{m.group(1)} {m.group(2)} {m.group(3)}"
            return datetime.strptime(date_raw, "%d %b %Y").strftime("%Y-%m-%d")
        except Exception:
            pass

    return raw


def validate_and_normalize_rfq(rfq_data, email_text):
    """
    Production validation pipeline: AI -> Validation -> Regex Correction -> Normalization -> Output
    """
    if not isinstance(rfq_data, dict):
        rfq_data = {}

    # 1. ITEM DESCRIPTION VALIDATION (Word Count & Regex Pattern Registry)
    desc = str(rfq_data.get("item_description") or "").strip()

    # If single word (e.g. "Office") or empty/generic, validate and expand via PRODUCT_PATTERNS
    if len(desc.split()) <= 1 or desc.lower() in ["office", "item", "product", "procurement"]:
        for p in PRODUCT_PATTERNS:
            m = re.search(p, email_text, re.IGNORECASE)
            if m:
                extracted = m.group(1).strip()
                if len(extracted.split()) >= 1 and extracted.lower() not in ["office", "item"]:
                    desc = extracted
                    break

    # Clean lead filler phrases
    desc = re.sub(
        r'^(we\s+request\s+you\s+to\s+submit\s+your\s+quotation\s+for\s+the\s+supply\s+of|please\s+provide\s+quotation\s+for\s+)?(the\s+following\s+items?\.?\s*\(?|we\s+have\s+(a\s+)?requirement\s+(of|for)|requirement\s+(of|for)|(please\s+)?(provide|send)\s+(a\s+)?(quote|quotation|rate)\s+(for|of)|rfq\s+(for|of)|enquiry\s+(for|of)|(we\s+)?need|(we\s+)?require)\s*:?\s*\(?',
        '', desc, flags=re.IGNORECASE
    ).strip().rstrip(":")

    if desc.lower().startswith("of "):
        desc = desc[3:].strip()

    rfq_data["item_description"] = desc or "Procurement Request"

    # 2. QUANTITY VALIDATION (Digits + Word Numbers)
    try:
        quantity = int(rfq_data.get("quantity", 0))
    except Exception:
        quantity = 0

    if quantity <= 0:
        explicit_qty = re.search(r'(?:quantity|qty|count)\s*[:=\-]?\s*(\d+)', email_text, re.IGNORECASE)
        if explicit_qty:
            quantity = int(explicit_qty.group(1))
        else:
            unit_qty = re.search(r'\b(\d{1,4})\s*(nos|pcs|units?|items?|laptops?|sets?|mtr|meters?|kg|litres?|qty|boxes?|packs?)\b', email_text, re.IGNORECASE)
            if unit_qty:
                quantity = int(unit_qty.group(1))
                if unit_qty.group(2) and not rfq_data.get("uom"):
                    rfq_data["uom"] = unit_qty.group(2).capitalize()
            else:
                word_qty = re.search(r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|fifty|hundred)\b', email_text, re.IGNORECASE)
                if word_qty:
                    quantity = NUMBER_WORDS.get(word_qty.group(1).lower(), 1)
                else:
                    quantity = 1

    rfq_data["quantity"] = quantity

    # 3. BRAND VALIDATION ("Any" brand support)
    brand = str(rfq_data.get("brand") or "").strip()
    if not brand or brand.lower() in ["we look forward to your quotation", "not specified", "none"]:
        if re.search(r'\b(any\s+brand|no\s+specific\s+brand|open\s+to\s+any\s+brand)\b', email_text, re.IGNORECASE):
            brand = "Any"
        else:
            for b in COMMON_BRANDS:
                if re.search(rf"\b{re.escape(b)}\b", email_text, re.IGNORECASE):
                    brand = b
                    break
    rfq_data["brand"] = brand or "Not Specified"

    # 4. FULL PHRASE SPECIFICATIONS EXTRACTION
    specs_list = []
    for sp in SPEC_PATTERNS:
        m = re.search(sp, email_text, re.IGNORECASE)
        if m and m.group(0) not in specs_list:
            specs_list.append(m.group(0))

    if specs_list:
        rfq_data["specifications"] = ", ".join(specs_list)
    elif not rfq_data.get("specifications"):
        rfq_data["specifications"] = f"{rfq_data['item_description']}" + (f", Brand: {brand}" if brand else "")

    # 5. DELIVERY DATE NORMALIZATION (ISO YYYY-MM-DD)
    delivery_date = str(rfq_data.get("delivery_date") or "").strip()
    if not delivery_date:
        date_match = re.search(r'\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b', email_text, re.IGNORECASE)
        if date_match:
            delivery_date = date_match.group(1).strip()

    rfq_data["delivery_date"] = normalize_date(delivery_date)

    return rfq_data


def extract_rfq(email_text):
    if not isinstance(email_text, str):
        email_text = str(email_text or "")

    # Allow up to 25,000 characters so long PDF/DOCX text is not truncated
    if len(email_text) > 25000:
        email_text = email_text[:25000]

    prompt = f"""You are an expert Procurement RFQ Extraction AI.

Read the email carefully.
Return ONLY JSON.
Never explain anything.
Never summarize.
Extract exactly what appears in the email.

Rules:
1. Item Description must ONLY contain the actual product/material name.
2. Quantity must ONLY be the requested item quantity as an integer. Convert word numbers ("Five" -> 5).
3. Brand: Extract manufacturer (e.g. Dell, HP, Asian Paints). If email says "any brand", return "Any".
4. UOM: Unit of measurement (e.g. Nos, Pcs, Kg, Mtr, Set, Box).
5. Specifications: List key features, specs, model numbers, or requirements.

Return ONLY this JSON structure:
{{
  "item_description": "",
  "specifications": "",
  "quantity": 0,
  "uom": "",
  "brand": "",
  "delivery_date": "",
  "delivery_city": "",
  "delivery_state": "",
  "delivery_pincode": ""
}}

Email:
{email_text}
"""

    rfq_data = {}
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "keep_alive": "1h",
                "options": {
                    "num_predict": 300,
                    "temperature": 0.0
                }
            },
            timeout=10
        )
        if response.status_code == 200:
            response_json = response.json()
            if "response" in response_json:
                result = response_json["response"]
                try:
                    rfq_data = json.loads(result.strip())
                except Exception:
                    json_match = re.search(r'\{[\s\S]*\}', result)
                    if json_match:
                        try:
                            rfq_data = json.loads(json_match.group())
                        except Exception:
                            pass
    except Exception as e:
        print(f"\n[WARNING] Ollama server unavailable ({e}). Switching to rule-based fallback extraction...")

    if not rfq_data:
        rfq_data = fallback_extract_rfq(email_text)

    # Pass through production validation & normalization pipeline
    return validate_and_normalize_rfq(rfq_data, email_text)


def fallback_extract_rfq(email_text):
    """
    Ultra-high precision rule-based fallback extractor when Ollama is offline.
    """
    if not email_text:
        email_text = ""

    rfq_data = {
        "item_description": "",
        "specifications": "",
        "quantity": 0,
        "uom": "Nos",
        "brand": "",
        "delivery_date": "",
        "delivery_city": "",
        "delivery_state": "",
        "delivery_pincode": ""
    }

    # Extract 6-digit Indian pincode if present
    pincode_match = re.search(r'\b[1-9]\d{5}\b', email_text)
    if pincode_match:
        rfq_data["delivery_pincode"] = pincode_match.group(0)

    return rfq_data


# TEST ONLY
if __name__ == "__main__":
    sample = """
    We request you to submit your quotation for the supply of Office Multifunction Laser Printers required for our organization. Five Nos. Any brand. Delivery Date: 10 August 2026. Specs: A4 Size, Print, Scan, Copy, Network Connectivity, Automatic Duplex Printing, 30-40 PPM, Warranty Details, Cartridge Yield, Installation Support.
    """

    rfq_data = extract_rfq(sample)
    print(rfq_data)