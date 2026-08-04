"""
Enterprise RFQ Extraction Engine - Production Grade Pipeline
Architecture: Few-Shot LLM (Ollama) -> Validation -> Priority Regex -> Domain Dictionary -> ISO Normalization -> Pincode Lookup
Author: Senior AI Engineer
"""

import requests
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Domain Product Dictionaries, Pincode Maps & Brand Registries
# ---------------------------------------------------------------------------

COMMON_BRANDS: List[str] = [
    "Dell", "HP", "Lenovo", "Acer", "Apple", "Asus", "Samsung", "LG",
    "Asian Paints", "Berger", "Dulux", "Nerolac", "Havells", "Schneider",
    "Legrand", "Finolex", "Supreme", "Ashirvad", "Astral", "Polycab",
    "Tata", "JSW", "Bosch", "Siemens", "Philips", "Godrej", "Crompton",
    "Anchor", "L&T", "Honeywell", "3M", "Kirloskar", "ABB"
]

NUMBER_WORDS: Dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
    "fifty": 50, "hundred": 100
}

PINCODE_PREFIX_MAP: Dict[str, tuple] = {
    "560": ("Bangalore", "Karnataka"), "561": ("Bangalore Rural", "Karnataka"),
    "562": ("Bangalore Rural", "Karnataka"), "570": ("Mysore", "Karnataka"),
    "580": ("Hubli", "Karnataka"), "575": ("Mangalore", "Karnataka"),
    "522": ("Guntur", "Andhra Pradesh"), "530": ("Visakhapatnam", "Andhra Pradesh"),
    "520": ("Vijayawada", "Andhra Pradesh"), "517": ("Tirupati", "Andhra Pradesh"),
    "500": ("Hyderabad", "Telangana"), "501": ("Hyderabad", "Telangana"),
    "600": ("Chennai", "Tamil Nadu"), "641": ("Coimbatore", "Tamil Nadu"),
    "625": ("Madurai", "Tamil Nadu"), "620": ("Tiruchirappalli", "Tamil Nadu"),
    "400": ("Mumbai", "Maharashtra"), "411": ("Pune", "Maharashtra"),
    "440": ("Nagpur", "Maharashtra"), "422": ("Nashik", "Maharashtra"),
    "110": ("New Delhi", "Delhi"), "122": ("Gurugram", "Haryana"),
    "201": ("Noida", "Uttar Pradesh"), "226": ("Lucknow", "Uttar Pradesh"),
    "208": ("Kanpur", "Uttar Pradesh"), "380": ("Ahmedabad", "Gujarat"),
    "390": ("Vadodara", "Gujarat"), "395": ("Surat", "Gujarat"),
    "302": ("Jaipur", "Rajasthan"), "700": ("Kolkata", "West Bengal"),
    "751": ("Bhubaneswar", "Odisha"), "781": ("Guwahati", "Assam"),
    "800": ("Patna", "Bihar"), "834": ("Ranchi", "Jharkhand"),
    "492": ("Raipur", "Chhattisgarh"), "462": ("Bhopal", "Madhya Pradesh"),
    "452": ("Indore", "Madhya Pradesh"), "682": ("Kochi", "Kerala"),
    "695": ("Trivandrum", "Kerala"), "248": ("Dehradun", "Uttarakhand"),
    "160": ("Chandigarh", "Punjab/Haryana")
}

# Domain Category Product Dictionary for Industrial & Enterprise Procurement
INDUSTRIAL_PRODUCT_DICTIONARY: List[str] = [
    "IP CCTV Surveillance System", "CCTV Surveillance System", "Surveillance System",
    "IP Cameras", "NVR", "Multifunction Laser Printers", "Laser Printers", "Desktop Computers",
    "Latitude Laptops", "Laptops", "CPVC Pipes", "PVC Pipes", "GI Pipes",
    "HDPE Pipes", "SS 304 Pipes", "Copper Cables", "Armoured Cables",
    "Acrylic Emulsion Paint", "Exterior Emulsion Paint", "MCCB Circuit Breaker",
    "Automatic Voltage Stabilizer", "Air Compressor", "Hammer Drill Machine",
    "Solvent Cement", "Centrifugal Water Pump"
]

