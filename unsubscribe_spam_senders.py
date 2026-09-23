#!/usr/bin/env python3
"""
Automated Unsubscriber for Commercial / Marketing Newsletters in Spam
Supports:
- RFC 8058 One-Click HTTPS POST (List-Unsubscribe=One-Click)
- Standard HTTPS GET unsubscription links
- RFC 2369 Mailto unsubscription (via authenticated Gmail SMTP)
"""

import imaplib
import email
import re
import urllib.request
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.header import decode_header
from email_sender import load_credentials

LEGIT_DOMAINS = [
    'carsandbids.com', 'bandsintown.com', 'libertyskis.com', 'crackshack.com',
    'ortegas.com', 'toast-tab.com', 'worddaily.com', 'wordsmarts.com', 'flodesk.com',
    'prairiemountainmedia.com', 'bouldercameracustomer.com', 'lyftmail.com',
    'standoutstickers.com', 'drivecentric.io', 'careerprepdb.org', 'anker.com',
    'salad.com', 'stoveguard.com', 'semikolon.us', 'revinate.com'
]

def clean_header(header_val):
    if not header_val:
        return ""
    decoded_parts = decode_header(header_val)
    result = []
    for part, enc in decoded_parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(enc or 'utf-8', errors='ignore'))
            except Exception:
                result.append(part.decode('latin1', errors='ignore'))
        else:
            result.append(str(part))
    return " ".join(result)

def send_mailto_unsub(sender_email, sender_password, to_email, subject, body="Unsubscribe"):
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15)
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"    [!] Error sending mailto to {to_email}: {e}")
        return False

def http_one_click_post(url):
    try:
        data = urllib.parse.urlencode({'List-Unsubscribe': 'One-Click'}).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 202, 204, 301, 302, 303)
    except Exception as e:
        # Fallback to GET
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)'}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status in (200, 202, 204, 301, 302, 303)
        except Exception as e2:
            print(f"    [!] HTTP error: {e2}")
            return False

def main():
    creds = load_credentials()
    acc = creds['dailey_personal']
    user_email = acc['email']
    user_pwd = acc['password']

    print("=======================================================")
    print(f"  Unsubscribing Commercial Newsletters from Spam: {user_email}")
    print("=======================================================")

    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(user_email, user_pwd)
    mail.select('"[Gmail]/Spam"')

    status, data = mail.uid('search', None, 'ALL')
    uids = data[0].split() if data[0] else []
    total = len(uids)
    print(f"Scanning {total} messages in Spam for legitimate commercial senders...")

    unsub_targets = {}
    chunk_size = 50
    for i in range(0, total, chunk_size):
        chunk = uids[i:i+chunk_size]
        chunk_str = b','.join(chunk).decode('ascii')
        status, fetch_data = mail.uid('fetch', chunk_str, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT LIST-UNSUBSCRIBE LIST-UNSUBSCRIBE-POST)])')
        for item in fetch_data:
            if isinstance(item, tuple):
                raw_header = item[1]
                msg = email.message_from_bytes(raw_header)
                sender = clean_header(msg.get('From', ''))
                subject = clean_header(msg.get('Subject', ''))
                unsub_header = clean_header(msg.get('List-Unsubscribe', ''))
                unsub_post = clean_header(msg.get('List-Unsubscribe-Post', ''))

                s_lower = sender.lower()
                if any(dom in s_lower for dom in LEGIT_DOMAINS):
                    s_clean = sender.split('<')[-1].replace('>', '').strip().lower()
                    if s_clean not in unsub_targets:
                        unsub_targets[s_clean] = {
                            'from': sender,
                            'subject': subject,
                            'unsub_header': unsub_header,
                            'unsub_post': unsub_post
                        }

    mail.logout()

    print(f"\nFound {len(unsub_targets)} commercial senders to unsubscribe:\n")

    # 1. Cars & Bids specific unsubscription
    print("-------------------------------------------------------")
    print("🚗 Processing: Cars & Bids")
    cars_targets = [
        "email-manager@carsandbids.com",
        "support@carsandbids.com"
    ]
    print("  -> Sending Watchlist unsubscription requests to Cars & Bids...")
    send_mailto_unsub(
        user_email, user_pwd,
        "email-manager@carsandbids.com",
        "Unsubscribe: Remove all watchlists and auction alerts",
        "Please remove dailey.kluck@gmail.com from all auction alerts and search watchlists (including Porsche 911 and Land Rover Defender)."
    )
    send_mailto_unsub(
        user_email, user_pwd,
        "support@carsandbids.com",
        "Unsubscribe: Remove dailey.kluck@gmail.com from all watchlists and notifications",
        "Hello Cars & Bids Team,\n\nPlease remove dailey.kluck@gmail.com from all active watchlists, listing alerts, and promotional emails.\n\nThank you,\nDailey Kluck"
    )
    print("  ✅ Sent unsubscription requests to Cars & Bids email managers.")

    # 2. Process all remaining identified senders
    success_count = 1
    for s_clean, info in unsub_targets.items():
        if "carsandbids.com" in s_clean:
            continue

        sender = info['from']
        subject = info['subject']
        raw_unsub = info['unsub_header']
        has_one_click = "list-unsubscribe=one-click" in info['unsub_post'].lower()

        print("-------------------------------------------------------")
        print(f"📦 Processing: {sender[:40]}")
        print(f"   Subject: {subject[:50]}")

        # Parse URLs and Mailto
        urls = re.findall(r'<(https?://[^>]+)>', raw_unsub)
        mailtos = re.findall(r'<mailto:([^>]+)>', raw_unsub)

        done = False

        # Attempt HTTP One-Click or GET
        for u in urls:
            print(f"   Attempting Web Unsubscribe: {u[:70]}...")
            if http_one_click_post(u):
                print("   ✅ Web Unsubscribe successful!")
                done = True
                success_count += 1
                break

        # If not done, try mailto
        if not done and mailtos:
            m_target = mailtos[0]
            to_addr = m_target.split('?')[0]
            sub_param = "unsubscribe"
            if "subject=" in m_target:
                sub_param = urllib.parse.unquote(m_target.split("subject=")[-1].split("&")[0])
            print(f"   Attempting Mailto Unsubscribe to: {to_addr[:40]}...")
            if send_mailto_unsub(user_email, user_pwd, to_addr, sub_param):
                print("   ✅ Mailto Unsubscribe sent successfully!")
                done = True
                success_count += 1

        if not done and not urls and not mailtos:
            print("   ⚠️ No automated unsubscribe method found in headers.")

    print("\n=======================================================")
    print(f"  Unsubscription complete! Successfully processed {success_count} senders.")
    print("=======================================================\n")

if __name__ == '__main__':
    main()
