import requests
import json
import re


def extract_rfq(email_text):

    # Truncate very long email text to prevent CPU prompt evaluation delays
    if isinstance(email_text, str) and len(email_text) > 3000:
        email_text = email_text[:3000]

    prompt = f"""You are an AI procurement assistant. Analyze the email and extract RFQ information.

Return ONLY valid JSON matching this schema:
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

Extraction Rules:
- item_description: The specific product, material, or service requested (e.g., "PLUMBING Materials - CPVC Pipes & Valves", "Dell Laptops").
  CRITICAL: Do NOT include filler lead phrases like "We have requirement of", "RFQ for", "Please quote for", "Requirement for". Extract the complete actual product/material names and list item details.
- quantity: total item quantity as a number (default 1 if unspecified or multiple line items).
- uom: Unit of Measurement (e.g., "Nos", "Kg", "Mtr", "Set", "Pcs"). Use "Nos" for countable items if unspecified.
- brand: manufacturer/brand string (comma-separated if multiple).
- delivery_date: format as YYYY-MM-DD (empty string if not specified).
- delivery_city, delivery_state, delivery_pincode: extract separately. A 6-digit number is delivery_pincode.
- specifications: detailed specifications, sizes, model numbers, or line item details.
- Ignore greetings, signatures, disclaimers, and non-procurement text.

Email Content:
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
                    "num_predict": 250,
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

    # Extract JSON from AI response
    json_match = re.search(
        r'\{[\s\S]*?\}',
        result
    )

    if not json_match:
        raise Exception("No JSON found in AI response")

    rfq_data = json.loads(
        json_match.group()
    )

    # Ensure all keys exist
    required_keys = [
    "item_description",
    "specifications",
    "quantity",
    "uom",
    "brand",
    "delivery_date",
    "delivery_location"
    ]

    for key in required_keys:

        if key not in rfq_data:

            if key == "quantity":
                rfq_data[key] = 0
            else:
                rfq_data[key] = ""

    # Clean filler lead phrases from AI extracted item_description
    if isinstance(rfq_data.get("item_description"), str):
        desc = rfq_data["item_description"].strip()
        desc = re.sub(r'^(we\s+have\s+(a\s+)?requirement\s+(of|for)|requirement\s+(of|for)|(please\s+)?(provide|send)\s+(a\s+)?(quote|quotation|rate)\s+(for|of)|rfq\s+(for|of)|enquiry\s+(for|of)|(we\s+)?need|(we\s+)?require)\s*:\s*', '', desc, flags=re.IGNORECASE).strip()
        rfq_data["item_description"] = desc

    # Quantity validation
    try:
        rfq_data["quantity"] = int(
            rfq_data["quantity"]
        )
    except:
        rfq_data["quantity"] = 0

    # UOM Validation

    if "uom" not in rfq_data:
        rfq_data["uom"] = ""

    rfq_data["uom"] = str(
        rfq_data["uom"]
    ).strip()

    # Brand should always be string
    if isinstance(
        rfq_data["brand"],
        list
    ):
        rfq_data["brand"] = ", ".join(
            rfq_data["brand"]
        )

    return rfq_data


def fallback_extract_rfq(email_text):
    """
    Fallback extractor when Ollama AI server is offline or unavailable.
    Uses targeted regex patterns to extract quantity, brand, item description, and specs accurately.
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

    # 1. ACCURATE QUANTITY EXTRACTION
    # First check explicit "Quantity: 25" or "Qty: 25"
    explicit_qty = re.search(r'(?:quantity|qty|count)\s*[:=\-]?\s*(\d+)', email_text, re.IGNORECASE)
    if explicit_qty:
        try:
            quantity = int(explicit_qty.group(1))
        except Exception:
            quantity = 1
    else:
        # Check number followed by unit keyword e.g. "25 Nos", "25 Pcs", "25 Laptops"
        unit_qty = re.search(r'\b(\d{1,3})\s*(nos|pcs|units|items|laptops|sets|mtr|kg|litres|qty)\b', email_text, re.IGNORECASE)
        if unit_qty:
            try:
                quantity = int(unit_qty.group(1))
                if unit_qty.group(2):
                    uom = unit_qty.group(2).capitalize()
            except Exception:
                quantity = 1
        else:
            quantity = 1

    # 2. BRAND EXTRACTION
    brand_match = re.search(r'(?:brand|make|manufacturer)\s*[:=\-]?\s*([A-Za-z0-9\s]+(?:\([A-Za-z0-9\s]+\))?)', email_text, re.IGNORECASE)
    if brand_match:
        brand = brand_match.group(1).strip()

    # 3. ACCURATE ITEM NAME EXTRACTION
    # Check for explicit "Item Name: Dell Latitude 5450 Laptop"
    item_name_match = re.search(r'(?:item\s*name|product\s*name|item|product)\s*[:=\-]?\s*([A-Za-z0-9\s\-\/\.\(\)]+?)(?=[,\;\n]|\s*(?:quantity|qty|brand|uom)|$)', email_text, re.IGNORECASE)
    if item_name_match:
        extracted_name = item_name_match.group(1).strip()
        if len(extracted_name) > 2 and not extracted_name.lower().startswith("the following"):
            item_description = extracted_name

    # Extract 6-digit Indian pincode if present
    pincode_match = re.search(r'\b[1-9]\d{5}\b', email_text)
    if pincode_match:
        delivery_pincode = pincode_match.group(0)

    # Filter out common greeting/signature lines if item_description is not found yet
    if not item_description:
        ignore_words = ["hi", "hello", "dear", "thanks", "regards", "subject:", "team", "from:", "sent:"]
        content_lines = []
        for line in lines:
            if not any(line.lower().startswith(w) for w in ignore_words):
                content_lines.append(line)

        if content_lines:
            raw_desc = content_lines[0]
            # Strip lead phrases like "the following item", "We have requirement of", etc.
            cleaned_desc = re.sub(
                r'^(please\s+provide\s+quotation\s+for\s+)?(the\s+following\s+items?\.?\s*\(?|we\s+have\s+(a\s+)?requirement\s+(of|for)|requirement\s+(of|for)|(please\s+)?(provide|send)\s+(a\s+)?(quote|quotation|rate)\s+(for|of)|rfq\s+(for|of)|enquiry\s+(for|of)|(we\s+)?need|(we\s+)?require)\s*:?\s*\(?',
                '',
                raw_desc,
                flags=re.IGNORECASE
            ).strip().rstrip(":")

            item_description = (cleaned_desc or raw_desc)[:180]
            specifications = ", ".join(content_lines[1:4])[:250] if len(content_lines) > 1 else item_description
        else:
            item_description = "Procurement Request"

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
        "delivery_pincode": delivery_pincode,
        "delivery_location": ""
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