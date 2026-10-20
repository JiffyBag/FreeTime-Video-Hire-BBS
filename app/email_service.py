import os
import aiosmtplib
from email.message import EmailMessage

SMTP_HOST = os.environ.get("SMTP_HOST", "mail")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "1025"))
FROM_ADDR = "noreply@mail.freetime.video"


async def send_reset_email(to_email: str, reset_link: str):
    msg = EmailMessage()
    msg["From"] = FROM_ADDR
    msg["To"] = to_email
    msg["Subject"] = "FreeTime Video Hire - Password Reset"
    msg.set_content(
        f"Be Kind, Rewind!\n\n"
        f"A password reset was requested for your FreeTime Video Hire BBS account.\n"
        f"Click the link below (valid 15 minutes):\n\n{reset_link}\n\n"
        f"If you didn't request this, ignore this message.\n"
    )
    await aiosmtplib.send(msg, hostname=SMTP_HOST, port=SMTP_PORT)
