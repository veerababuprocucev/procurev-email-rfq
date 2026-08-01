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

            if msg.is_multipart():

                for part in msg.walk():

                    content_type = (
                        part.get_content_type()
                    )

                    filename = (
                        part.get_filename()
                    )

                    # Email Body

                    if (
                        content_type
                        == "text/plain"
                        and not filename
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

                    if filename:

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

                            f.write(
                                part.get_payload(
                                    decode=True
                                )
                            )
                        
                        extension = (
                            os.path.splitext(
                                file_path
                            )[1]
                            .lower()
                        )
                        attachment_type = extension
                        attachment_path = file_path
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
                    "attachment_path": attachment_path
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