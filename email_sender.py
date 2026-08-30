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

DEFAULT_RECIPIENTS = ["ldobashi@gmail.com", "dailey.kluck@gmail.com"]

def send_email(subject, body, recipients=None, from_account="leo", is_html=False):
    """
    Sends an email to specified recipients using configured SMTP credentials.
    Default recipients: ['ldobashi@gmail.com', 'dailey.kluck@gmail.com']
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

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = ", ".join(recipients)

    subtype = "html" if is_html else "plain"
    msg.attach(MIMEText(body, subtype, "utf-8"))

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
    parser.add_argument("--to", help="Comma-separated recipients", default="ldobashi@gmail.com,dailey.kluck@gmail.com")
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