PRODUCT_PATTERNS: List[str] = [
    # Priority 1: Email Subject / Header line (cleanest product description)
    r'\b(?:subject|re|rfq|enquiry|tender|quotation)\s*[:=\-]\s*([A-Za-z0-9\s\-\/\(\)]+?)(?=[;\n\.]|\s*(?:quantity|qty|brand|delivery)|$)',

    # Priority 2: Explicit Tagged Fields (Item Name / Product Name)
    r'\b(?:item\s*name|product\s*name|item|product)\s*[:=\-]?\s*([A-Za-z0-9\s\-\/\.\(\)]+?)(?=[;\n\.]|\s*(?:quantity|qty|brand|uom)|$)',

    # Priority 3: Supply, installation and commissioning of / Supply of / Procurement of
    r'\b(?:supply|procurement|purchase|installation|commissioning)(?:[,\s]+(?:installation|commissioning))*?\s+of\s+(?:an?\s+)?([A-Za-z0-9\s\-\/\(\)]+?)(?=\s+(?:required|needed|for\s+our|for\s+facility|for\s+project)|[;\n\.]|\s*(?:delivery|specs|quantity|qty|brand)|$)',

    # Priority 4: Quotation for / Please quote for
    r'\b(?:quotation\s+for|quote\s+for|please\s+quote\s+for)\s+(?:the\s+)?(?:supply|procurement|purchase|installation|commissioning)?(?:[,\s]+(?:installation|commissioning))*?\s*of\s+(?:an?\s+)?([A-Za-z0-9\s\-\/\(\)]+?)(?=\s+(?:required|needed|for\s+our|for\s+facility|for\s+project)|[;\n\.]|\s*(?:delivery|specs|quantity|qty|brand)|$)',

    # Priority 5: Requirement of/for
    r'\b(?:requirement\s+(?:of|for))\s+(?:the\s+)?([A-Za-z0-9\s\-\/\(\)]+?)(?=\s+(?:required|needed|for\s+our|for\s+facility|for\s+project)|[;\n\.]|\s*(?:delivery|specs|quantity|qty|brand)|$)',

    # Priority 6: Looking for / Need / Require
    r'\b(?:looking\s+for|need|require)\s+(?:\d+\s+)?(?:nos|pcs|units|items)?\s*(?:of\s+)?([A-Za-z0-9\s\-\/\(\)]+?)(?=\s+(?:for|delivery|pincode|qty|brand|location)|[;\n\.]|$)'
]

SPEC_PATTERNS: List[str] = [
    r'A[345]\s+Size[^\.\,\n]*',
    r'(?:Print|Scan|Copy)(?:[,\s/]+(?:and\s+)?(?:Print|Scan|Copy))+',
    r'Automatic\s+Duplex\s+(?:Printing)?[^\.\,\n]*',
    r'Network\s+Connectivity[^\.\,\n]*',
    r'\d+\s*(?:–|-|\s*to\s*)\s*\d+\s*PPM|\b\d+\s*PPM',
    r'\d+\s+IP\s+Cameras[^\.\,\n]*',
    r'IP\s+Cameras[^\.\,\n]*',
    r'NVR[^\.\,\n]*',
    r'Hard\s+Disk\s+Storage[^\.\,\n]*',
    r'Network\s+Accessories[^\.\,\n]*',
    r'\d+\s*GB\s+(?:RAM|SSD|HDD)[^\.\,\n]*',
    r'Intel\s+i[3579]\s+(?:Processor)?[^\.\,\n]*',
    r'CPVC|PVC|PN10|PN16',
    r'Wi-Fi|Bluetooth|HDMI|Gigabit'
]

