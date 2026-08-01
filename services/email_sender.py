import smtplib

from email.mime.text import MIMEText

from config import (
    EMAIL,
    APP_PASSWORD
)

def send_registration_email(
    recipient_email
):

    subject = (
        "Procurev Registration Required"
    )

    body = f"""
Dear User,

We received your RFQ request from:

{recipient_email}

However, your email address is not registered in the Procurev Platform.

Please register in the Procurev Portal and then submit your RFQ again.

For support please contact the Procurev Team.

Regards,
Procurev Team
"""

    msg = MIMEText(body)

    msg["Subject"] = subject
    msg["From"] = EMAIL
    msg["To"] = recipient_email

    try:

        server = smtplib.SMTP(
            "smtp.gmail.com",
            587
        )

        server.starttls()

        server.login(
            EMAIL,
            APP_PASSWORD
        )

        server.send_message(
            msg
        )

        server.quit()

        print(
            f"Registration Email Sent: {recipient_email}"
        )

    except Exception as e:

        print(
            f"Email Send Error: {e}"
        )