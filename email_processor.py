from services.email_reader import read_unread_emails
from services.buyer_api_service import verify_buyer
from services.ai_extractor import extract_rfq
from services.rfq_api_service import create_rfq_api
import base64
import os
import re
from datetime import datetime, timedelta
from services.email_sender import (
    send_registration_email
)

def parse_delivery_date(raw_date_str):
    """
    Parses any delivery date format (e.g. 10-08-2026, 10/08/2026, 2026-08-10, 10 August 2026)
    into ISO YYYY-MM-DD format (e.g. 2026-08-10) required by Azure API. Defaults to +5 days if missing or invalid.
    """
    if not raw_date_str or not str(raw_date_str).strip():
        return (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")

    raw_str = str(raw_date_str).strip()
    raw_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', raw_str, flags=re.IGNORECASE)

    date_formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
        "%d-%b-%Y", "%d-%B-%Y", "%d %B %Y", "%d %b %Y", "%d.%m.%Y",
        "%B %d %Y", "%b %d %Y", "%B %d, %Y", "%b %d, %Y"
    ]

    for fmt in date_formats:
        try:
            parsed = datetime.strptime(raw_str, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Regex fallback for DD-MM-YYYY or DD/MM/YYYY
    m = re.search(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})', raw_str)
    if m:
        try:
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            parsed = datetime(year, month, day)
            return parsed.strftime("%Y-%m-%d")
        except Exception:
            pass

    m2 = re.search(r'(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})', raw_str)
    if m2:
        try:
            year, month, day = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
            parsed = datetime(year, month, day)
            return parsed.strftime("%Y-%m-%d")
        except Exception:
            pass

    return (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")


# ============================================
# Email Processing Function
# ============================================

def process_emails():

    # -----------------------------
    # Read All Unread Emails
    # -----------------------------

    emails = read_unread_emails()

    if len(emails) == 0:

        print("No unread emails found")

        return

    # -----------------------------
    # Process Each Email
    # -----------------------------

    for email_data in emails:

        print("\n===================================")
        print("Email Received")
        print("===================================\n")

        # -----------------------------
        # Extract Sender Email
        # -----------------------------

        sender = email_data["sender"]

        match = re.search(
            r'<(.+?)>',
            sender
        )

        if match:
            sender_email = match.group(1)
        else:
            sender_email = sender

        # -----------------------------
        # Buyer Validation
        # -----------------------------

        buyer = verify_buyer(sender_email)

        if not buyer:

            print(
                f"Buyer not found: {sender_email}"
            )

            send_registration_email(
                sender_email
            )

            continue

        print("Buyer Verified")
        print(buyer)

        # -----------------------------
        # AI Extraction
        # -----------------------------

        rfq_data = extract_rfq(
            email_data["body"]
        )

        print(
            "\n========== AI EXTRACTED RFQ =========="
        )

        print(
            f"Item Description : {rfq_data['item_description']}"
        )

        print(
            f"Specifications   : {rfq_data['specifications']}"
        )

        print(
            f"Quantity         : {rfq_data['quantity']}"
        )
        print(
        f"UOM              : {rfq_data.get('uom', '')}"
        )
        print(
            f"Brand            : {rfq_data.get('brand', '')}"
        )

        print(
            f"Delivery Date    : {rfq_data.get('delivery_date', '')}"
        )

        loc_parts = [rfq_data.get('delivery_city', ''), rfq_data.get('delivery_state', ''), rfq_data.get('delivery_pincode', '')]
        loc_str = ", ".join([p for p in loc_parts if p]).strip()
        print(
            f"Delivery Location: {loc_str}"
        )

        print(
            "======================================\n"
        )

        # -----------------------------
        # RFQ Validation
        # -----------------------------

        item_description = (
            rfq_data.get("item_description", "")
            .strip()
        )

        if item_description == "":

            print(
                "Invalid RFQ - Item Description Missing"
            )

            continue

        if len(item_description) < 3:

            print(
                "Invalid RFQ - Item Description Too Short"
            )

            continue

        if not rfq_data.get("quantity") or rfq_data["quantity"] <= 0:

            rfq_data["quantity"] = 1

        # -----------------------------
        # Delivery Date Handling
        # -----------------------------

        raw_delivery_date = rfq_data.get("delivery_date", "")
        delivery_date = parse_delivery_date(raw_delivery_date)

        # -----------------------------
        # Delivery Location Handling
        # -----------------------------

        delivery_city = (
            rfq_data.get("delivery_city", "")
            .strip()
                )

        delivery_state = (
            rfq_data.get("delivery_state", "")
            .strip()
        )

        delivery_pincode = (
            rfq_data.get("delivery_pincode", "")
            .strip()
        )

        # -----------------------------
        # Brand Handling
        # -----------------------------

        brand = rfq_data["brand"]

        if isinstance(
            brand,
            list
        ):
            brand = ", ".join(brand)

        brand = brand.strip()

        if brand == "":

            brand = "Brand: Not Specified"

        else:

            brand = f"Brand: {brand}"

        # -----------------------------
        # UOM Handling
        # -----------------------------

        uom = rfq_data.get(
        "uom",
        ""
        )

        uom = str(uom).strip()

        if uom == "":
            uom = "Nos"

        # -----------------------------
        # Specifications Handling
        # -----------------------------

        specifications = rfq_data.get(
            "specifications",
            ""
        )

        if specifications.strip() == "":

            specifications = item_description

        spec_parts = specifications.split(",")

        if len(spec_parts) > 3:

            specifications = ",".join(
                spec_parts[:3]
            )

            # -----------------------------
            # RFQ Object
            # -----------------------------



        
        # -----------------------------
        # Attachment Handling
        # -----------------------------

        rfq_documents = []

        attachment_items = email_data.get("attachments", [])
        if not attachment_items and email_data.get("attachment_path"):
            single_path = email_data.get("attachment_path")
            if os.path.exists(single_path) and os.path.getsize(single_path) > 0:
                attachment_items = [{
                    "path": single_path,
                    "filename": os.path.basename(single_path)
                }]

        for att in attachment_items:
            file_path = att.get("path")
            filename = att.get("filename") or os.path.basename(file_path)

            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    print(f"Skipping 0-byte empty attachment: {filename}")
                    continue

                try:
                    with open(file_path, "rb") as file:
                        raw_bytes = file.read()

                    if len(raw_bytes) > 0:
                        file_content = base64.b64encode(raw_bytes).decode("utf-8")

                        if file_content and len(file_content) > 0:
                            rfq_documents.append(
                                {
                                    "fileName": filename,
                                    "file": file_content
                                }
                            )
                            print(f"Attachment Processed Successfully: {filename} ({file_size} bytes, b64_len={len(file_content)})")
                except Exception as e:
                    print(f"Attachment Error for {filename}: {e}")

        # -----------------------------
        # RFQ Object
        # -----------------------------

        rfq_object = {

            "createdBy":
            buyer["name"],

            "projectDesc":
            item_description,

            "deliveryDate":
            delivery_date,

            "noPrFlag":
            True,

            "org": {
                "id": str(
                buyer["orgId"]
                )
            },

            "rfqItem": [

                {
                    "brand":
                    brand,

                    "unitofMeasures":
                    uom,

                    "quantity":
                    rfq_data["quantity"],

                    "description":
                    item_description,

                    "category":
                    None,

                    "createdBy":
                    buyer["name"],

                    "createdTS":
                    datetime.now().isoformat(),

                    "itemcode":
                    None,

                    "serialNo":
                    1001,

                    "remarks":
                    specifications
                }

            ],

            "vendors": [],

            "clientdeliverylocationrfq": [

                {
                    "state":
                    delivery_state,

                    "city":
                    delivery_city,

                    "pincode":
                    delivery_pincode
                }

            ],

            "remarks": "",
            
            "rfqDocument":
            rfq_documents,

            "user":
            str(
                buyer["userId"]
            ),

            "sourceType":
            "T"
        }

        # -----------------------------
        # RFQ Object Print
        # -----------------------------

        print(
            "\nRFQ OBJECT"
        )

        print(
            rfq_object
        )

        # -----------------------------
        # Send RFQ To API
        # -----------------------------
        print("\nSending RFQ To API...")
        token = buyer.get("token") or buyer.get("jwtToken") if isinstance(buyer, dict) else None
        response = create_rfq_api(rfq_object, token)

        if isinstance(response, dict) and (response.get("status") == "Success" or response.get("code") == "00"):

            print("\nRFQ Created Successfully")

        else:

            desc = response.get('description') if isinstance(response, dict) else str(response)
            print(
                f"\nRFQ Creation Failed : {desc}"
            )