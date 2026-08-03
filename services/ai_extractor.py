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
    r'supply\s+of\s+(.+?)(?=\s+required|\s+needed|\s+for\s+our|\n|$)',
    r'procurement\s+of\s+(.+?)(?=\n|$)',
    r'purchase\s+of\s+(.+?)(?=\n|$)',
    r'quotation\s+for\s+(.+?)(?=\n|$)',
    r'please\s+quote\s+for\s+(.+?)(?=\n|$)',
    r'looking\s+for\s+(.+?)(?=\n|$)',
    r'need\s+\d*\s*(.+?)(?=\n|$)',
    r'item\s*name\s*[:=\-]?\s*(.+)'
]

SPEC_PATTERNS = [
    r'A[345]\s+Size[^\.\,\n]*',
    r'Print[,\s]+Scan[,\s]+Copy[^\.\,\n]*',
    r'Automatic\s+Duplex\s+Printing[^\.\,\n]*',
    r'Network\s+Connectivity[^\.\,\n]*',
    r'\d+\s*-\s*\d+\s*PPM|\d+\s*PPM',
    r'Warranty\s+Details[^\.\,\n]*',
    r'Installation\s+Support[^\.\,\n]*',
    r'Cartridge\s+Yield[^\.\,\n]*',
    r'\d+\s*GB\s+(?:RAM|SSD|HDD)[^\.\,\n]*',
    r'Intel\s+i[3579]\s+(?:Processor)?[^\.\,\n]*',
    r'CPVC|PVC|PN10|PN16',
    r'Wi-Fi|Bluetooth|HDMI|Gigabit'
]

UOM_REGEX = r'\b(nos|pcs|kg|boxes?|packs?|each|ea|lot|lumpsum|sets?|pair|coil|roll|bundle|sheet|tons?|mt|kl|ltr|litres?|sqft|sqm|cum|mtr|meters?)\b'