UOM_REGEX: str = r'\b(nos|pcs|kg|boxes?|packs?|bags?|each|ea|lot|lumpsum|sets?|pair|coil|roll|bundle|sheet|tons?|mt|kl|ltr|litres?|sqft|sqm|cum|mtr|meters?|laptops?|printers?|units?|items?|cameras?)\b'


# ---------------------------------------------------------------------------
# Helper Functions: Validation, Normalization, Clean-up, Pincode Lookup
# ---------------------------------------------------------------------------

def is_generic_description(desc_str: Optional[str]) -> bool:
    """
    Validates if an item description is a generic filler word, prompt artifact, or table header row.
    Returns True if invalid/generic, False if valid product description.
    """
    if not desc_str or not str(desc_str).strip():
        return True

    clean = re.sub(r'\s+', ' ', str(desc_str).strip().lower())

    # Exact match against single generic words, prompt artifacts, or table headers
    generic_exact = [
        "procurement request", "procurement", "request", "rfq", "enquiry", "quotation", "quote",
        "description specification / make", "description specification make", "description specification",
        "item description", "product description", "specification / make", "specification make",
        "description / specification", "item name", "product name", "item", "product", "particulars",
        "sl no", "s.no", "description", "specification", "make", "material", "general item",
        "office", "printer", "laptop", "pipe", "cable", "paint",
        "catalogue", "product catalogue", "technical datasheet", "datasheet", "commercial terms",
        "installation support", "warranty details", "cartridge yield", "warranty", "terms"
    ]
    if clean in generic_exact:
        return True

    # Prefix/suffix match ONLY for explicit multi-word table headers & filler phrases
    generic_phrases = [
        "procurement request", "item description", "product description",
        "description specification", "specification make", "description / specification",
        "product catalogue", "technical datasheet", "commercial terms", "installation support",
        "warranty details", "cartridge yield"
    ]
    for g in generic_phrases:
        if clean == g or clean.startswith(g + " ") or clean.endswith(" " + g):
            return True

    return False


