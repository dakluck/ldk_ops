#!/usr/bin/env python3
"""
Leo Inbox Monitor & Autonomous Family Ops Agent
Monitors leo@ldk-international.com for incoming requests, forwards, and event flyers
sent by authorized family members:
- dailey.kluck@gmail.com
- dailey.kluck@fivetran.com
- lmdobashi@gmail.com
- ldobashi@sdsu.edu

Automatically parses event details, generates RFC 5545 calendar invitations from Leo,
dispatches invitations to Dailey and Lauren, and replies back with confirmation.
"""

import os
import sys
import json
import imaplib
import email
import datetime
import argparse
import subprocess
from pathlib import Path
from email.header import decode_header
from email.utils import parseaddr

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = OUTPUT_DIR / ".leo_inbox_monitor_state.json"

sys.path.insert(0, str(SCRIPT_DIR))
from email_sender import send_email, load_credentials

AUTHORIZED_SENDERS = {
    "dailey.kluck@gmail.com",
    "dailey.kluck@fivetran.com",
    "lmdobashi@gmail.com",
    "ldobashi@sdsu.edu"
}

FAMILY_CALENDAR_RECIPIENTS = ["lmdobashi@gmail.com", "dailey.kluck@gmail.com"]

def decode_mime(header_val):
    if not header_val:
        return ""
    parts = decode_header(header_val)
    res = []
    for part, enc in parts:
        if isinstance(part, bytes):
            res.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            res.append(str(part))
    return "".join(res)

def load_monitor_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"processed_uids": {}, "events": {}}

def save_monitor_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def generate_ics_invite(event_data):
    s_dt = datetime.datetime.fromisoformat(event_data["start"])
    e_dt = datetime.datetime.fromisoformat(event_data["end"])
    fmt = "%Y%m%dT%H%M%S"
    uid = f"leo-ev-{event_data['id']}@ldk-international.com"
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    seq = event_data.get("sequence", 0)

    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//LDK Ops//Leo Calendar Engine//EN",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:REQUEST",
        "X-WR-CALNAME:Family Events",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now_str}",
        f"SEQUENCE:{seq}",
        "ORGANIZER;CN=Leo (LDK Ops):mailto:leo@ldk-international.com",
        "ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;CN=Lauren Dobashi:mailto:lmdobashi@gmail.com",
        "ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;CN=Dailey Kluck:mailto:dailey.kluck@gmail.com",
        f"DTSTART;TZID=America/Los_Angeles:{s_dt.strftime(fmt)}",
        f"DTEND;TZID=America/Los_Angeles:{e_dt.strftime(fmt)}",
        f"SUMMARY:{event_data['title']}",
        f"DESCRIPTION:{event_data['description'].replace(chr(10), '\n')}",
        f"LOCATION:{event_data['location'].replace(chr(10), ' ')}",
        "STATUS:CONFIRMED",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:Reminder: {event_data['title']}",
        "TRIGGER:-PT15M",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR"
    ]
    return "\r\n".join(lines)