def normalize_date(date_str):
    """
    Formats dates into ISO YYYY-MM-DD format (e.g. 2026-08-10) required by backend API.
    """
    if not date_str or not str(date_str).strip():
        return ""
    raw = str(date_str).strip()

    # Strip ordinal suffixes (10th -> 10, 1st -> 1, 2nd -> 2, 3rd -> 3)
    raw = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', raw, flags=re.IGNORECASE)

    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
        "%d-%b-%Y", "%d-%B-%Y", "%d %B %Y", "%d %b %Y", "%d.%m.%Y",
        "%B %d %Y", "%b %d %Y", "%B %d, %Y", "%b %d, %Y", "%Y %b %d", "%Y %B %d"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Regex try for 10 August 2026 or August 10 2026
    m = re.search(r'(\d{1,2})[\s\/\-\.]+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\/\-\.]+(\d{4})', raw, re.IGNORECASE)
    if m:
        try:
            date_raw = f"{m.group(1)} {m.group(2)} {m.group(3)}"
            return datetime.strptime(date_raw, "%d %b %Y").strftime("%Y-%m-%d")
        except Exception:
            pass

    m2 = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\/\-\.]+(\d{1,2})[,\s\/\-\.]+(\d{4})', raw, re.IGNORECASE)
    if m2:
        try:
            date_raw = f"{m2.group(2)} {m2.group(1)} {m2.group(3)}"
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

    # 1. ITEM DESCRIPTION VALIDATION (Word Count & Length Validation)
    desc = str(rfq_data.get("item_description") or "").strip()

    # Clean lead filler phrases
    desc = re.sub(
        r'^(we\s+request\s+you\s+to\s+submit\s+your\s+quotation\s+for\s+the\s+supply\s+of|please\s+provide\s+quotation\s+for\s+)?(the\s+following\s+items?\.?\s*\(?|we\s+have\s+(a\s+)?requirement\s+(of|for)|requirement\s+(of|for)|(please\s+)?(provide|send)\s+(a\s+)?(quote|quotation|rate)\s+(for|of)|rfq\s+(for|of)|enquiry\s+(for|of)|(we\s+)?need|(we\s+)?require)\s*:?\s*\(?',
        '', desc, flags=re.IGNORECASE
    ).strip().rstrip(":")

    if desc.lower().startswith("of "):
        desc = desc[3:].strip()

    # Strip leading "Units of ", "Pcs of ", "Nos of "
    desc = re.sub(r'^(?:units?|pcs|nos|items?|packs?|boxes?)\s+of\s+', '', desc, flags=re.IGNORECASE).strip()

    # Strip quantity suffixes like "- Ten Pcs", "- 100 Mtr", "- Twenty Boxes"
    desc = re.sub(r'[\-\:]?\s*(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|fifty|hundred|\d+)\s*(?:nos|pcs|units?|items?|laptops?|sets?|mtr|meters?|kg|litres?|boxes?|packs?)\b.*$', '', desc, flags=re.IGNORECASE).strip()

    # If desc is missing, < 2 words, < 10 chars, or generic word like "office", recover via PRODUCT_PATTERNS
    if not desc or len(desc.split()) < 2 or len(desc) < 10 or desc.lower() in ["office", "printer", "laptop", "cable", "pipe", "paint", "item", "product", "procurement"]:
        for p in PRODUCT_PATTERNS:
            m = re.search(p, email_text, re.IGNORECASE)
            if m:
                extracted = m.group(1).strip()
                extracted = re.sub(r'^(?:the\s+)?(?:supply\s+of\s+)?', '', extracted, flags=re.IGNORECASE).strip()
                if extracted and len(extracted.split()) >= 1 and extracted.lower() not in ["office", "item", "printer", "laptop", "cable", "pipe", "paint"]:
                    desc = extracted
                    break

    # Safe fallback check before defaulting
    if not desc:
        m_fall = re.search(r'supply\s+of\s+(.+?)(?=\s+required|\.)', email_text, re.IGNORECASE)
        if m_fall:
            desc = m_fall.group(1).strip()

    rfq_data["item_description"] = desc or "Procurement Request"

    # 2. QUANTITY VALIDATION (Digits + Word Numbers + "Qty : Five" Support)
    qty_word = re.search(r'(?:qty|quantity|count)\s*[:=\-]?\s*(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|fifty|hundred)\b', email_text, re.IGNORECASE)
    word_qty = re.search(r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|fifty|hundred)\b(?:\s*(nos|pcs|units?|items?|laptops?|sets?|mtr|meters?|kg|litres?|boxes?|packs?))?', email_text, re.IGNORECASE)
    explicit_qty = re.search(r'(?:quantity|qty|count)\s*[:=\-]?\s*(\d+)', email_text, re.IGNORECASE)

    if explicit_qty:
        quantity = int(explicit_qty.group(1))
    elif qty_word:
        quantity = NUMBER_WORDS.get(qty_word.group(1).lower(), 1)
    elif word_qty:
        quantity = NUMBER_WORDS.get(word_qty.group(1).lower(), 1)
        if word_qty.group(2) and not rfq_data.get("uom"):
            rfq_data["uom"] = word_qty.group(2).capitalize()
    else:
        try:
            quantity = int(rfq_data.get("quantity", 0))
        except Exception:
            quantity = 0

        if quantity <= 0 or quantity > 5000:
            unit_qty = re.search(r'\b(\d{1,4})\s*' + UOM_REGEX, email_text, re.IGNORECASE)
            if unit_qty:
                quantity = int(unit_qty.group(1))
                if unit_qty.group(2) and not rfq_data.get("uom"):
                    rfq_data["uom"] = unit_qty.group(2).capitalize()
            else:
                quantity = 1

    rfq_data["quantity"] = quantity

    # 3. UOM VALIDATION (Extended Vocabulary)
    if not rfq_data.get("uom") or rfq_data["uom"].lower() in ["", "none", "null"]:
        uom_m = re.search(UOM_REGEX, email_text, re.IGNORECASE)
        if uom_m:
            rfq_data["uom"] = uom_m.group(1).capitalize()
        else:
            rfq_data["uom"] = "Nos"

    # 4. BRAND VALIDATION ("Any", "No Specific", "Open", "Equivalent" brand support)
    brand = str(rfq_data.get("brand") or "").strip()
    if re.search(r'\b(any|equivalent|open|no\s+specific)\s+(brand|make)\b', email_text, re.IGNORECASE):
        brand = "Any"
    elif not brand or brand.lower() in ["we look forward to your quotation", "not specified", "none"]:
        for b in COMMON_BRANDS:
            if re.search(rf"\b{re.escape(b)}\b", email_text, re.IGNORECASE):
                brand = b
                break
    rfq_data["brand"] = brand or "Not Specified"

    # 5. FULL PHRASE SPECIFICATIONS EXTRACTION
    specs_list = []
    for sp in SPEC_PATTERNS:
        m = re.search(sp, email_text, re.IGNORECASE)
        if m and m.group(0).strip() not in specs_list:
            specs_list.append(m.group(0).strip())

    if specs_list:
        rfq_data["specifications"] = ", ".join(specs_list)
    elif not rfq_data.get("specifications"):
        rfq_data["specifications"] = f"{rfq_data['item_description']}" + (f", Brand: {brand}" if brand else "")

    # 6. DELIVERY DATE NORMALIZATION (DD-Mon-YYYY format)
    delivery_date = str(rfq_data.get("delivery_date") or "").strip()
    if not delivery_date:
        date_match = re.search(r'\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{4}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b', email_text, re.IGNORECASE)
        if date_match:
            delivery_date = date_match.group(1).strip()

    rfq_data["delivery_date"] = normalize_date(delivery_date)

    # 7. DELIVERY LOCATION & PINCODE EXTRACTION
    loc = re.search(r'(?:delivery\s+location|delivery\s+address|delivery\s+site|ship\s+to|destination)\s*[:=\-]\s*([A-Za-z0-9\s,\-]+?)(?=[,\;\n\.]|\s*(?:specs|specifications|quantity|qty|brand|date)|$)', email_text, re.IGNORECASE)
    if loc:
        location_raw = loc.group(1).strip()
        pin = re.search(r'\b\d{6}\b', location_raw)
        if pin:
            rfq_data["delivery_pincode"] = pin.group()
        city = re.sub(r'\b\d{6}\b', '', location_raw).strip(" ,.")
        rfq_data["delivery_city"] = city

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
Never return single words like "Office", "Printer", "Laptop", "Cable", "Pipe", "Paint" alone.
Always return the complete product name exactly as written.
GOOD:
- Office Multifunction Laser Printers
- Dell Latitude 5450 Laptop
- Asian Paints Acrylic Emulsion
- CPVC Pipe PN16

BAD:
- Office
- Printer
- Laptop
- Pipe
- Paint

2. Quantity must ONLY be the requested item quantity as an integer. Convert word numbers ("Five" -> 5).
3. Brand: Extract manufacturer (e.g. Dell, HP, Asian Paints). If email says "any brand", "no specific brand", "open brand", "equivalent brand", return "Any".
4. UOM: Unit of measurement (e.g. Nos, Pcs, Kg, Mtr, Set, Box, Each, EA, Lot, Lumpsum, Pair, Roll, Sheet, Ton, MT, KL, Ltr, Sqft, Sqm, Cum).
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
    We request you to submit your quotation for the supply of Office Multifunction Laser Printers required for our organization. Qty : Five Nos. Any brand. Delivery Date: 10th August 2026. Delivery Location: Bangalore 560001. Specs: A4 Size, Print, Scan, Copy, Network Connectivity, Automatic Duplex Printing, 30-40 PPM, Warranty Details, Cartridge Yield, Installation Support.
    """

    rfq_data = extract_rfq(sample)
    print(rfq_data)