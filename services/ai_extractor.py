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


def extract_rfq(email_text):
    if not isinstance(email_text, str):
        email_text = str(email_text or "")

    # Issue 1: Allow up to 25,000 characters so long PDF/DOCX text is not truncated
    if len(email_text) > 25000:
        email_text = email_text[:25000]

    # Issue 2: High-precision prompt with explicit GOOD vs BAD examples
    prompt = f"""You are an expert Procurement RFQ Extraction AI.

Read the email carefully.
Return ONLY JSON.
Never explain anything.
Never summarize.
Extract exactly what appears in the email.

Rules:
1. Item Description must ONLY contain the actual product/material name.
GOOD:
- Dell Latitude 5450 Laptop
- CPVC Pipes
- Acrylic Paint

BAD:
- We have requirement of...
- Please quote for...
- The following item...
- Requirement for...

2. Quantity must ONLY be the requested item quantity.
If email says "Dell Latitude 5450 Laptop, Quantity: 25 Nos", return 25.
Never return model numbers like 5450 as quantity!

3. Brand: Extract only the manufacturer (e.g. Dell, HP, Asian Paints, Finolex).

4. UOM: Unit of measurement (e.g. Nos, Pcs, Kg, Mtr, Set, Box).

5. Specifications: Include model numbers, specs (processor, RAM, size, thickness, etc.).

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
            timeout=20
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

    # Issue 3: Clean JSON loading without flaky regex
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
            r'^(please\s+provide\s+quotation\s+for\s+)?(the\s+following\s+items?\.?\s*\(?|we\s+have\s+(a\s+)?requirement\s+(of|for)|requirement\s+(of|for)|(please\s+)?(provide|send)\s+(a\s+)?(quote|quotation|rate)\s+(for|of)|rfq\s+(for|of)|enquiry\s+(for|of)|(we\s+)?need|(we\s+)?require)\s*:?\s*\(?',
            '', desc, flags=re.IGNORECASE
        ).strip().rstrip(":")
        rfq_data["item_description"] = desc

    # Quantity validation (prevent model number overflow)
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
                rfq_data["quantity"] = 1

    # Brand validation
    if isinstance(rfq_data.get("brand"), list):
        rfq_data["brand"] = ", ".join(rfq_data["brand"])
    rfq_data["brand"] = str(rfq_data.get("brand") or "").strip()

    # Brand fallback detection if brand missing
    if not rfq_data["brand"]:
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
    specifications = ""

    # 1. ACCURATE QUANTITY & UOM EXTRACTION
    explicit_qty = re.search(r'(?:quantity|qty|count)\s*[:=\-]?\s*(\d+)', email_text, re.IGNORECASE)
    if explicit_qty:
        try:
            quantity = int(explicit_qty.group(1))
        except Exception:
            quantity = 1
    else:
        # Check "Need 50 Dell Latitude..." or "25 Nos" or "100 Litres"
        need_qty = re.search(r'\b(?:need|required?|looking\s+for|require)\s+(\d{1,4})\b', email_text, re.IGNORECASE)
        if need_qty:
            quantity = int(need_qty.group(1))
        else:
            unit_qty = re.search(r'\b(\d{1,4})\s*(nos|pcs|units?|items?|laptops?|sets?|mtr|meters?|kg|litres?|qty|boxes?|packs?)\b', email_text, re.IGNORECASE)
            if unit_qty:
                try:
                    quantity = int(unit_qty.group(1))
                    if unit_qty.group(2):
                        uom = unit_qty.group(2).capitalize()
                except Exception:
                    quantity = 1
            else:
                quantity = 1

    # Extract UOM if explicitly mentioned in text (e.g. "100 Litres", "50 Mtr")
    uom_match = re.search(r'\b\d+\s*(nos|pcs|units?|items?|laptops?|sets?|mtr|meters?|kg|litres?|boxes?|packs?)\b', email_text, re.IGNORECASE)
    if uom_match and uom_match.group(1):
        uom = uom_match.group(1).capitalize()

    # 2. BRAND EXTRACTION
    brand_match = re.search(r'(?:brand|make|manufacturer)\s*[:=\-]?\s*([A-Za-z0-9\s]+(?:\([A-Za-z0-9\s]+\))?)', email_text, re.IGNORECASE)
    if brand_match:
        brand = brand_match.group(1).strip()

    if not brand:
        for b in COMMON_BRANDS:
            if re.search(rf"\b{re.escape(b)}\b", email_text, re.IGNORECASE):
                brand = b
                break

    # 3. ACCURATE ITEM NAME EXTRACTION
    item_name_match = re.search(r'(?:item\s*name|product\s*name|item|product)\s*[:=\-]?\s*([A-Za-z0-9\s\-\/\.\(\)]+?)(?=[,\;\n]|\s*(?:quantity|qty|brand|uom)|$)', email_text, re.IGNORECASE)
    if item_name_match:
        extracted_name = item_name_match.group(1).strip()
        if len(extracted_name) > 2 and not extracted_name.lower().startswith("the following"):
            item_description = extracted_name

    # "Need 50 Dell Laptops" or "Looking for 200 Units of Havells Wires"
    if not item_description:
        need_match = re.search(r'(?:need|required?|looking\s+for|require)\s+(?:\d+\s+)?(?:nos|pcs|units|items)?\s*(?:of\s+)?([A-Za-z0-9\s\-\/\.\(\)]+?)(?=[,\;\n\.]|\s*(?:delivery|pincode|qty|brand|location)|$)', email_text, re.IGNORECASE)
        if need_match and need_match.group(1):
            cleaned_need = need_match.group(1).strip()
            if cleaned_need and len(cleaned_need) > 2:
                item_description = cleaned_need

    # Lead phrase cleanup for generic sentences
    if not item_description or item_description.lower().startswith("kindly") or item_description.lower().startswith("please"):
        ignore_words = ["hi", "hello", "dear", "thanks", "regards", "subject:", "team", "from:", "sent:"]
        content_lines = []
        for line in lines:
            if not any(line.lower().startswith(w) for w in ignore_words):
                content_lines.append(line)

        if content_lines:
            raw_desc = content_lines[0]
            cleaned_desc = re.sub(
                r'^(kindly\s+(send|share|provide)\s+(rate|price|quote|quotation)\s+(for|of)|please\s+provide\s+quotation\s+for|the\s+following\s+items?\.?\s*\(?|we\s+have\s+(a\s+)?requirement\s+(of|for)|requirement\s+(of|for)|(please\s+)?(provide|send)\s+(a\s+)?(quote|quotation|rate)\s+(for|of)|rfq\s+(for|of)|enquiry\s+(for|of)|(we\s+)?need|(we\s+)?require)\s*:?\s*\(?',
                '',
                raw_desc,
                flags=re.IGNORECASE
            ).strip().rstrip(":")

            item_description = (cleaned_desc or raw_desc)[:180]
            specifications = ", ".join(content_lines[1:4])[:250] if len(content_lines) > 1 else item_description
        else:
            item_description = "Procurement Request"

    # Strip lead "of " if present
    if item_description.lower().startswith("of "):
        item_description = item_description[3:].strip()

    if not specifications:
        specifications = f"{item_description}" + (f", Brand: {brand}" if brand else "")

    print(f"[EXTRACTED ITEM]: '{item_description}' | Qty: {quantity} {uom} | Brand: '{brand}'")

    return {
        "item_description": item_description,
        "specifications": specifications or item_description,
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
    Need 50 Dell Latitude 5450 laptops.
    
    Specifications:
    Intel i7 Processor
    16GB RAM
    512GB SSD
    
    Delivery Date: 10 July 2026
    Delivery Location: Bangalore
    """

    rfq_data = extract_rfq(sample)
    print(rfq_data)