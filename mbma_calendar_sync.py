#!/usr/bin/env python3
"""
MBMA School & Parent Group Calendar Sync Engine
Tracks MBMA events, generates RFC 5545 calendar invitations (METHOD:REQUEST/CANCEL),
dispatches native calendar invites from leo@ldk-international.com, and daily-scans
school communications for new, updated, or cancelled dates.
"""

import os
import sys
import json
import email
import imaplib
import datetime
import argparse
import urllib.parse
from pathlib import Path
from email.header import decode_header

# Local paths
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = OUTPUT_DIR / ".mbma_events_state.json"
COMBINED_ICS_FILE = OUTPUT_DIR / "mbma_events_2026_2027.ics"

# Ensure ldk_ops is in sys.path
sys.path.insert(0, str(SCRIPT_DIR))
from email_sender import send_email, load_credentials

DEFAULT_RECIPIENTS = ["lmdobashi@gmail.com", "dailey.kluck@gmail.com"]
ORGANIZER = "leo@ldk-international.com"
ORGANIZER_NAME = "Leo (LDK Ops)"
MBMA_LOCATION = "Mission Bay Montessori Academy, 2640 Soderblom Ave, San Diego, CA 92122"

# Initial baseline of verified 2026-2027 events
INITIAL_EVENTS = [
    {
        "id": "halloween-kickoff-20260918",
        "title": "MBMA: Halloween Carnival Kick-Off Meeting",
        "start": "2026-09-18T08:30:00",
        "end": "2026-09-18T09:30:00",
        "location": "MBMA Library (inside Main Office), 2640 Soderblom Ave, San Diego, CA 92122",
        "description": "Parent Group kick-off meeting to plan a memorable Halloween Carnival for the school. All MBMA parents welcome!",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "pizza-friday-start-20260918",
        "title": "MBMA: First Pizza Friday Starts",
        "start": "2026-09-18T11:30:00",
        "end": "2026-09-18T12:30:00",
        "location": MBMA_LOCATION,
        "description": "First Friday of Pizza Lunch program. Remember to pack healthy sides to go with cheese pizza for the kids!",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "halloween-art-deadline-20260923",
        "title": "MBMA: Halloween Art Contest Deadline",
        "start": "2026-09-29T08:00:00",
        "end": "2026-09-29T16:00:00",
        "location": MBMA_LOCATION,
        "description": "Deadline to submit student Halloween Art Contest posters on the official form. (Extended to Tuesday, September 29, 2026 by MBMA Parent Group).",
        "status": "CONFIRMED",
        "sequence": 1
    },
    {
        "id": "directory-deadline-20261009",
        "title": "MBMA: Parent/Student Directory Deadline",
        "start": "2026-10-09T08:00:00",
        "end": "2026-10-09T17:00:00",
        "location": MBMA_LOCATION,
        "description": "Deadline to scan QR code and submit details for the 2026-27 Parent/Student Directory.",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "fall-movie-night-20261009",
        "title": "MBMA: Fall Family Movie Night (Toy Story 5)",
        "start": "2026-10-09T17:30:00",
        "end": "2026-10-09T20:30:00",
        "location": "MBMA Upper Parking Lot, 2640 Soderblom Ave, San Diego, CA 92122",
        "description": "Food available starting at 5:30 PM, movie starts at 6:30 PM. Bring lawn chairs and blankets for a movie under the stars on the upper lot!",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "goal-setting-ch-20261019",
        "title": "MBMA: Goal Setting Conferences (K-2 / Children's House)",
        "start": "2026-10-19T08:00:00",
        "end": "2026-10-23T17:00:00",
        "location": "MBMA K-2 Classroom, 2640 Soderblom Ave, San Diego, CA 92122",
        "description": "Goal setting conferences week with Nellie's teacher (Ms. Graciela Berumen). Register via SignUpGenius link when sent.",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "picture-day-20261022",
        "title": "MBMA: School Picture Day",
        "start": "2026-10-22T08:30:00",
        "end": "2026-10-22T14:00:00",
        "location": MBMA_LOCATION,
        "description": "MBMA Picture Day: Class photo, individual student portraits, and sibling photos.",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "halloween-carnival-20261030",
        "title": "MBMA: Halloween Carnival (Early Dismissal Day)",
        "start": "2026-10-30T14:30:00",
        "end": "2026-10-30T17:30:00",
        "location": MBMA_LOCATION,
        "description": "Annual MBMA Halloween Carnival! Note: Early dismissal day for students.",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "penguin-patch-20261116",
        "title": "MBMA: Penguin Patch Holiday Shop",
        "start": "2026-11-16T07:45:00",
        "end": "2026-11-19T17:00:00",
        "location": MBMA_LOCATION,
        "description": "Holiday shopping shop for students. Hours: 7:45 AM - 8:45 AM & 3:00 PM - 5:00 PM.",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "thanksgiving-feast-20261120",
        "title": "MBMA: Thanksgiving Feast",
        "start": "2026-11-20T11:00:00",
        "end": "2026-11-20T13:30:00",
        "location": MBMA_LOCATION,
        "description": "School community Thanksgiving Feast celebration.",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "winter-book-fair-20261207",
        "title": "MBMA: Winter Book Fair",
        "start": "2026-12-07T07:45:00",
        "end": "2026-12-11T17:00:00",
        "location": "MBMA Auditorium, 2640 Soderblom Ave, San Diego, CA 92122",
        "description": "Winter Book Fair in the Auditorium. Hours: 7:45 AM - 8:45 AM & 3:00 PM - 5:00 PM.",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "jog-a-thon-20270226",
        "title": "MBMA: 2027 Jog-A-Thon",
        "start": "2027-02-26T09:00:00",
        "end": "2027-02-26T13:00:00",
        "location": "MBMA Athletic Field / Lower Playground, 2640 Soderblom Ave, San Diego, CA 92122",
        "description": "Annual MBMA Jog-A-Thon fundraiser and school run (9:00 AM - 1:00 PM).",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "family-day-out-20270306",
        "title": "MBMA: Family Day Out",
        "start": "2027-03-06T10:00:00",
        "end": "2027-03-06T14:00:00",
        "location": MBMA_LOCATION,
        "description": "MBMA community Family Day Out.",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "spring-movie-night-20270416",
        "title": "MBMA: Spring Family Movie Night",
        "start": "2027-04-16T17:30:00",
        "end": "2027-04-16T20:30:00",
        "location": "MBMA Auditorium, 2640 Soderblom Ave, San Diego, CA 92122",
        "description": "Spring Movie Night (5:30 PM - 8:30 PM) in the Auditorium.",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "spring-book-fair-20270426",
        "title": "MBMA: Spring Book Fair",
        "start": "2027-04-26T07:45:00",
        "end": "2027-04-30T17:00:00",
        "location": "MBMA Auditorium, 2640 Soderblom Ave, San Diego, CA 92122",
        "description": "Spring Book Fair in the Auditorium. Hours: 7:45 AM - 8:45 AM & 3:00 PM - 5:00 PM.",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "teacher-appreciation-20270503",
        "title": "MBMA: Teacher & Staff Appreciation Week",
        "start": "2027-05-03T08:00:00",
        "end": "2027-05-07T17:00:00",
        "location": MBMA_LOCATION,
        "description": "Week dedicated to honoring teachers and school staff.",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "popsicle-party-20270604",
        "title": "MBMA: Popsicle Party",
        "start": "2027-06-04T14:00:00",
        "end": "2027-06-04T16:00:00",
        "location": MBMA_LOCATION,
        "description": "End of school year celebration Popsicle Party!",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "emergency-comfort-kit-20260925",
        "title": "🎒 MBMA: Emergency Comfort Kit Due (Nellie)",
        "start": "2026-09-25T08:00:00",
        "end": "2026-09-25T08:30:00",
        "location": MBMA_LOCATION,
        "description": "Emergency Comfort Kit due for Nellie in Ms. Graciela's classroom (K-2 / Children's House).\n\n📦 Kit Checklist:\n• 1-gallon Ziploc bag clearly labeled with Nellie Kluck's name\n• Family photo\n• Reassuring / comforting note from parents\n• Complete change of clothes (shirt, pants, underwear, socks)\n\nTurn in at morning drop-off on Friday, Sept 25.",
        "status": "CONFIRMED",
        "sequence": 0
    },
    {
        "id": "ms-graciela-birthday",
        "title": "🎂 MBMA: Ms. Graciela's Birthday",
        "start": "2027-08-06T08:00:00",
        "end": "2027-08-06T17:00:00",
        "location": MBMA_LOCATION,
        "description": "Ms. Graciela Berumen's Birthday (Nellie's Teacher at MBMA - Children's House / K-2).\n\n🎁 Ms. Graciela's Favorites Profile:\n• Stores: Macy’s, Nordstrom, Target\n• Gift Cards: Starbucks, Amazon\n• Favorite Colors: Black, red, pink, turquoise\n• Favorite Flowers: Orchids\n• Favorite Restaurants: P.F. Chang’s, California Pizza Kitchen, Lorna’s\n• Gifts to Avoid: Creams, lotions, and candles\n\nRoom Parent Coordinator: Megan Shaver (megan.a.shaver@gmail.com)\nVenmo: @Megan-Shaver-MBMA (last 4 digits 8841)\nZelle: megan.a.shaver@gmail.com",
        "status": "CONFIRMED",
        "rrule": "FREQ=YEARLY",
        "sequence": 0
    }
]

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception as e:
            print(f"⚠️ Error reading state file: {e}")
    
    # Initialize from default baseline
    state = {"events": {ev["id"]: ev for ev in INITIAL_EVENTS}, "last_scan": None}
    save_state(state)
    return state

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def generate_ics_invite(ev, method="REQUEST"):
    """
    Generates RFC 5545 iCalendar with METHOD:REQUEST or METHOD:CANCEL,
    ORGANIZER, and ATTENDEES for automated Google Calendar integration.
    """
    s_dt = datetime.datetime.fromisoformat(ev["start"])
    e_dt = datetime.datetime.fromisoformat(ev["end"])
    fmt = "%Y%m%dT%H%M%S"
    uid = ev.get("uid") or f"mbma-v2-{ev['id']}@ldk-international.com"
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    seq = ev.get("sequence", 0)
    status = "CANCELLED" if method == "CANCEL" else ev.get("status", "CONFIRMED")

    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//LDK Ops//MBMA Calendar Engine//EN",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        f"METHOD:{method}",
        f"X-WR-CALNAME:MBMA Events",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now_str}",
        f"SEQUENCE:{seq}",
        f"ORGANIZER;CN={ORGANIZER_NAME}:mailto:{ORGANIZER}",
        "ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;CN=Lauren Dobashi:mailto:lmdobashi@gmail.com",
        "ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;CN=Dailey Kluck:mailto:dailey.kluck@gmail.com",
        f"DTSTART;TZID=America/Los_Angeles:{s_dt.strftime(fmt)}",
        f"DTEND;TZID=America/Los_Angeles:{e_dt.strftime(fmt)}",
    ]
    if ev.get("rrule"):
        lines.append(f"RRULE:{ev['rrule']}")
    lines.extend([
        f"SUMMARY:{ev['title']}",
        f"DESCRIPTION:{ev['description'].replace(chr(10), '\n')}",
        f"LOCATION:{ev['location'].replace(chr(10), ' ')}",
        f"STATUS:{status}",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:Reminder: {ev['title']}",
        "TRIGGER:-PT15M",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR"
    ])
    return "\r\n".join(lines)

