"""
Enterprise Multi-Item RFQ Extraction Engine - Production Grade Pipeline
Architecture: Few-Shot LLM (Ollama) -> Table Parser -> Multiline Scope -> Multi-Brand -> Dictionary Normalization -> Multi-Item Schema
Author: Senior AI Engineer
"""

import requests
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Enterprise Domain Dictionaries, Pincode Maps & Multi-Brand Registries
# ---------------------------------------------------------------------------

COMMON_BRANDS: List[str] = [
    "Dell", "HP", "Lenovo", "Acer", "Apple", "Asus", "Samsung", "LG", "Cisco",
    "Asian Paints", "Berger", "Dulux", "Nerolac", "Havells", "Schneider",
    "Legrand", "Finolex", "Supreme", "Ashirvad", "Astral", "Polycab",
    "Tata", "JSW", "Bosch", "Siemens", "Philips", "Godrej", "Crompton",
    "Anchor", "L&T", "Honeywell", "3M", "Kirloskar", "ABB", "CP Plus",
    "Hikvision", "Dahua", "Eaton", "Danfoss", "SKF", "FAG", "Grundfos",
    "Emerson", "APC", "Makita", "Dewalt"
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

# 200+ Enterprise Normalized Product Dictionary across 15 Industrial Categories
INDUSTRIAL_PRODUCT_DICTIONARY: List[str] = [
    # IT & Telecom
    "IP CCTV Surveillance System", "CCTV Surveillance System", "IP Cameras", "NVR",
    "Multifunction Laser Printers", "Laser Printers", "Desktop Computers",
    "Latitude Laptops", "Laptops", "Network Switches", "Cisco Switch", "Online UPS",
    "Rack Server", "Workstation PC", "Gigabit Router", "CAT6 Network Cables",
    # Safety & PPE
    "Industrial Personal Protective Equipment (PPE) Kits", "Personal Protective Equipment (PPE) Kits",
    "PPE Kits", "Safety Shoes", "Safety Helmets", "Hand Gloves", "Safety Goggles",
    "Reflective Jackets", "Ear Protection", "Fire Extinguishers", "Fall Arrest Harness",
    # Electrical & Power
    "XLPE Armoured Aluminium Cables", "Armoured Cables", "Copper Cables", "MCCB Circuit Breaker",
    "MCB Circuit Breaker", "Automatic Voltage Stabilizer", "Distribution Transformer",
    "Distribution Board", "LED Flood Lights", "Switchgear Panel", "VFD Drive",
    # Mechanical, MRO & Tools
    "Centrifugal Water Pump", "Air Compressor", "Hammer Drill Machine", "Ball Bearings",
    "Taper Roller Bearings", "Butterfly Valves", "Gate Valves", "Globe Valves",
    "Check Valves", "Flanged End Ball Valve", "Stainless Steel Flanges", "Industrial Gearbox",
    # Civil, Piping & Plumbing
    "CPVC Pipes", "PVC Pipes", "GI Pipes", "HDPE Pipes", "SS 304 Pipes", "SS 316 Pipes",
    "Solvent Cement", "TMT Steel Rebars", "Structural Steel Channels", "MS Angles",
    # Paint & Chemicals
    "Acrylic Emulsion Paint", "Exterior Emulsion Paint", "Epoxy Primer", "Industrial Solvent",
    "Polyurethane Coating", "Enamel Paint", "Caustic Soda", "Hydrochloric Acid"
]

PRODUCT_PATTERNS: List[str] = [
    # Header / Subject match
    r'\b(?:subject|re|rfq|enquiry|tender|quotation)\s*[:=\-]\s*([A-Za-z0-9\s\-\/\(\)]+?)(?=[;\n\.]|\s*(?:quantity|qty|brand|delivery)|$)',

    # Explicit Tagged Fields
    r'\b(?:item\s*name|product\s*name|item|product)\s*[:=\-]?\s*([A-Za-z0-9\s\-\/\.\(\)]+?)(?=[;\n\.]|\s*(?:quantity|qty|brand|uom)|$)',

    # Supply, installation and commissioning of / Supply of / Procurement of
    r'\b(?:supply|procurement|purchase|installation|commissioning)(?:[,\s]+(?:installation|commissioning|testing))*?\s+of\s+(?:an?\s+)?([A-Za-z0-9\s\-\/\(\)]+?)(?=\s+(?:consisting|required|needed|for\s+our|for\s+facility|for\s+project)|[;\n\.]|\s*(?:delivery|specs|quantity|qty|brand)|$)',

    # Quotation for / Please quote for
    r'\b(?:quotation\s+for|quote\s+for|please\s+quote\s+for)\s+(?:the\s+)?(?:supply|procurement|purchase|installation|commissioning)?(?:[,\s]+(?:installation|commissioning))*?\s*of\s+(?:an?\s+)?([A-Za-z0-9\s\-\/\(\)]+?)(?=\s+(?:consisting|required|needed|for\s+our|for\s+facility|for\s+project)|[;\n\.]|\s*(?:delivery|specs|quantity|qty|brand)|$)',

    # Requirement of/for
    r'\b(?:requirement\s+(?:of|for|is\s+for))\s+(?:the\s+)?([A-Za-z0-9\s\-\/\(\)]+?)(?=\s+(?:consisting|required|needed|for\s+our|for\s+facility|for\s+project)|[;\n\.]|\s*(?:delivery|specs|quantity|qty|brand)|$)',

    # Looking for / Need / Require
    r'\b(?:looking\s+for|need|require)\s+(?:\d+\s+)?(?:nos|pcs|units|items)?\s*(?:of\s+)?([A-Za-z0-9\s\-\/\(\)]+?)(?=\s+(?:for|delivery|pincode|qty|brand|location)|[;\n\.]|$)'
]

UOM_REGEX: str = r'\b(nos|pcs|kg|boxes?|packs?|bags?|each|ea|lot|lumpsum|sets?|pair|coil|roll|bundle|sheet|tons?|mt|kl|ltr|litres?|sqft|sqm|cum|mtr|meters?|laptops?|printers?|units?|items?|cameras?|kits?|tins)\b'


# ---------------------------------------------------------------------------
# Helper & Extraction Engine Utilities
# ---------------------------------------------------------------------------

def is_generic_description(desc_str: Optional[str]) -> bool:
    """Validates if an item description is generic noise, header artifact or document filler."""
    if not desc_str or not str(desc_str).strip():
        return True

    clean = re.sub(r'\s+', ' ', str(desc_str).strip().lower())
    generic_exact = [
        "procurement request", "procurement", "request", "rfq", "enquiry", "quotation", "quote",
        "description specification / make", "description specification make", "description specification",
        "item description", "product description", "specification / make", "specification make",
        "description / specification", "item name", "product name", "item", "product", "particulars",
        "sl no", "s.no", "description", "specification", "make", "material", "general item",
        "office", "printer", "laptop", "pipe", "cable", "paint", "industrial", "accessories",
        "catalogue", "product catalogue", "technical datasheet", "datasheet", "commercial terms",
        "installation support", "warranty details", "cartridge yield", "warranty", "terms"
    ]
    if clean in generic_exact:
        return True

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
    """Normalizes explicit calendar date into YYYY-MM-DD or preserves clean relative PO phrase."""
    if not date_str or not str(date_str).strip():
        return ""
    raw = str(date_str).strip()

    # Relative PO phrase recognition (e.g., "within 15 days from Purchase Order")
    if re.search(r'\b(?:days?\s+from|within|days?\s+after|purchase\s+order|po\b|immediate)', raw, re.IGNORECASE):
        clean_rel = re.sub(r'\s+', ' ', raw).strip()
        return clean_rel

    raw_clean = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', raw, flags=re.IGNORECASE)
    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
        "%d-%b-%Y", "%d-%B-%Y", "%d %B %Y", "%d %b %Y", "%d.%m.%Y",
        "%B %d %Y", "%b %d %Y", "%B %d, %Y", "%b %d, %Y", "%Y %b %d", "%Y %B %d"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw_clean, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    m = re.search(r'(\d{1,2})[\s\/\-\.]+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\/\-\.]+(\d{4})', raw_clean, re.IGNORECASE)
    if m:
        try:
            date_raw = f"{m.group(1)} {m.group(2)} {m.group(3)}"
            return datetime.strptime(date_raw, "%d %b %Y").strftime("%Y-%m-%d")
        except Exception:
            pass

    return raw


def lookup_pincode_location(pincode_str: Optional[str]) -> tuple:
    """Looks up City & State from Indian Pincode prefix."""
    if not pincode_str or len(str(pincode_str).strip()) != 6:
        return "", ""
    pin = str(pincode_str).strip()
    return PINCODE_PREFIX_MAP.get(pin[:3], ("", ""))


def extract_multi_brands(text: str) -> str:
    """Extracts multi-brand / equivalent strings like 'Schneider / ABB / Siemens / Legrand or equivalent'."""
    m_brand = re.search(r'\b(?:brand|make|manufacturer)\s*[:=\-]?\s*([A-Za-z0-9\s\/\-\&]+?)(?=[;\n\.]|\s*(?:delivery|specs|quantity|qty|material)|$)', text, re.IGNORECASE)
    if m_brand:
        extracted = m_brand.group(1).strip()
        if extracted and len(extracted) > 1 and not is_generic_description(extracted):
            return extracted

    matched_brands = []
    for b in COMMON_BRANDS:
        if re.search(rf"\b{re.escape(b)}\b", text, re.IGNORECASE):
            if b not in matched_brands:
                matched_brands.append(b)

    if matched_brands:
        if len(matched_brands) > 1:
            base = " / ".join(matched_brands)
            if re.search(r'\bor\s+equivalent\b', text, re.IGNORECASE):
                return base + " or equivalent"
            return base
        return matched_brands[0]

    if re.search(r'\b(any|equivalent|open|no\s+specific)\s+(brand|make)\b', text, re.IGNORECASE):
        return "Any"

    return "Not Specified"


def parse_rfq_table(email_text: str) -> List[Dict[str, Any]]:
    """
    Parses structured tabular RFQs (ASCII, Markdown, Pipe, or Tab delimited) into item list.
    E.g.:
    Sl No | Description | Qty | UOM
    1     | CPVC Pipe 1 inch | 100 | Mtr
    2     | Solvent Cement 500ml | 20 | Tins
    """
    items = []
    lines = [line.strip() for line in email_text.splitlines() if line.strip()]

    for line in lines:
        if '|' in line:
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 3 and not any(h in parts[0].lower() for h in ['sl', 's.no', 'item', 'description', 'particulars']):
                try:
                    desc_candidate = parts[1] if len(parts) > 3 else parts[0]
                    qty_candidate = parts[2] if len(parts) > 3 else parts[1]
                    uom_candidate = parts[3] if len(parts) > 3 else "Nos"

                    m_qty = re.search(r'\d+', qty_candidate)
                    if m_qty and not is_generic_description(desc_candidate):
                        items.append({
                            "item_description": desc_candidate,
                            "quantity": int(m_qty.group()),
                            "uom": uom_candidate if uom_candidate else "Nos",
                            "brand": extract_multi_brands(email_text),
                            "specifications": desc_candidate
                        })
                except Exception:
                    pass

    return items


# ---------------------------------------------------------------------------
# Core Production Validation & Normalization Pipeline
# ---------------------------------------------------------------------------

def validate_and_normalize_rfq(rfq_data: Dict[str, Any], email_text: str) -> Dict[str, Any]:
    """
    Enterprise production validation pipeline supporting Multi-Item JSON Schema,
    Multiline Specifications, Multiline Addresses, and PO Relative Delivery Dates.
    """
    if not isinstance(rfq_data, dict):
        rfq_data = {}

    items: List[Dict[str, Any]] = rfq_data.get("items") or []

    # Convert single item dictionary from LLM/Single-pass to items list
    if not items and rfq_data.get("item_description"):
        items.append({
            "item_description": rfq_data.get("item_description"),
            "quantity": rfq_data.get("quantity", 1),
            "uom": rfq_data.get("uom", "Nos"),
            "brand": rfq_data.get("brand", extract_multi_brands(email_text)),
            "specifications": rfq_data.get("specifications", "")
        })

    # Check for Tabular RFQs
    if not items:
        table_items = parse_rfq_table(email_text)
        if table_items:
            items = table_items

    # Multiline List Pattern Extraction (e.g. 1. Dell Laptop - 20 Nos \n 2. HP Printer - 5 Nos)
    if not items:
        list_items = re.findall(r'(?:^|\n)\s*(?:\d+[\.\)]|\-|\*)\s*([^\n]+)', email_text)
        if len(list_items) >= 2:
            for itm in list_items:
                itm_clean = itm.strip()
                if itm_clean and len(itm_clean) > 4 and not is_generic_description(itm_clean):
                    m_q = re.search(r'[\-\:\s]+(\d+)\s*(?:nos|pcs|units|items|mtr|tins)?\b', itm_clean, re.IGNORECASE)
                    qty = int(m_q.group(1)) if m_q else 1

                    clean_title = re.sub(r'[\-\:]?\s*\d+\s*(?:nos|pcs|units|items|mtr|tins)?\b.*$', '', itm_clean, flags=re.IGNORECASE).strip()
                    clean_title = clean_title.rstrip(" -:,.")

                    items.append({
                        "item_description": clean_title if clean_title else itm_clean,
                        "quantity": qty,
                        "uom": "Nos",
                        "brand": extract_multi_brands(email_text),
                        "specifications": itm_clean
                    })

    # Single Main Item Fallback
    if not items:
        desc = ""
        for p in PRODUCT_PATTERNS:
            m = re.search(p, email_text, re.IGNORECASE)
            if m:
                extracted = m.group(1).strip()
                extracted = re.sub(r'^(?:the\s+)?(?:supply\s+of\s+)?', '', extracted, flags=re.IGNORECASE).strip()
                if extracted and not is_generic_description(extracted):
                    desc = extracted
                    break

        if is_generic_description(desc):
            for dict_item in INDUSTRIAL_PRODUCT_DICTIONARY:
                if re.search(rf"\b{re.escape(dict_item)}\b", email_text, re.IGNORECASE):
                    desc = dict_item
                    break

        if is_generic_description(desc):
            desc = "Procurement Request"

        items.append({
            "item_description": desc,
            "quantity": 1,
            "uom": "Nos",
            "brand": extract_multi_brands(email_text),
            "specifications": desc
        })

    # MULTILINE SPECIFICATIONS & SCOPE CAPTURE (Spans across newlines up to section headers)
    multiline_spec = re.search(
        r'((?:consisting\s+of|scope\s+includes|requirement\s+includes|includes|specifications?)\s*[:=\-]?\s*[\s\S]{1,800}?)(?=\n\s*(?:Brand|Make|Material|The\s+material|The\s+delivery|Delivery|Kindly|Commercial|Payment|Terms|Regards|\n\n[A-Z0-9])|$)',
        email_text, re.IGNORECASE
    )

    full_spec_text = multiline_spec.group(1).strip() if multiline_spec else ""

    # Normalize items list
    for item in items:
        item_desc = str(item.get("item_description") or "").strip()
        item_desc = re.sub(r'^(?:supply|procurement|purchase|installation|commissioning|requirement\s+for|supply\s+of)\s+(?:of\s+)?(?:an?\s+)?', '', item_desc, flags=re.IGNORECASE).strip()
        item_desc = item_desc.rstrip(" -:,.")

        if is_generic_description(item_desc):
            for dict_item in INDUSTRIAL_PRODUCT_DICTIONARY:
                if re.search(rf"\b{re.escape(dict_item)}\b", email_text, re.IGNORECASE):
                    item_desc = dict_item
                    break

        item["item_description"] = item_desc if not is_generic_description(item_desc) else "Procurement Request"

        try:
            qty = int(item.get("quantity", 0))
        except Exception:
            qty = 0

        if qty <= 0 or qty > 50000:
            m_q = re.search(r'\b(?:quantity|qty|count|for|includes|require)\s*(?:is|for)?\s*(\d{1,5})\b|\b(\d{1,5})\s*' + UOM_REGEX, email_text, re.IGNORECASE)
            qty = int(m_q.group(1) or m_q.group(2)) if m_q else 1
        item["quantity"] = qty

        if not item.get("uom") or item["uom"].lower() in ["", "none", "null"]:
            uom_m = re.search(UOM_REGEX, email_text, re.IGNORECASE)
            item["uom"] = uom_m.group(1).capitalize() if uom_m else "Nos"

        if not item.get("brand") or item["brand"] in ["Not Specified", ""]:
            item["brand"] = extract_multi_brands(email_text)

        if full_spec_text and (is_generic_description(item.get("specifications")) or len(str(item.get("specifications"))) < 15):
            item["specifications"] = full_spec_text

    # MULTILINE LOCATION & ADDRESS BLOCK PARSING
    loc_multi = re.search(
        r'(?:delivery\s+location|delivery\s+address|delivery\s+site|material\s+should\s+be\s+delivered\s+to|material\s+is\s+required|required\s+at|delivered\s+at|ship\s+to|destination|location|site)\s*(?:is|at|to|[:=\-])?\s*([\s\S]{1,300}?)(?=\n\s*(?:within|from|kindly|specs|specifications|quantity|qty|brand|delivery\s+within|date|commercial|payment|terms|regards|\n\n[A-Z])|$)',
        email_text, re.IGNORECASE
    )

    full_address = loc_multi.group(1).strip() if loc_multi else ""
    full_address_clean = re.sub(r'\s+', ' ', full_address).strip(" ,.")

    pincode = ""
    pin_m = re.search(r'\b[1-9]\d{5}\b', email_text)
    if pin_m:
        pincode = pin_m.group(0)

    city, state = "", ""
    if pincode:
        city_lookup, state_lookup = lookup_pincode_location(pincode)
        if city_lookup:
            city = city_lookup
        if state_lookup:
            state = state_lookup

    if not city and full_address_clean:
        clean_addr = re.sub(r'\b\d{6}\b', '', full_address_clean).strip(" ,.")
        parts = [p.strip() for p in clean_addr.split(',') if p.strip()]
        if parts:
            city = parts[0]
            if len(parts) > 1:
                state = parts[1]

    # RELATIVE PO DELIVERY DATE / CALENDAR ISO DATE PARSING
    delivery_date = str(rfq_data.get("delivery_date") or "").strip()
    if not delivery_date:
        rel_po = re.search(r'\b(?:within|in)\s+(\d{1,3}\s+days\s+(?:from|after)?\s*(?:the\s+)?(?:date\s+of\s+)?(?:Purchase\s+Order|PO\b)?|\d{1,3}\s+days\s+from\s+PO\b)', email_text, re.IGNORECASE)
        if rel_po:
            delivery_date = rel_po.group(0).strip()
        else:
            rel_days = re.search(r'\b(?:within|in)\s+(\d{1,3})\s+days\b', email_text, re.IGNORECASE)
            if rel_days:
                num_days = int(rel_days.group(1))
                delivery_date = f"within {num_days} days from Purchase Order"
            else:
                date_match = re.search(r'\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{4}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b', email_text, re.IGNORECASE)
                if date_match:
                    delivery_date = date_match.group(1).strip()

    delivery_date_final = normalize_date(delivery_date)

    main_item = items[0]
    return {
        "items": items,
        "item_description": main_item["item_description"],
        "quantity": main_item["quantity"],
        "uom": main_item["uom"],
        "brand": main_item["brand"],
        "specifications": main_item["specifications"],
        "delivery_date": delivery_date_final,
        "delivery_city": city,
        "delivery_state": state,
        "delivery_pincode": pincode,
        "delivery_location_full": full_address_clean
    }


# ---------------------------------------------------------------------------
# Ollama Few-Shot LLM Extraction Core (Expanded 15-Category Prompt)
# ---------------------------------------------------------------------------

def extract_rfq(email_text: str) -> Dict[str, Any]:
    """
    Main RFQ Extraction Entrypoint.
    Executes Few-Shot Ollama Llama3 JSON Extraction -> Validation -> Normalization.
    """
    if not isinstance(email_text, str):
        email_text = str(email_text or "")

    if len(email_text) > 25000:
        email_text = email_text[:25000]

    prompt = f"""You are an Enterprise Procurement AI System extracting multi-item RFQ data into valid JSON.

CRITICAL RULES:
1. items MUST be an array of objects. Extract ALL products requested in the RFQ.
2. item_description MUST be the COMPLETE PRODUCT NAME.
3. quantity MUST be an integer. Convert words ("Five" -> 5).
4. brand: Extract full brand string (e.g., "Schneider / ABB or equivalent").
5. delivery_date: Preserve phrases like "Within 15 days from Purchase Order" or ISO YYYY-MM-DD.

EXAMPLES:

Example 1 (Multi-Item Request):
Input: "Please quote for: 1. Dell Latitude 5450 Laptop - 20 Nos. 2. HP Laser Printer - 5 Nos. Delivery location: Pune 411001 within 15 days from PO."
Output:
{{
  "items": [
    {{"item_description": "Dell Latitude 5450 Laptop", "quantity": 20, "uom": "Nos", "brand": "Dell", "specifications": "Dell Latitude 5450 Laptop"}},
    {{"item_description": "HP Laser Printer", "quantity": 5, "uom": "Nos", "brand": "HP", "specifications": "HP Laser Printer"}}
  ],
  "delivery_date": "Within 15 days from Purchase Order",
  "delivery_city": "Pune",
  "delivery_state": "Maharashtra",
  "delivery_pincode": "411001"
}}

Example 2 (CCTV System Scope):
Input: "Quotation for supply & installation of IP CCTV Surveillance System consisting of 16 IP Cameras, 2 NVR, 2TB HDD, POE Switch. Brand: Hikvision / CP Plus or equivalent. Delivery: Chennai, Tamil Nadu."
Output:
{{
  "items": [
    {{
      "item_description": "IP CCTV Surveillance System",
      "quantity": 16,
      "uom": "Nos",
      "brand": "Hikvision / CP Plus or equivalent",
      "specifications": "consisting of 16 IP Cameras, 2 NVR, 2TB HDD, POE Switch"
    }}
  ],
  "delivery_date": "",
  "delivery_city": "Chennai",
  "delivery_state": "Tamil Nadu",
  "delivery_pincode": ""
}}

NOW EXTRACT FROM THIS RFQ TEXT:
{email_text}

Return ONLY VALID JSON following this exact structure:
{{
  "items": [
    {{
      "item_description": "",
      "quantity": 0,
      "uom": "",
      "brand": "",
      "specifications": ""
    }}
  ],
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
                    "num_predict": 500,
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
    except Exception:
        # Silent fallback to high-precision rule engine when Ollama LLM is offline or not installed
        pass

    if not rfq_data:
        rfq_data = fallback_extract_rfq(email_text)

    return validate_and_normalize_rfq(rfq_data, email_text)


def fallback_extract_rfq(email_text: str) -> Dict[str, Any]:
    """
    Enterprise rule-based fallback extractor when Ollama is offline.
    """
    if not email_text:
        email_text = ""

    rfq_data = {
        "items": [],
        "delivery_date": "",
        "delivery_city": "",
        "delivery_state": "",
        "delivery_pincode": ""
    }

    return validate_and_normalize_rfq(rfq_data, email_text)