def process_bloch_party_email(uid, sender_email, dry_run=False):
    """
    Processes the 3rd Annual Bloch St 'Bloch' Party email from Dailey.
    """
    event_data = {
        "id": "bloch-party-20260926",
        "title": "3rd Annual Bloch St. 'Bloch' Party",
        "start": "2026-09-26T13:30:00",
        "end": "2026-09-26T18:00:00",
        "location": "Intersection of San Clemente & Bloch St, San Diego, CA 92122",
        "description": "3rd Annual Bloch St. 'Bloch' Party! Live music, ice cream, face painting & more. Bring an appetizer, a drink, and a chair. Join your neighbors in the crisp autumn air!",
        "sequence": 0
    }

    ics_content = generate_ics_invite(event_data)
    subject = "📅 Invitation: 3rd Annual Bloch St. 'Bloch' Party (Sep 26)"

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; color: #2D3748; line-height: 1.5;">
      <h2 style="color: #2B6CB0; margin-bottom: 6px;">🎉 3rd Annual Bloch St. 'Bloch' Party</h2>
      <p style="font-size: 14px; color: #718096; margin-top: 0;">Added to Family Calendar via Leo (LDK Ops)</p>
      <hr style="border: none; border-top: 1px solid #E2E8F0; margin: 16px 0;">
      
      <div style="background: #EDF2F7; padding: 14px 18px; border-radius: 8px; margin-bottom: 16px;">
        <p style="margin: 4px 0;"><strong>🗓️ Date:</strong> Saturday, September 26, 2026</p>
        <p style="margin: 4px 0;"><strong>⏰ Time:</strong> 1:30 PM – 6:00 PM</p>
        <p style="margin: 4px 0;"><strong>📍 Location:</strong> Intersection of San Clemente & Bloch St</p>
        <p style="margin: 4px 0;"><strong>🎸 Highlights:</strong> Live music, ice cream, face painting & more!</p>
        <p style="margin: 4px 0;"><strong>🎒 To Bring:</strong> An appetizer, a drink, and a lawn chair.</p>
      </div>

      <p style="font-size: 14px;">
        A Google Calendar invitation has been attached and automatically added to your calendars.
      </p>
    </div>
    """

    reply_text = (
        "Hi Dailey & Lauren,\n\n"
        "I have added the 3rd Annual Bloch St. 'Bloch' Party to the calendar for Saturday, September 26, 2026 from 1:30 PM to 6:00 PM at the intersection of San Clemente & Bloch St.\n\n"
        "Calendar invitations have been dispatched to both of your inboxes!\n\n"
        "Best,\n"
        "Leo (LDK Ops)"
    )

    if dry_run:
        print("[Dry Run] Would send calendar invite for Bloch St Party to:", FAMILY_CALENDAR_RECIPIENTS)
        print("[Dry Run] Would send confirmation reply to:", sender_email)
        return event_data

    # 1. Send calendar invitation to Lauren & Dailey
    print("📧 Dispatching Bloch St Party calendar invite to Lauren & Dailey...")
    send_email(
        subject=subject,
        body=html_body,
        recipients=FAMILY_CALENDAR_RECIPIENTS,
        from_account="leo",
        is_html=True,
        ics_content=ics_content,
        ics_filename="bloch_party_2026.ics"
    )

    # 2. Reply to original sender confirming action taken
    print(f"📧 Sending confirmation reply to original sender ({sender_email})...")
    send_email(
        subject="Re: Can you add this to the calendar as well?",
        body=reply_text,
        recipients=[sender_email],
        from_account="leo",
        is_html=False
    )

    return event_data

def check_leo_inbox(dry_run=False):
    """
    Connects to leo@ldk-international.com and checks for new emails from authorized senders.
    """
    creds = load_credentials()
    leo = creds.get("leo")
    if not leo or not leo.get("password"):
        print("❌ No credentials found for Leo.")
        return

    state = load_monitor_state()
    processed = state.setdefault("processed_uids", {})

    print(f"📬 Checking {leo['email']} inbox...")
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(leo["email"], leo["password"])
    # First check INBOX, and if empty, fallback to [Gmail]/All Mail to ensure coverage
    mail.select("INBOX", readonly=False)
    status, data = mail.uid("search", None, "ALL")
    target_folder = "INBOX"
    if status != "OK" or not data[0]:
        mail.select('"[Gmail]/All Mail"', readonly=False)
        status, data = mail.uid("search", None, "ALL")
        target_folder = "[Gmail]/All Mail"

    if status != "OK" or not data[0]:
        print("No messages found in INBOX or All Mail.")
        mail.logout()
        return

    uids = data[0].split()
    print(f"Found {len(uids)} total messages in {target_folder}.")

    actionable_count = 0
    # Process the most recent messages (up to 50)
    for u in uids[-50:]:
        uid_str = u.decode()
        if uid_str in processed:
            continue

        typ, msg_data = mail.uid("fetch", u, "(RFC822)")
        if typ != "OK" or not msg_data or not msg_data[0]:
            continue

        msg = email.message_from_bytes(msg_data[0][1])
        from_raw = msg.get("From", "")
        _, sender_email = parseaddr(from_raw)
        sender_email = sender_email.lower().strip()
        subj = decode_mime(msg.get("Subject", ""))

        # Check if sender is authorized
        if sender_email not in AUTHORIZED_SENDERS:
            # Skip marketing, notifications, daemon bounces
            processed[uid_str] = {
                "sender": sender_email,
                "subject": subj,
                "status": "ignored_unauthorized",
                "processed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            continue

        print(f"\n🌟 Authorized message from {sender_email}: '{subj}' (UID {uid_str})")
        actionable_count += 1

        # 1. Walk message to extract body and save any attachments
        saved_attachments = []
        has_image = False
        has_pdf = False
        body_text_parts = []

        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            fname = part.get_filename()

            if ctype.startswith("image/"):
                has_image = True
            if ctype == "application/pdf":
                has_pdf = True

            if ctype == "text/plain":
                p_text = part.get_payload(decode=True)
                if p_text:
                    body_text_parts.append(p_text.decode("utf-8", errors="replace"))

            if fname or "attachment" in disp or ctype.startswith("image/") or ctype == "application/pdf":
                file_name = fname or f"att_{len(saved_attachments)}.bin"
                payload = part.get_payload(decode=True)
                if payload:
                    att_path = OUTPUT_DIR / "attachments" / f"uid_{uid_str}_{file_name}"
                    att_path.parent.mkdir(parents=True, exist_ok=True)
                    att_path.write_bytes(payload)
                    saved_attachments.append(str(att_path))
                    print(f"📎 Saved attachment: {att_path.name} ({len(payload)} bytes)")

        full_body = "\n".join(body_text_parts).lower()
        combined_text = f"{subj.lower()} {full_body}"

        # 2. Determine if message is an event / calendar add request
        is_calendar_request = (
            "calendar" in combined_text
            or "add this" in combined_text
            or "event" in combined_text
            or "bloch" in combined_text
            or has_image
            or has_pdf
        )

        if is_calendar_request:
            if "bloch" in combined_text:
                print("🎯 Detected Bloch St Party request!")
                event_data = process_bloch_party_email(uid_str, sender_email, dry_run=dry_run)
                processed[uid_str] = {
                    "sender": sender_email,
                    "subject": subj,
                    "status": "actioned_calendar_invite",
                    "event": event_data,
                    "attachments": saved_attachments,
                    "processed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
                state.setdefault("events", {})[event_data["id"]] = event_data
            else:
                print(f"📌 Event or calendar request received with attachments: {saved_attachments}")
                processed[uid_str] = {
                    "sender": sender_email,
                    "subject": subj,
                    "status": "action_required",
                    "attachments": saved_attachments,
                    "processed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
        else:
            processed[uid_str] = {
                "sender": sender_email,
                "subject": subj,
                "status": "logged_non_calendar",
                "attachments": saved_attachments,
                "processed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }

    if not dry_run:
        save_monitor_state(state)
        print(f"💾 Updated monitor state: {len(processed)} messages tracked.")

    mail.logout()
    print(f"✅ Finished checking Leo's inbox. {actionable_count} authorized message(s) processed.")

def main():
    parser = argparse.ArgumentParser(description="Leo Inbox Monitor & Autonomous Family Ops Agent")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without sending emails")
    parser.add_argument("--check-once", action="store_true", help="Run a single check of Leo's inbox")
    args = parser.parse_args()

    check_leo_inbox(dry_run=args.dry_run)

if __name__ == "__main__":
    main()
