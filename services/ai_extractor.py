import requests
import json
import re

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

SPEC_KEYWORDS = [
    "Print", "Scan", "Copy", "Network", "Duplex", "PPM", "Warranty",
    "Cartridge", "Installation", "A4", "A3", "RAM", "SSD", "HDD",
    "Intel", "Processor", "i5", "i7", "CPVC", "PVC", "PN10", "PN16",
    "Automatic", "Bluetooth", "Wi-Fi", "HDMI", "USB", "Gigabit"
]


def extract_rfq(email_text):
    if not isinstance(email_text, str):
        email_text = str(email_text or "")

    # Allow up to 25,000 characters so long PDF/DOCX text is not truncated
    if len(email_text) > 25000:
        email_text = email_text[:25000]

    # Ultra-high precision prompt with explicit natural language rules
    prompt = f"""You are an expert Procurement RFQ Extraction AI.

Read the email carefully.
Return ONLY JSON.
Never explain anything.
Never summarize.
Extract exactly what appears in the email.

Rules:
1. Item Description must ONLY contain the actual product/material name.
GOOD:
- Office Multifunction Laser Printers
- Dell Latitude 5450 Laptop
- CPVC Pipes

BAD:
- We request you to submit your quotation...
- We have requirement of...
- Required for our organization...

2. Quantity must ONLY be the requested item quantity as an integer.
Convert word numbers like "Five" -> 5, "Ten" -> 10.

3. Brand: Extract manufacturer (e.g. Dell, HP, Asian Paints). If email says "any brand", return "Any".

4. UOM: Unit of measurement (e.g. Nos, Pcs, Kg, Mtr, Set, Box).

5. Specifications: List key features, specs, model numbers, or requirements.

6. Ignore greetings, signatures, footers, and email disclaimers.

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
    except Exception as e:
        print(f"\n[WARNING] Ollama server unavailable ({e}). Switching to rule-based fallback extraction...")
        return fallback_extract_rfq(email_text)

    if response.status_code != 200:
        print(f"\n[WARNING] Ollama HTTP {response.status_code}. Switching to rule-based fallback extraction...")
        return fallback_extract_rfq(email_text)

    response_json = response.json()

    if "response" not in response_json:
        error_detail = response_json.get("error", "Unknown error from Ollama")
        raise Exception(f"Invalid response from Ollama: {error_detail}")

    result = response_json["response"]

    try:
        rfq_data = json.loads(result.strip())
    except Exception:
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            try:
                rfq_data = json.loads(json_match.group())
            except Exception:
                raise Exception("Invalid JSON returned by Ollama")
        else:
            raise Exception("Invalid JSON returned by Ollama")

    # Ensure required fields exist
    required_keys = [
        "item_description", "specifications", "quantity",
        "uom", "brand", "delivery_date", "delivery_city",
        "delivery_state", "delivery_pincode"
    ]
    for key in required_keys:
        if key not in rfq_data:
            rfq_data[key] = 0 if key == "quantity" else ""

    # Clean filler lead phrases from AI extracted item_description
    if isinstance(rfq_data.get("item_description"), str):
        desc = rfq_data["item_description"].strip()
        desc = re.sub(
            r'^(we\s+request\s+you\s+to\s+submit\s+your\s+quotation\s+for\s+the\s+supply\s+of|please\s+provide\s+quotation\s+for\s+)?(the\s+following\s+items?\.?\s*\(?|we\s+have\s+(a\s+)?requirement\s+(of|for)|requirement\s+(of|for)|(please\s+)?(provide|send)\s+(a\s+)?(quote|quotation|rate)\s+(for|of)|rfq\s+(for|of)|enquiry\s+(for|of)|(we\s+)?need|(we\s+)?require)\s*:?\s*\(?',
            '', desc, flags=re.IGNORECASE
        ).strip().rstrip(":")
        rfq_data["item_description"] = desc

    # Quantity validation
    try:
        rfq_data["quantity"] = int(rfq_data["quantity"])
    except Exception:
        rfq_data["quantity"] = 0

    if rfq_data["quantity"] <= 0:
        # Fallback to scanning for explicit quantity in text
        explicit_qty = re.search(r'(?:quantity|qty|count)\s*[:=\-]?\s*(\d+)', email_text, re.IGNORECASE)
        if explicit_qty:
            rfq_data["quantity"] = int(explicit_qty.group(1))
        else:
            unit_qty = re.search(r'\b(\d{1,4})\s*(nos|pcs|units?|items?|laptops?|sets?|mtr|meters?|kg|litres?|qty|boxes?|packs?)\b', email_text, re.IGNORECASE)
            if unit_qty:
                rfq_data["quantity"] = int(unit_qty.group(1))
                if unit_qty.group(2) and not rfq_data.get("uom"):
                    rfq_data["uom"] = unit_qty.group(2).capitalize()
            else:
                word_qty = re.search(r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|fifty|hundred)\b', email_text, re.IGNORECASE)
                if word_qty:
                    rfq_data["quantity"] = NUMBER_WORDS.get(word_qty.group(1).lower(), 1)
                else:
                    rfq_data["quantity"] = 1

    # Brand validation
    if isinstance(rfq_data.get("brand"), list):
        rfq_data["brand"] = ", ".join(rfq_data["brand"])
    rfq_data["brand"] = str(rfq_data.get("brand") or "").strip()

    if not rfq_data["brand"]:
        if re.search(r'\b(any\s+brand|no\s+specific\s+brand|open\s+to\s+any\s+brand)\b', email_text, re.IGNORECASE):
            rfq_data["brand"] = "Any"
        else:
            for b in COMMON_BRANDS:
                if re.search(rf"\b{re.escape(b)}\b", email_text, re.IGNORECASE):
                    rfq_data["brand"] = b
                    break

    return rfq_data


def fallback_extract_rfq(email_text):
    """
    Ultra-high precision rule-based fallback extractor when Ollama is offline.
    """
    if not email_text:
        email_text = ""

    lines = [line.strip() for line in email_text.splitlines() if line.strip()]

    item_description = ""
    quantity = 0
    uom = "Nos"
    brand = ""
    delivery_date = ""
    delivery_city = ""
    delivery_state = ""
    delivery_pincode = ""

    # 1. NATURAL ENGLISH PRODUCT NAME PATTERNS
    # Pattern A: "supply of Office Multifunction Laser Printers required for..."
    product_match = re.search(
        r'(?:supply\s+of|procurement\s+of|purchase\s+of|quotation\s+for\s+(?:the\s+)?supply\s+of)\s+(.+?)\s+(?:required\s+for|needed\s+for|for\s+our|for\s+project)',
        email_text, re.IGNORECASE
    )
    if product_match:
        item_description = product_match.group(1).strip()

    # Pattern B: Explicit "Item Name: Dell Latitude 5450 Laptop"
    if not item_description:
        item_name_match = re.search(r'(?:item\s*name|product\s*name|item|product)\s*[:=\-]?\s*([A-Za-z0-9\s\-\/\.\(\)]+?)(?=[,\;\n]|\s*(?:quantity|qty|brand|uom)|$)', email_text, re.IGNORECASE)
        if item_name_match:
            extracted_name = item_name_match.group(1).strip()
            if len(extracted_name) > 2 and not extracted_name.lower().startswith("the following"):
                item_description = extracted_name

    # Pattern C: "Need 50 Dell Laptops" or "Looking for 200 Units of Havells Wires"
    if not item_description:
        need_match = re.search(r'(?:need|required?|looking\s+for|require)\s+(?:\d+\s+)?(?:nos|pcs|units|items)?\s*(?:of\s+)?([A-Za-z0-9\s\-\/\.\(\)]+?)(?=[,\;\n\.]|\s*(?:delivery|pincode|qty|brand|location)|$)', email_text, re.IGNORECASE)
        if need_match and need_match.group(1):
            cleaned_need = need_match.group(1).strip()
            if cleaned_need and len(cleaned_need) > 2:
                item_description = cleaned_need

    # Pattern D: Lead phrase cleanup for general text
    if not item_description or item_description.lower().startswith("kindly") or item_description.lower().startswith("please"):
        ignore_words = ["hi", "hello", "dear", "thanks", "regards", "subject:", "team", "from:", "sent:"]
        content_lines = []
        for line in lines:
            if not any(line.lower().startswith(w) for w in ignore_words):
                content_lines.append(line)

        if content_lines:
            raw_desc = content_lines[0]
            cleaned_desc = re.sub(
                r'^(we\s+request\s+you\s+to\s+submit\s+your\s+quotation\s+for\s+the\s+supply\s+of|kindly\s+(send|share|provide)\s+(rate|price|quote|quotation)\s+(for|of)|please\s+provide\s+quotation\s+for|the\s+following\s+items?\.?\s*\(?|we\s+have\s+(a\s+)?requirement\s+(of|for)|requirement\s+(of|for)|(please\s+)?(provide|send)\s+(a\s+)?(quote|quotation|rate)\s+(for|of)|rfq\s+(for|of)|enquiry\s+(for|of)|(we\s+)?need|(we\s+)?require)\s*:?\s*\(?',
                '', raw_desc, flags=re.IGNORECASE
            ).strip().rstrip(":")
            item_description = (cleaned_desc or raw_desc)[:180]
        else:
            item_description = "Procurement Request"

    if item_description.lower().startswith("of "):
        item_description = item_description[3:].strip()

    # 2. ACCURATE QUANTITY & UOM EXTRACTION (DIGITS + WORDS)
    explicit_qty = re.search(r'(?:quantity|qty|count)\s*[:=\-]?\s*(\d+)', email_text, re.IGNORECASE)
    if explicit_qty:
        try:
            quantity = int(explicit_qty.group(1))
        except Exception:
            quantity = 1
    else:
        digit_qty = re.search(r'\b(\d{1,4})\s*(nos|pcs|units?|items?|laptops?|sets?|mtr|meters?|kg|litres?|qty|boxes?|packs?)\b', email_text, re.IGNORECASE)
        if digit_qty:
            quantity = int(digit_qty.group(1))
            if digit_qty.group(2):
                uom = digit_qty.group(2).capitalize()
        else:
            word_qty = re.search(r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|fifty|hundred)\b(?:\s*(nos|pcs|units?|items?|laptops?|sets?|mtr|kg|litres?))?', email_text, re.IGNORECASE)
            if word_qty:
                w_str = word_qty.group(1).lower()
                quantity = NUMBER_WORDS.get(w_str, 1)
                if word_qty.group(2):
                    uom = word_qty.group(2).capitalize()
            else:
                quantity = 1

    # Extract UOM if explicitly mentioned
    uom_match = re.search(r'\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*(nos|pcs|units?|items?|laptops?|sets?|mtr|meters?|kg|litres?|boxes?|packs?)\b', email_text, re.IGNORECASE)
    if uom_match and uom_match.group(1):
        uom = uom_match.group(1).capitalize()

    # 3. BRAND EXTRACTION ("Any" brand support)
    if re.search(r'\b(any\s+brand|no\s+specific\s+brand|open\s+to\s+any\s+brand)\b', email_text, re.IGNORECASE):
        brand = "Any"
    else:
        brand_match = re.search(r'(?:brand|make|manufacturer)\s*[:=\-]?\s*([A-Za-z0-9\s]+(?:\([A-Za-z0-9\s]+\))?)', email_text, re.IGNORECASE)
        if brand_match:
            brand = brand_match.group(1).strip()
        else:
            for b in COMMON_BRANDS:
                if re.search(rf"\b{re.escape(b)}\b", email_text, re.IGNORECASE):
                    brand = b
                    break

    # 4. KEYWORD-BASED SPECIFICATIONS EXTRACTION
    matched_specs = []
    for kw in SPEC_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", email_text, re.IGNORECASE):
            matched_specs.append(kw)

    if matched_specs:
        specifications = ", ".join(matched_specs)
    else:
        specifications = f"{item_description}" + (f", Brand: {brand}" if brand else "")

    # 5. DELIVERY DATE EXTRACTION (e.g. 10-08-2026, 10/08/2026, 2026-08-10, 10 August 2026)
    date_match = re.search(r'\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b', email_text, re.IGNORECASE)
    if date_match:
        delivery_date = date_match.group(1).strip()

    # Extract 6-digit Indian pincode if present
    pincode_match = re.search(r'\b[1-9]\d{5}\b', email_text)
    if pincode_match:
        delivery_pincode = pincode_match.group(0)

    print(f"[EXTRACTED ITEM]: '{item_description}' | Qty: {quantity} {uom} | Brand: '{brand}' | Date: '{delivery_date}'")

    return {
        "item_description": item_description,
        "specifications": specifications,
        "quantity": quantity,
        "uom": uom,
        "brand": brand,
        "delivery_date": delivery_date,
        "delivery_city": delivery_city,
        "delivery_state": delivery_state,
        "delivery_pincode": delivery_pincode
    }


# TEST ONLY
if __name__ == "__main__":
    sample = """
    We request you to submit your quotation for the supply of Office Multifunction Laser Printers required for our organization. Five Nos. Any brand. Specs: A4 Size, Print, Scan, Copy, Network Connectivity, Automatic Duplex Printing, 30-40 PPM, Warranty Details, Cartridge Yield, Installation Support.
    """

    rfq_data = fallback_extract_rfq(sample)
    print(rfq_data)