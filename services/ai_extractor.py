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
            timeout=300
        )
    except requests.exceptions.ConnectionError as e:
        raise Exception(
            "Could not connect to Ollama server at http://localhost:11434. "
            "Please ensure Ollama is running (`ollama serve`)."
        ) from e
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ollama request failed: {e}") from e

    if response.status_code != 200:
        raise Exception(f"Ollama HTTP {response.status_code}: {response.text}")

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