def normalize_date(date_str: Optional[str]) -> str:
    """
    Normalizes any human date format into ISO YYYY-MM-DD format (e.g. 2026-08-10) required by backend API.
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


def lookup_pincode_location(pincode_str: Optional[str]) -> tuple:
    """
    Looks up City and State from 6-digit Indian Pincode prefix.
    Returns (City, State) tuple.
    """
    if not pincode_str or len(str(pincode_str).strip()) != 6:
        return "", ""
    pin = str(pincode_str).strip()
    prefix = pin[:3]
    return PINCODE_PREFIX_MAP.get(prefix, ("", ""))


# ---------------------------------------------------------------------------
# Core Production Validation & Normalization Pipeline
# ---------------------------------------------------------------------------

def validate_and_normalize_rfq(rfq_data: Dict[str, Any], email_text: str) -> Dict[str, Any]:
    """
    Production validation pipeline: AI -> Validation -> Priority Regex -> Domain Dictionary -> Normalization -> Output
    """
    from datetime import timedelta

    if not isinstance(rfq_data, dict):
        rfq_data = {}

    # 1. ITEM DESCRIPTION VALIDATION
    desc = str(rfq_data.get("item_description") or "").strip()

    # Clean leading filler phrases
    desc = re.sub(
        r'^(we\s+request\s+you\s+to\s+submit\s+your\s+quotation\s+for\s+the\s+supply\s+of|please\s+provide\s+quotation\s+for\s+)?(the\s+following\s+items?\.?\s*\(?|we\s+have\s+(a\s+)?requirement\s+(of|for)|requirement\s+(of|for)|(please\s+)?(provide|send)\s+(a\s+)?(quote|quotation|rate)\s+(for|of)|rfq\s+(for|of)|enquiry\s+(for|of)|(we\s+)?need|(we\s+)?require)\s*:?\s*\(?',
        '', desc, flags=re.IGNORECASE
    ).strip().rstrip(":")

    if desc.lower().startswith("of "):
        desc = desc[3:].strip()

    # Strip leading "Units of ", "Pcs of ", "Nos of "
    desc = re.sub(r'^(?:units?|pcs|nos|items?|packs?|boxes?)\s+of\s+', '', desc, flags=re.IGNORECASE).strip()

    # Strip quantity suffixes like "- Ten Pcs", "- 100 Mtr", "- Twenty Boxes", "- 500 Mtr", "- 50 Boxes"
    desc = re.sub(r'[\-\:]?\s*(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|fifty|hundred|\d+)\s*(?:nos|pcs|units?|items?|laptops?|sets?|mtr|meters?|kg|litres?|boxes?|packs?)\b.*$', '', desc, flags=re.IGNORECASE).strip()
    desc = desc.rstrip(" -:,.")

    # Recovery Tier 1: Priority Regular Expressions
    if is_generic_description(desc) or len(desc.split()) < 2 or len(desc) < 10:
        for p in PRODUCT_PATTERNS:
            m = re.search(p, email_text, re.IGNORECASE)
            if m:
                extracted = m.group(1).strip()
                extracted = re.sub(r'^(?:the\s+)?(?:supply\s+of\s+)?', '', extracted, flags=re.IGNORECASE).strip()
                if extracted and not is_generic_description(extracted):
                    desc = extracted
                    break

    # Recovery Tier 2: Safe Fallback Regex
    if is_generic_description(desc):
        m_fall = re.search(r'supply\s+of\s+(.+?)(?=\s+required|\s+needed|[,\;\n\.]|$)', email_text, re.IGNORECASE)
        if m_fall and not is_generic_description(m_fall.group(1).strip()):
            desc = m_fall.group(1).strip()

    # Recovery Tier 3: Industrial Domain Product Dictionary Match
    if is_generic_description(desc):
        for dict_item in INDUSTRIAL_PRODUCT_DICTIONARY:
            if re.search(rf"\b{re.escape(dict_item)}\b", email_text, re.IGNORECASE):
                desc = dict_item
                break

    rfq_data["item_description"] = desc if not is_generic_description(desc) else "Procurement Request"

    # 2. QUANTITY VALIDATION (Explicit + Need Verb + Word Numbers + Unit Digits + Item Counts)
    explicit_qty = re.search(r'(?:quantity|qty|count)\s*[:=\-]?\s*(\d+)', email_text, re.IGNORECASE)
    need_qty = re.search(r'\b(?:need|require|looking\s+for|procure|purchase|want|supply\s+of|quotation\s+for|requirement\s+(?:for|of|is\s+for|includes))\s+(?:\d*\s+)?(\d{1,4})\b', email_text, re.IGNORECASE)
    cam_qty = re.search(r'\b(\d{1,4})\s*(?:IP\s+Cameras|Cameras|nos|pcs|units|items)\b', email_text, re.IGNORECASE)
    qty_word = re.search(r'(?:qty|quantity|count)\s*[:=\-]?\s*(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|fifty|hundred)\b', email_text, re.IGNORECASE)
    word_qty = re.search(r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|fifty|hundred)\b(?:\s*\(\d+\)\s*)?(?:\s*' + UOM_REGEX + ')?', email_text, re.IGNORECASE)

    if explicit_qty:
        quantity = int(explicit_qty.group(1))
    elif cam_qty:
        quantity = int(cam_qty.group(1))
    elif need_qty:
        quantity = int(need_qty.group(1))
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

    # 3. UOM VALIDATION (25 Procurement Units)
    if not rfq_data.get("uom") or rfq_data["uom"].lower() in ["", "none", "null"]:
        uom_m = re.search(UOM_REGEX, email_text, re.IGNORECASE)
        if uom_m:
            rfq_data["uom"] = uom_m.group(1).capitalize()
        else:
            rfq_data["uom"] = "Nos"

    # 4. BRAND VALIDATION ("Any", "No Specific", "Open", "Equivalent" Brand Recognition)
    brand = str(rfq_data.get("brand") or "").strip()
    if re.search(r'\b(any|equivalent|open|no\s+specific)\s+(brand|make)\b', email_text, re.IGNORECASE):
        brand = "Any"
    elif not brand or brand.lower() in ["we look forward to your quotation", "not specified", "none"]:
        for b in COMMON_BRANDS:
            if re.search(rf"\b{re.escape(b)}\b", email_text, re.IGNORECASE):
                brand = b
                break
    rfq_data["brand"] = brand or "Not Specified"

    # 5. FULL PHRASE SPECIFICATIONS EXTRACTION (Includes Requirement Lists & Model Codes)
    specs_list = []
    req_inc = re.search(r'\b(?:requirement\s+includes|includes|specifications?|features?)\s*[:=\-]?\s*([^\n\.]+?)(?=\s*(?:The\s+delivery|Kindly\s+include|[;\n\.]|\d{6})|$)', email_text, re.IGNORECASE)
    if req_inc:
        specs_list.append(req_inc.group(1).strip())

    for sp in SPEC_PATTERNS:
        m = re.search(sp, email_text, re.IGNORECASE)
        if m:
            val = m.group(0).strip()
            # Avoid adding sub-phrases if already covered by full requirement clause
            if not any(val.lower() in existing.lower() for existing in specs_list):
                specs_list.append(val)

    if specs_list:
        rfq_data["specifications"] = ", ".join(specs_list)
    elif not rfq_data.get("specifications"):
        rfq_data["specifications"] = f"{rfq_data['item_description']}" + (f", Brand: {brand}" if brand else "")

    # 6. DELIVERY DATE NORMALIZATION (ISO YYYY-MM-DD with relative days calculation)
    delivery_date = str(rfq_data.get("delivery_date") or "").strip()
    if not delivery_date:
        rel_days = re.search(r'\b(?:within|in)\s+(\d{1,3})\s+days\b|\b(\d{1,3})\s+days\s+from\b', email_text, re.IGNORECASE)
        if rel_days:
            num_days = int(rel_days.group(1) or rel_days.group(2))
            delivery_date = (datetime.now() + timedelta(days=num_days)).strftime("%Y-%m-%d")
        else:
            date_match = re.search(r'\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{4}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b', email_text, re.IGNORECASE)
            if date_match:
                delivery_date = date_match.group(1).strip()

    rfq_data["delivery_date"] = normalize_date(delivery_date)

    # 7. DELIVERY LOCATION, STATE & PINCODE EXTRACTION WITH AUTOMATIC PINCODE LOOKUP
    loc = re.search(r'(?:delivery\s+location|delivery\s+address|delivery\s+site|ship\s+to|destination|location|site|pincode|pin)\s*(?:is|[:=\-])\s*([^\n\.]+?)(?=\s*(?:and\s+the|and|within|from|kindly|specs|specifications|quantity|qty|brand|date|\n)|$)', email_text, re.IGNORECASE)
    if loc:
        location_raw = loc.group(1).strip()
        pin = re.search(r'\b\d{6}\b', location_raw)
        if pin:
            rfq_data["delivery_pincode"] = pin.group()

        clean_loc = re.sub(r'\b\d{6}\b', '', location_raw).strip(" ,.")
        clean_loc = re.sub(r'^(?:is|at)\s+', '', clean_loc, flags=re.IGNORECASE).strip()
        parts = [p.strip() for p in clean_loc.split(',') if p.strip()]
        if parts:
            rfq_data["delivery_city"] = parts[0]
            if len(parts) > 1 and not rfq_data.get("delivery_state"):
                rfq_data["delivery_state"] = parts[1]

    # Standalone Pincode Detection if pincode missing
    if not rfq_data.get("delivery_pincode"):
        pin_standalone = re.search(r'\b[1-9]\d{5}\b', email_text)
        if pin_standalone:
            rfq_data["delivery_pincode"] = pin_standalone.group(0)

    # Automatic City & State Lookup from Pincode if city missing
    if rfq_data.get("delivery_pincode") and not rfq_data.get("delivery_city"):
        city_lookup, state_lookup = lookup_pincode_location(rfq_data["delivery_pincode"])
        if city_lookup:
            rfq_data["delivery_city"] = city_lookup
        if state_lookup and not rfq_data.get("delivery_state"):
            rfq_data["delivery_state"] = state_lookup

    return rfq_data


# ---------------------------------------------------------------------------
# Ollama Few-Shot LLM Extraction Core
# ---------------------------------------------------------------------------

def extract_rfq(email_text: str) -> Dict[str, Any]:
    """
    Main RFQ Extraction Entrypoint.
    Executes Few-Shot Ollama Llama3 JSON Extraction -> Validation -> Normalization.
    """
    if not isinstance(email_text, str):
        email_text = str(email_text or "")

    # Allow up to 25,000 characters so long PDF/DOCX text is not truncated
    if len(email_text) > 25000:
        email_text = email_text[:25000]

    prompt = f"""You are a Senior Procurement AI System extracting RFQ data into valid JSON.

