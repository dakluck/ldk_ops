import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
import os
import argparse
from pathlib import Path

def load_credentials():
    """Loads credentials from .env or ~/.config/himalaya/config.toml."""
    creds = {
        "leo": {
            "email": "leo@ldk-international.com",
            "password": os.environ.get("GMAIL_LEO_PASSWORD", ""),
            "sender_name": "Leo (LDK Ops)"
        },
        "dailey_ldk": {
            "email": "dailey@ldk-international.com",
            "password": os.environ.get("GMAIL_DAILEY_LDK_PASSWORD", ""),
            "sender_name": "Dailey Kluck (LDK International)"
        },
        "dailey_personal": {
            "email": "dailey.kluck@gmail.com",
            "password": os.environ.get("GMAIL_DAILEY_PERSONAL_PASSWORD", ""),
            "sender_name": "Dailey Kluck"
        },
        "dailey_reference": {
            "email": "dailey@thereference.app",
            "password": os.environ.get("GMAIL_DAILEY_REFERENCE_PASSWORD", ""),
            "sender_name": "Dailey Kluck"
        }
    }

    # If passwords are not in env, parse from .env file or himalaya config
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k == "GMAIL_LEO_PASSWORD":
                    creds["leo"]["password"] = v
                elif k == "GMAIL_DAILEY_LDK_PASSWORD":
                    creds["dailey_ldk"]["password"] = v
                elif k == "GMAIL_DAILEY_PERSONAL_PASSWORD":
                    creds["dailey_personal"]["password"] = v
                elif k == "GMAIL_DAILEY_REFERENCE_PASSWORD":
                    creds["dailey_reference"]["password"] = v

    # Fallback to Himalaya config.toml
    himalaya_conf = Path.home() / ".config" / "himalaya" / "config.toml"
    if himalaya_conf.exists() and (not creds["leo"]["password"] or not creds["dailey_ldk"]["password"]):
        try:
            content = himalaya_conf.read_text()
            import re
            for acc_key, acc_id in [("leo", "google"), ("dailey_ldk", "dailey_ldk"), ("dailey_personal", "dailey_personal")]:
                if not creds[acc_key]["password"]:
                    match = re.search(r'\[accounts\.' + acc_id + r'[\s\S]*?raw\s*=\s*"([^"]+)"', content)
                    if match:
                        creds[acc_key]["password"] = match.group(1)
        except Exception:
            pass

    return creds

DEFAULT_RECIPIENTS = ["lmdobashi@gmail.com", "dailey.kluck@gmail.com"]

def send_email(subject, body, recipients=None, from_account="leo", is_html=False, ics_content=None, ics_filename="invite.ics", ics_method="REQUEST", extra_headers=None, attachments=None, inline_images=None):
    """
    Sends an email to specified recipients using configured SMTP credentials.
    Default recipients: ['lmdobashi@gmail.com', 'dailey.kluck@gmail.com']
    Supports native iCalendar invite delivery (default method=REQUEST, or CANCEL) when ics_content is provided.
    Supports file attachments and inline CID embedded images.
    """
    if recipients is None:
        recipients = DEFAULT_RECIPIENTS
    elif isinstance(recipients, str):
        recipients = [r.strip() for r in recipients.split(",") if r.strip()]

    accounts = load_credentials()
    acc = accounts.get(from_account, accounts["leo"])
    sender_email = acc["email"]
    sender_pwd = acc["password"]
    sender_name = acc["sender_name"]

    if not sender_pwd:
        raise ValueError(f"No password found for account {from_account} in .env or himalaya config.")

    if ics_content:
        from email.mime.base import MIMEBase
        from email import encoders

        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = ", ".join(recipients)

        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(body if not is_html else "This email contains an event invitation. Please open in an email client that supports iCalendar.", "plain", "utf-8"))
        if is_html:
            alt_part.attach(MIMEText(body, "html", "utf-8"))

        cal_part = MIMEText(ics_content, f"calendar; method={ics_method}; charset=UTF-8")
        cal_part.add_header("Content-Disposition", f'inline; filename="{ics_filename}"')
        cal_part.add_header("Content-Class", "urn:content-classes:calendarmessage")
        alt_part.attach(cal_part)
        msg.attach(alt_part)

        att_part = MIMEBase("text", "calendar", method=ics_method, name=ics_filename)
        att_part.set_payload(ics_content.encode("utf-8"))
        encoders.encode_base64(att_part)
        att_part.add_header("Content-Disposition", f'attachment; filename="{ics_filename}"')
        att_part.add_header("Content-Class", "urn:content-classes:calendarmessage")
        msg.attach(att_part)
    elif attachments or inline_images:
        from email.mime.image import MIMEImage
        from email.mime.base import MIMEBase
        from email import encoders
        import mimetypes
        import re

        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = ", ".join(recipients)

        if inline_images:
            related_part = MIMEMultipart("related")
            alt_part = MIMEMultipart("alternative")
            if is_html:
                plain_text = re.sub(r'<[^>]+>', ' ', body)
                plain_text = re.sub(r'\s+', ' ', plain_text).strip()
                alt_part.attach(MIMEText(plain_text, "plain", "utf-8"))
                alt_part.attach(MIMEText(body, "html", "utf-8"))
            else:
                alt_part.attach(MIMEText(body, "plain", "utf-8"))
            related_part.attach(alt_part)

            for cid, img_ref in inline_images.items():
                p = Path(img_ref)
                if p.exists():
                    with open(p, "rb") as f:
                        img_data = f.read()
                    subtype = p.suffix.lstrip(".").lower()
                    if subtype == "jpg":
                        subtype = "jpeg"
                    mime_img = MIMEImage(img_data, _subtype=subtype)
                    mime_img.add_header("Content-ID", f"<{cid}>")
                    mime_img.add_header("Content-Disposition", "inline", filename=p.name)
                    related_part.attach(mime_img)
            msg.attach(related_part)
        else:
            alt_part = MIMEMultipart("alternative")
            subtype = "html" if is_html else "plain"
            alt_part.attach(MIMEText(body, subtype, "utf-8"))
            msg.attach(alt_part)

        if attachments:
            for att in attachments:
                p = Path(att)
                if not p.exists():
                    continue
                ctype, encoding = mimetypes.guess_type(str(p))
                if ctype is None or encoding is not None:
                    ctype = "application/octet-stream"
                maintype, subtype = ctype.split("/", 1)
                with open(p, "rb") as f:
                    part = MIMEBase(maintype, subtype)
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{p.name}"')
                msg.attach(part)
    else:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = ", ".join(recipients)

        subtype = "html" if is_html else "plain"
        msg.attach(MIMEText(body, subtype, "utf-8"))

    if extra_headers:
        for hk, hv in extra_headers.items():
            msg[hk] = hv

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender_email, sender_pwd)
        server.sendmail(sender_email, recipients, msg.as_string())
        server.quit()
        print(f"✅ Email successfully sent to: {', '.join(recipients)}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send emails via LDK Ops SMTP")
    parser.add_argument("--to", help="Comma-separated recipients", default="lmdobashi@gmail.com,dailey.kluck@gmail.com")
    parser.add_argument("--subject", required=True, help="Email subject")
    parser.add_argument("--body", required=True, help="Email body")
    parser.add_argument("--from-account", choices=["leo", "dailey_ldk", "dailey_personal"], default="leo")
    parser.add_argument("--html", action="store_true", help="Send as HTML")
    args = parser.parse_args()

    send_email(
        subject=args.subject,
        body=args.body,
        recipients=args.to,
        from_account=args.from_account,
        is_html=args.html
    )
