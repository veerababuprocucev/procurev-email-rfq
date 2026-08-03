import imaplib
import email
import sys
import os
import re

from datetime import (
    datetime,
    timedelta
)

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from config import (
    EMAIL,
    APP_PASSWORD
)

# from services.buyer_service import (
#     get_buyer
# )

from services.attachment_reader import (
    extract_attachment_text
)


def read_unread_emails():

    mail = imaplib.IMAP4_SSL(
        "imap.gmail.com"
    )

    mail.login(
        EMAIL,
        APP_PASSWORD
    )

    mail.select("inbox")

    # Last 24 Hours
    yesterday = (
        datetime.now()
        - timedelta(days=1)
    ).strftime("%d-%b-%Y")

    status, messages = mail.search(
        None,
        f'(UNSEEN SINCE "{yesterday}")'
        #  "UNSEEN"
    )

    email_ids = messages[0].split()

    # Maximum 50 emails
    email_ids = email_ids[-50:]

    if len(email_ids) == 0:

        mail.logout()

        return []

    emails = []

    for email_id in email_ids:

        try:

            status, msg_data = mail.fetch(
                email_id,
                "(BODY.PEEK[])"
            )

            raw_email = msg_data[0][1]

            msg = email.message_from_bytes(
                raw_email
            )

            sender = msg["From"]

            match = re.search(
                r"<(.+?)>",
                sender
            )

            if match:

                sender_email = (
                    match.group(1)
                )

            else:

                sender_email = sender

            # Buyer Validation

            # buyer = get_buyer(
            #     sender_email
            # )

            # if not buyer:

            #     print(
            #         f"Buyer not found: {sender_email}"
            #     )
            #     mail.store(
            #     email_id,
            #     '+FLAGS',
            #     '\\Seen'
            # )

            #     continue

            # print(
            #     f"Buyer Verified: {sender_email}"
            # )


            subject = (
                msg["Subject"]
                if msg["Subject"]
                else ""
            )

            body = ""

            attachment_text = ""

            attachment_type = ""
            attachment_path = ""
            attachments_list = []

            if msg.is_multipart():

                for part in msg.walk():

                    content_type = (
                        part.get_content_type()
                    )

                    raw_filename = (
                        part.get_filename()
                    )

                    # Email Body

                    if (
                        content_type
                        == "text/plain"
                        and not raw_filename
                    ):

                        try:

                            body += (
                                part.get_payload(
                                    decode=True
                                )
                                .decode(
                                    errors="ignore"
                                )
                            )

                        except Exception:

                            pass

                    # Attachments

                    if raw_filename:
                        # Decode RFC 2047 / MIME header filename
                        from email.header import decode_header
                        try:
                            decoded_fragments = decode_header(raw_filename)
                            fn_parts = []
                            for frag, enc in decoded_fragments:
                                if isinstance(frag, bytes):
                                    fn_parts.append(frag.decode(enc or 'utf-8', errors='ignore'))
                                else:
                                    fn_parts.append(str(frag))
                            filename = "".join(fn_parts).strip()
                            filename = os.path.basename(filename)
                        except Exception:
                            filename = os.path.basename(raw_filename)

                        if not filename:
                            continue

                        # Extract payload safely
                        payload = part.get_payload(decode=True)
                        if not payload:
                            raw_p = part.get_payload()
                            if isinstance(raw_p, str):
                                try:
                                    import base64
                                    payload = base64.b64decode(raw_p)
                                except Exception:
                                    payload = raw_p.encode("utf-8")
                            elif isinstance(raw_p, bytes):
                                payload = raw_p

                        # Prevent writing 0-byte or None files
                        if payload and len(payload) > 0:
                            os.makedirs(
                                "attachments",
                                exist_ok=True
                            )

                            file_path = (
                                os.path.join(
                                    "attachments",
                                    filename
                                )
                            )

                            with open(
                                file_path,
                                "wb"
                            ) as f:
                                f.write(payload)
                            
                            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                                extension = (
                                    os.path.splitext(
                                        file_path
                                    )[1]
                                    .lower()
                                )
                                attachment_type = extension
                                attachment_path = file_path
                                attachments_list.append({
                                    "path": file_path,
                                    "filename": filename,
                                    "type": extension
                                })
                                extracted_text = (
                                    extract_attachment_text(
                                        file_path
                                    )
                                )

                                attachment_text += (
                                    "\n\n"
                                    + extracted_text
                                )

            else:

                try:

                    body = (
                        msg.get_payload(
                            decode=True
                        )
                        .decode(
                            errors="ignore"
                        )
                    )

                except Exception:

                    body = ""

            final_body = (
                body
                + "\n\n"
                + attachment_text
            )

            emails.append(
                {
                    "sender": sender,
                    "subject": subject,
                    "body": final_body,
                    "attachment_type": attachment_type,
                    "attachment_path": attachment_path,
                    "attachments": attachments_list
                }
            )
            mail.store(
                    email_id,
                    '+FLAGS',
                    '\\Seen'
            )
        except Exception as e:

            print(
                f"Email Processing Error: {e}"
            )

    mail.logout()

    return emails


if __name__ == "__main__":

    emails = read_unread_emails()

    print(
        f"\nTotal Valid Emails: {len(emails)}\n"
    )

    for email_data in emails:

        print(
            "\n========================="
        )

        print(
            f"Sender : {email_data['sender']}"
        )

        print(
            f"Subject: {email_data['subject']}"
        )

        print(
            f"Attachment Type : {email_data.get('attachment_type', '')}"
        )

        print(
            f"Attachment Path : {email_data.get('attachment_path', '')}"
        )

        print(
            f"Body:\n{email_data['body']}"
        )

        print(
            "=========================\n"
        )