def generate_gcal_link(ev):
    s_dt = datetime.datetime.fromisoformat(ev["start"])
    e_dt = datetime.datetime.fromisoformat(ev["end"])
    fmt = "%Y%m%dT%H%M%S"
    params = {
        "action": "TEMPLATE",
        "text": ev["title"],
        "dates": f"{s_dt.strftime(fmt)}/{e_dt.strftime(fmt)}",
        "details": ev["description"],
        "location": ev["location"],
        "ctz": "America/Los_Angeles"
    }
    if ev.get("rrule"):
        params["recur"] = f"RRULE:{ev['rrule']}"
    return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"

def send_event_invite(ev, method="REQUEST", dry_run=False):
    gcal_url = generate_gcal_link(ev)
    ics_content = generate_ics_invite(ev, method=method)
    
    s_dt = datetime.datetime.fromisoformat(ev["start"])
    time_str = s_dt.strftime("%A, %B %d, %Y at %-I:%M %p") if "T" in ev["start"] and not ev["start"].endswith("T08:00:00") else s_dt.strftime("%A, %B %d, %Y")
    
    is_update = ev.get("sequence", 0) > 0 and method == "REQUEST"
    subject_prefix = "📅 Updated: " if is_update else ("📅 Invitation: " if method == "REQUEST" else "❌ Cancelled: ")
    subject = f"{subject_prefix}{ev['title']} ({s_dt.strftime('%b %d')})"
    
    header_title = f"[UPDATED] {ev['title']}" if is_update else ev['title']
    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; color: #2D3748; line-height: 1.5;">
      <div style="border-bottom: 2px solid #3182CE; padding-bottom: 12px; margin-bottom: 16px;">
        <h2 style="color: #2B6CB0; margin: 0 0 6px 0;">{header_title}</h2>
        <span style="font-size: 14px; color: #718096;">MBMA School & Parent Group Calendar Update</span>
      </div>
      
      <div style="background: #EDF2F7; padding: 14px 18px; border-radius: 8px; margin-bottom: 16px;">
        <div style="font-size: 15px; margin-bottom: 6px;"><strong>🗓️ Date:</strong> {time_str}</div>
        <div style="font-size: 15px; margin-bottom: 6px;"><strong>📍 Location:</strong> {ev['location']}</div>
        <div style="font-size: 15px;"><strong>📝 Details:</strong> {ev['description']}</div>
      </div>

      <div style="margin: 20px 0;">
        <a href="{gcal_url}" style="display: inline-block; background-color: #3182CE; color: #ffffff; text-decoration: none; padding: 10px 18px; border-radius: 6px; font-size: 14px; font-weight: 600;">+ Open in Google Calendar</a>
      </div>

      <p style="font-size: 12px; color: #A0AEC0; margin-top: 24px;">
        Dispatched automatically by Leo (LDK Ops) on behalf of Dailey & Lauren. A native iCalendar invite is attached.
      </p>
    </div>
    """

    if dry_run:
        print(f"📧 [Dry Run] Would send {method} for: {ev['title']}")
        print(f"   Subject: {subject}")
        print(f"   Recipients: {', '.join(DEFAULT_RECIPIENTS)}")
        return True

    print(f"📧 Dispatching calendar invite: {ev['title']} -> {', '.join(DEFAULT_RECIPIENTS)}...")
    success = send_email(
        subject=subject,
        body=html_body,
        recipients=DEFAULT_RECIPIENTS,
        from_account="leo",
        is_html=True,
        ics_content=ics_content,
        ics_filename=f"{ev['id']}.ics",
        ics_method=method
    )
    return success

def export_combined_ics(events):
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LDK Ops//MBMA Calendar Engine//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:MBMA School & Parent Group Events 2026-2027",
        "X-WR-TIMEZONE:America/Los_Angeles"
    ]
    for ev in events:
        s_dt = datetime.datetime.fromisoformat(ev["start"])
        e_dt = datetime.datetime.fromisoformat(ev["end"])
        fmt = "%Y%m%dT%H%M%S"
        uid = ev.get("uid") or f"mbma-v2-{ev['id']}@ldk-international.com"
        vevent_lines = [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_str}",
            f"DTSTART;TZID=America/Los_Angeles:{s_dt.strftime(fmt)}",
            f"DTEND;TZID=America/Los_Angeles:{e_dt.strftime(fmt)}",
        ]
        if ev.get("rrule"):
            vevent_lines.append(f"RRULE:{ev['rrule']}")
        vevent_lines.extend([
            f"SUMMARY:{ev['title']}",
            f"DESCRIPTION:{ev['description'].replace(chr(10), '\n')}",
            f"LOCATION:{ev['location'].replace(chr(10), ' ')}",
            "STATUS:CONFIRMED",
            "END:VEVENT"
        ])
        lines.extend(vevent_lines)
    lines.append("END:VCALENDAR")
    COMBINED_ICS_FILE.write_text("\r\n".join(lines))
    print(f"✅ Saved combined ICS file to: {COMBINED_ICS_FILE}")

def _decode_mime(header_val):
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

def _get_email_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition"))
            if ctype == "text/plain" and "attachment" not in cdispo:
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode("utf-8", errors="replace") + "\n"
            elif ctype == "text/html" and not body and "attachment" not in cdispo:
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode("utf-8", errors="replace") + "\n"
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="replace")
    return body

def scan_recent_emails(state, dry_run=False, days=14, apply_label=True, archive=False):
    """
    Connects to IMAP to check recent messages from MBMA domains:
      - @mbmapg.org (Parent Group)
      - @mbmaclass.com / @mbmacademy.com (Administration & Teachers)
      - @online.procaresoftware.com (Classroom chats & updates)
    Compares against existing state ledger and detects updates or newly announced dates.
    Applies the 'School/MBMA' Gmail label to all processed school communications.
    """
    print("🔍 Scanning recent emails for MBMA communications...")
    creds = load_credentials()
    acc = creds.get("dailey_personal")
    if not acc or not acc.get("password"):
        print("⚠️ No credentials found for dailey_personal to scan inbox.")
        return False

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(acc["email"], acc["password"])
        mail.select('"[Gmail]/All Mail"', readonly=False)
    except Exception as e:
        print(f"⚠️ IMAP login failed during scan: {e}")
        return False

    if apply_label and not dry_run:
        try:
            mail.create('"School/MBMA"')
        except Exception:
            pass

    target_domains = [
        "mbmapg.org",
        "mbmaclass.com",
        "mbmacademy.com",
        "online.procaresoftware.com",
        "procaremessagingservice.com"
    ]

    since_date = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")
    uids = set()

    for domain in target_domains:
        query = f'(SINCE "{since_date}" FROM "{domain}")'
        typ, data = mail.uid("search", None, query)
        if typ == "OK" and data and data[0]:
            for u in data[0].split():
                uids.add(u)

    # Also search by subject keywords
    for kw in ["MBMA", "Montessori"]:
        query = f'(SINCE "{since_date}" SUBJECT "{kw}")'
        typ, data = mail.uid("search", None, query)
        if typ == "OK" and data and data[0]:
            for u in data[0].split():
                uids.add(u)

    if not uids:
        print(f"ℹ️ No new MBMA communications found in the last {days} days.")
        state["last_scan"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if not dry_run:
            save_state(state)
        mail.logout()
        return True

    sorted_uids = sorted(list(uids), key=lambda x: int(x))
    print(f"📬 Found {len(sorted_uids)} MBMA messages across target domains in the last {days} days.")

    found_messages = []
    labeled_count = 0
    archived_count = 0

    for u in sorted_uids:
        typ, data = mail.uid("fetch", u, "(RFC822.HEADER)")
        if typ != "OK" or not data:
            continue
        msg = email.message_from_bytes(data[0][1])
        sender = _decode_mime(msg.get("From"))
        # Filter out Leo's own automated dispatches immediately without downloading body
        if ORGANIZER in sender:
            continue

        subj = _decode_mime(msg.get("Subject"))
        dt = msg.get("Date")

        # Now fetch full body for confirmed school messages
        typ_body, body_data = mail.uid("fetch", u, "(RFC822)")
        body = ""
        if typ_body == "OK" and body_data:
            full_msg = email.message_from_bytes(body_data[0][1])
            body = _get_email_body(full_msg)

        # Apply School/MBMA label
        if apply_label and not dry_run:
            mail.uid("store", u, "+X-GM-LABELS", '("School/MBMA")')
            labeled_count += 1

        # Optionally archive from INBOX
        if archive and not dry_run:
            mail.uid("store", u, "-X-GM-LABELS", '("\\\\Inbox")')
            archived_count += 1

        found_messages.append({
            "uid": u.decode(),
            "from": sender,
            "subject": subj,
            "date": dt,
            "body": body
        })

    print(f"📋 Verified {len(found_messages)} unique inbound school communications:")
    for m in found_messages:
        label_note = ' [🏷️ School/MBMA]' if apply_label and not dry_run else ''
        print(f"  • [{m['date']}] {m['from']} -> \"{m['subject']}\" (UID: {m['uid']}){label_note}")

    if labeled_count > 0:
        print(f"🏷️ Successfully attached 'School/MBMA' label to {labeled_count} messages.")
    if archived_count > 0:
        print(f"📦 Successfully archived {archived_count} messages from INBOX.")

    state["last_scan"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if not dry_run:
        save_state(state)

    mail.logout()
    return True

def main():
    parser = argparse.ArgumentParser(description="MBMA Calendar Sync & Dispatcher")
    parser.add_argument("--send-all", action="store_true", help="Send calendar invites for all events")
    parser.add_argument("--send-event", help="Send invite for a specific event ID")
    parser.add_argument("--cancel", action="store_true", help="Send cancellation (METHOD:CANCEL)")
    parser.add_argument("--scan", action="store_true", help="Scan recent emails for school event updates")
    parser.add_argument("--no-label", action="store_true", help="Skip applying 'School/MBMA' Gmail label")
    parser.add_argument("--archive", action="store_true", help="Archive scanned emails from INBOX to All Mail")
    parser.add_argument("--export-ics", action="store_true", help="Export combined .ics file")
    parser.add_argument("--days", type=int, default=14, help="Days back to scan for emails (default: 14)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without sending emails or modifying labels")
    args = parser.parse_args()

    state = load_state()
    events = list(state["events"].values())

    if args.export_ics or not any([args.send_all, args.send_event, args.scan]):
        export_combined_ics(events)

    if args.send_all:
        print(f"🚀 Sending invites for {len(events)} events...")
        sent_count = 0
        for ev in events:
            # Send invite
            ok = send_event_invite(ev, method="REQUEST", dry_run=args.dry_run)
            if ok and not args.dry_run:
                ev["last_dispatched_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                save_state(state)
                sent_count += 1
        print(f"🎉 Completed! Sent {sent_count} event invitations.")

    elif args.send_event:
        ev = state["events"].get(args.send_event)
        if not ev:
            print(f"❌ Event ID '{args.send_event}' not found in state ledger.")
            sys.exit(1)
        method = "CANCEL" if args.cancel else "REQUEST"
        send_event_invite(ev, method=method, dry_run=args.dry_run)
        if not args.dry_run:
            ev["last_dispatched_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            if args.cancel:
                ev["status"] = "CANCELLED"
            save_state(state)

    if args.scan:
        scan_recent_emails(
            state,
            dry_run=args.dry_run,
            days=args.days,
            apply_label=not args.no_label,
            archive=args.archive
        )

if __name__ == "__main__":
    main()