CRITICAL RULES:
1. item_description MUST be the COMPLETE PRODUCT NAME.
   NEVER return generic single words like "Office", "Printer", "Laptop", "Cable", "Pipe", "Paint", "Description", "Item", "Product", "Procurement Request".
2. quantity MUST be an integer representing item count only. Convert words ("Five" -> 5).
3. brand: If document specifies "any brand", "open brand", "equivalent make", return "Any".
4. delivery_date: Output ISO date format YYYY-MM-DD.

EXAMPLES:

Example 1:
Input: "We request quotation for supply of Office Multifunction Laser Printers required for our team. Five Nos. Any brand. Delivery Date: 10 August 2026. Location: Bangalore 560001."
Output:
{{
  "item_description": "Office Multifunction Laser Printers",
  "specifications": "Print, Scan, Copy, Duplex",
  "quantity": 5,
  "uom": "Nos",
  "brand": "Any",
  "delivery_date": "2026-08-10",
  "delivery_city": "Bangalore",
  "delivery_state": "",
  "delivery_pincode": "560001"
}}

Example 2:
Input: "Requirement for Dell Latitude 5450 Laptop - Ten Pcs. Specs: 16GB RAM, 512GB SSD. Delivery: 15-08-2026."
Output:
{{
  "item_description": "Dell Latitude 5450 Laptop",
  "specifications": "16GB RAM, 512GB SSD",
  "quantity": 10,
  "uom": "Pcs",
  "brand": "Dell",
  "delivery_date": "2026-08-15",
  "delivery_city": "",
  "delivery_state": "",
  "delivery_pincode": ""
}}

