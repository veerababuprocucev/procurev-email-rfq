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
- item_description: requested product or service.
- quantity: number (default 0 if not specified).
- uom: Unit of Measurement (e.g., "Nos", "Kg", "Mtr", "Litres"). Use "Nos" for countable items if unspecified.
- brand: manufacturer/brand string (comma-separated if multiple).
- delivery_date: format as YYYY-MM-DD (empty string if not specified).
- delivery_city, delivery_state, delivery_pincode: extract separately. A 6-digit number is delivery_pincode.
- specifications: comma-separated string of specs/remarks.
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
    Uses smart regex patterns to extract quantity, item description, and specs.
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

    # Extract quantity
    qty_match = re.search(r'\b(\d+)\s*(nos|pcs|units|items|laptops|qty)?\b', email_text, re.IGNORECASE)
    if qty_match:
        try:
            quantity = int(qty_match.group(1))
            if qty_match.group(2):
                uom = qty_match.group(2).capitalize()
        except Exception:
            quantity = 1
    else:
        quantity = 1

    # Extract 6-digit Indian pincode if present
    pincode_match = re.search(r'\b[1-9]\d{5}\b', email_text)
    if pincode_match:
        delivery_pincode = pincode_match.group(0)

    # Extract item description from non-greeting content lines
    ignore_words = ["hi", "hello", "dear", "thanks", "regards", "subject:", "team", "from:"]
    desc_lines = []
    for line in lines:
        if not any(line.lower().startswith(w) for w in ignore_words):
            desc_lines.append(line)

    if desc_lines:
        item_description = desc_lines[0][:150]
        if len(desc_lines) > 1:
            specifications = ", ".join(desc_lines[1:4])[:200]
    else:
        item_description = "Procurement Request"

    print(f"[FALLBACK PARSER] Extracted Item: '{item_description}', Qty: {quantity}")

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