Example 3:
Input: "Please quote for CPVC Pipe PN16 1 inch - 100 Mtr. Brand: Supreme. Delivery Date: 2026-08-25."
Output:
{{
  "item_description": "CPVC Pipe PN16 1 inch",
  "specifications": "CPVC, PN16, 1 inch",
  "quantity": 100,
  "uom": "Mtr",
  "brand": "Supreme",
  "delivery_date": "2026-08-25",
  "delivery_city": "",
  "delivery_state": "",
  "delivery_pincode": ""
}}

NOW EXTRACT FROM THIS RFQ TEXT:
{email_text}

Return ONLY VALID JSON following this exact structure:
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


def fallback_extract_rfq(email_text: str) -> Dict[str, Any]:
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


# ---------------------------------------------------------------------------
# Module Test Suite
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample = """
    We request you to submit your quotation for the supply of Office Multifunction Laser Printers required for our organization. Qty : Five Nos. Any brand. Delivery Date: 10th August 2026. Delivery Location: Bangalore, Karnataka, 560001. Specs: A4 Size, Print, Scan, Copy, Network Connectivity, Automatic Duplex Printing, 30-40 PPM, Warranty Details, Cartridge Yield, Installation Support.
    """

    rfq_data = extract_rfq(sample)
    print("\n========== AI EXTRACTED RFQ ==========")
    for k, v in rfq_data.items():
        print(f"{k:<18}: {v}")
    print("======================================\n")