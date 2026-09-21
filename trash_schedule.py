#!/usr/bin/env python3
"""
Trash Schedule Engine for 5522 Bloch St, San Diego, CA 92122
Integrates with City of San Diego Environmental Services Department (Get It Done portal),
Google Calendar API (pushing to Family Calendar via OAuth or service account), and reMarkable Daily Folio.
"""

import os
import sys
import json
import re
import datetime
import argparse
import urllib.parse
import urllib.request
import subprocess
from pathlib import Path

# Base paths
SCRIPT_DIR = Path(__file__).resolve().parent
SERVICE_ACCOUNT_FILE = SCRIPT_DIR / "service_account.json"
TOKEN_FILE = SCRIPT_DIR / ".google_calendar_token.json"
CACHE_FILE = SCRIPT_DIR / ".trash_schedule_cache.json"
OUTPUT_DIR = SCRIPT_DIR / "output"

PORTAL_URL = "https://share.google/ka7L03pH1gIQS9Zy9"
ADDRESS = "5522 BLOCH ST, San Diego, CA 92122"

# Known anchor date for biweekly recycling (Schedule CL-1 / Zone B)
# 2026-09-21 is confirmed recycling pickup
RECYCLING_ANCHOR_MONDAY = datetime.date(2026, 9, 21)

def is_city_holiday(d: datetime.date) -> bool:
    """
    Checks if a date is an official City of San Diego trash holiday.
    Observed holidays that shift collection by 1 day:
    - New Year's Day (Jan 1)
    - Memorial Day (Last Monday in May)
    - Independence Day (July 4)
    - Labor Day (First Monday in Sept)
    - Thanksgiving Day (4th Thursday in Nov)
    - Christmas Day (Dec 25)
    """
    month, day = d.month, d.day
    if month == 1 and day == 1:
        return True
    if month == 7 and day == 4:
        return True
    if month == 12 and day == 25:
        return True
    
    # Memorial Day: last Monday of May
    if month == 5 and d.weekday() == 0 and day >= 25:
        return True
    
    # Labor Day: first Monday of September
    if month == 9 and d.weekday() == 0 and day <= 7:
        return True
    
    # Thanksgiving: 4th Thursday in November
    if month == 11 and d.weekday() == 3 and 22 <= day <= 28:
        return True
        
    return False

def scrape_live_schedule():
    """
    Attempts to fetch live schedule details from the San Diego portal.
    Falls back gracefully if network or sandbox restrictions prevent it.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (X-UA-Compatible; ldk-ops/1.0; +https://ldk-international.com)"
    }
    
    html_text = ""
    try:
        proc = subprocess.run(
            ["curl", "-sL", "--max-time", "6", PORTAL_URL],
            capture_output=True,
            text=True
        )
        if proc.returncode == 0 and len(proc.stdout) > 200:
            html_text = proc.stdout
    except Exception:
        pass
    
    if not html_text:
        try:
            req = urllib.request.Request(PORTAL_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                html_text = resp.read().decode("utf-8", errors="ignore")
        except Exception:
            pass

    if not html_text and CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            pass

    if html_text:
        data = {
            "address": ADDRESS,
            "url": PORTAL_URL,
            "updated_at": datetime.datetime.now().isoformat()
        }
        
        trash_m = re.search(r'Trash[\s\S]*?(\d{2}/\d{2}/\d{4})', html_text, re.IGNORECASE)
        recyc_m = re.search(r'Recyclables[\s\S]*?(\d{2}/\d{2}/\d{4})', html_text, re.IGNORECASE)
        organ_m = re.search(r'Organics[\s\S]*?(\d{2}/\d{2}/\d{4})', html_text, re.IGNORECASE)
        
        if trash_m:
            data["next_trash"] = trash_m.group(1)
        if recyc_m:
            data["next_recycling"] = recyc_m.group(1)
        if organ_m:
            data["next_organics"] = organ_m.group(1)
            
        if "next_trash" in data:
            CACHE_FILE.write_text(json.dumps(data, indent=2))
            return data

    return None

def get_upcoming_schedule(target_date: datetime.date = None):
    """
    Determines the trash schedule for the upcoming/current collection week.
    If target_date is Sunday or Monday, gives the schedule for that immediate collection.
    If target_date is Tuesday-Saturday, gives the schedule for the coming Sunday/Monday.
    """
    if target_date is None:
        target_date = datetime.date.today()

    weekday = target_date.weekday() # 0 = Monday, 6 = Sunday

    if weekday == 0:
        collection_monday = target_date
        staging_sunday = collection_monday - datetime.timedelta(days=1)
    elif weekday == 6:
        staging_sunday = target_date
        collection_monday = staging_sunday + datetime.timedelta(days=1)
    else:
        days_ahead = (7 - weekday) % 7
        staging_sunday = target_date + datetime.timedelta(days=days_ahead)
        collection_monday = staging_sunday + datetime.timedelta(days=1)

    # Check holiday shift
    collection_date = collection_monday
    holiday_delayed = False
    if is_city_holiday(staging_sunday) or is_city_holiday(collection_monday):
        collection_date = collection_monday + datetime.timedelta(days=1)
        holiday_delayed = True

    # Calculate biweekly recycling
    diff_days = (collection_monday - RECYCLING_ANCHOR_MONDAY).days
    diff_weeks = diff_days // 7
    is_recycling_week = (diff_weeks % 2 == 0)

    # Cross-check live scrape if available
    live_data = scrape_live_schedule()
    if live_data and "next_recycling" in live_data:
        try:
            live_recyc_dt = datetime.datetime.strptime(live_data["next_recycling"], "%m/%d/%Y").date()
            if live_recyc_dt == collection_monday:
                is_recycling_week = True
            elif abs((live_recyc_dt - collection_monday).days) < 7:
                is_recycling_week = (live_recyc_dt == collection_monday)
        except Exception:
            pass

    bins = [
        {"name": "Trash", "color": "Black", "icon": "🗑️", "notes": "Landfill waste"},
        {"name": "Organics", "color": "Green", "icon": "🌱", "notes": "Food scraps & yard waste"}
    ]
    if is_recycling_week:
        bins.append({"name": "Recyclables", "color": "Blue", "icon": "♻️", "notes": "Paper, cardboard, plastic, bottles & cans"})

    bin_names = [b["color"] for b in bins]
    bin_summary = " + ".join(bin_names)
    
    title = f"🗑️ Put Out Bins: {bin_summary}"
    if is_recycling_week:
        title += " (Recycling Week!)"

    return {
        "target_date": target_date.isoformat(),
        "staging_sunday": staging_sunday.isoformat(),
        "collection_date": collection_date.isoformat(),
        "collection_day_name": collection_date.strftime("%A"),
        "holiday_delayed": holiday_delayed,
        "is_recycling_week": is_recycling_week,
        "bins": bins,
        "bin_summary": bin_summary,
        "title": title,
        "address": ADDRESS
    }

def generate_gcal_link(sched: dict):
    """Generates a 1-click web URL to add the event to Google Calendar."""
    staging_dt = datetime.datetime.strptime(sched["staging_sunday"], "%Y-%m-%d")
    start_dt = datetime.datetime.combine(staging_dt, datetime.time(19, 0)) # 7:00 PM Sunday
    end_dt = datetime.datetime.combine(staging_dt, datetime.time(19, 30))

    fmt = "%Y%m%dT%H%M%S"
    
    bin_desc = "\n".join([f"• {b['color']} ({b['name']}): {b['notes']}" for b in sched["bins"]])
    details = (
        f"City of San Diego Trash Collection for {sched['address']}.\n\n"
        f"Bins to put out tonight:\n{bin_desc}\n\n"
        f"Collection Day: {sched['collection_day_name']}, {sched['collection_date']} (by 6:00 AM)\n"
        f"{'⚠️ Holiday Delay: Collection shifted by 1 day.\n' if sched['holiday_delayed'] else ''}\n"
        f"Official Portal: {PORTAL_URL}"
    )

    params = {
        "action": "TEMPLATE",
        "text": sched["title"],
        "dates": f"{start_dt.strftime(fmt)}/{end_dt.strftime(fmt)}",
        "details": details,
        "location": sched["address"]
    }
    return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"

def generate_ics_content(sched: dict):
    """Generates RFC 5545 iCalendar format for direct import."""
    staging_dt = datetime.datetime.strptime(sched["staging_sunday"], "%Y-%m-%d")
    start_dt = datetime.datetime.combine(staging_dt, datetime.time(19, 0))
    end_dt = datetime.datetime.combine(staging_dt, datetime.time(19, 30))
    
    fmt = "%Y%m%dT%H%M%S"
    uid = f"trash-bloch-{sched['staging_sunday']}@ldk-international.com"
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    bin_desc = "\\n".join([f"- {b['color']} ({b['name']}): {b['notes']}" for b in sched["bins"]])
    
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LDK Ops//Trash Schedule Engine//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now_str}",
        f"DTSTART;TZID=America/Los_Angeles:{start_dt.strftime(fmt)}",
        f"DTEND;TZID=America/Los_Angeles:{end_dt.strftime(fmt)}",
        f"SUMMARY:{sched['title']}",
        f"DESCRIPTION:Bins to roll out:\\n{bin_desc}\\n\\nCollection: {sched['collection_day_name']} {sched['collection_date']}",
        f"LOCATION:{sched['address']}",
        "STATUS:CONFIRMED",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "DESCRIPTION:Reminder: Put out trash bins",
        "TRIGGER:-PT0M",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR"
    ]
    return "\r\n".join(ics_lines)

def generate_calendar_invite_ics(sched: dict, organizer="leo@ldk-international.com"):
    """
    Generates RFC 5545 iCalendar with METHOD:REQUEST, ORGANIZER, and ATTENDEES.
    When delivered to Gmail, Google Calendar automatically detects this and adds
    the event directly to Lauren's and Dailey's Google Calendars!
    """
    staging_dt = datetime.datetime.strptime(sched["staging_sunday"], "%Y-%m-%d")
    start_dt = datetime.datetime.combine(staging_dt, datetime.time(19, 0)) # 7:00 PM Sunday
    end_dt = datetime.datetime.combine(staging_dt, datetime.time(19, 30))

    fmt = "%Y%m%dT%H%M%S"
    uid = f"trash-bloch-{sched['staging_sunday']}@ldk-international.com"
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    bin_desc = "\\n".join([f"• {b['color']} ({b['name']}): {b['notes']}" for b in sched["bins"]])
    details = (
        f"City of San Diego Trash & Recycling Collection for {sched['address']}.\\n\\n"
        f"Bins to put out tonight:\\n{bin_desc}\\n\\n"
        f"Collection Day: {sched['collection_day_name']}, {sched['collection_date']} (by 6:00 AM)\\n"
        f"{'⚠️ Holiday Delay: Collection shifted by 1 day.\\n' if sched['holiday_delayed'] else ''}\\n"
        f"Official Portal: {PORTAL_URL}"
    )

    ics_lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//LDK Ops//Trash Schedule Engine//EN",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:REQUEST",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now_str}",
        f"ORGANIZER;CN=Leo (LDK Ops):mailto:{organizer}",
        "ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;CN=Lauren Dobashi:mailto:lmdobashi@gmail.com",
        "ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;CN=Dailey Kluck:mailto:dailey.kluck@gmail.com",
        f"DTSTART;TZID=America/Los_Angeles:{start_dt.strftime(fmt)}",
        f"DTEND;TZID=America/Los_Angeles:{end_dt.strftime(fmt)}",
        f"SUMMARY:{sched['title']}",
        f"DESCRIPTION:{details}",
        f"LOCATION:{sched['address']}",
        "STATUS:CONFIRMED",
        "SEQUENCE:0",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "DESCRIPTION:Reminder: Put out trash bins",
        "TRIGGER:-PT0M",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR"
    ]
    return "\r\n".join(ics_lines)

def send_trash_invite(sched: dict, dry_run: bool = False):
    """
    Dispatches a native Google Calendar invitation email from Leo to Lauren & Dailey.
    """
    from email_sender import send_email

    gcal_url = generate_gcal_link(sched)
    ics_invite = generate_calendar_invite_ics(sched)

    subject = f"{sched['title']} ({sched['collection_day_name']} Pickup)"

    bin_badges = ""
    for b in sched["bins"]:
        bg = "#2D3748" if b["color"] == "Black" else ("#2F855A" if b["color"] == "Green" else "#2B6CB0")
        bin_badges += f"""
        <div style="background: {bg}; color: #ffffff; padding: 10px 14px; border-radius: 8px; margin-bottom: 8px; font-weight: 500;">
          <span style="font-size: 16px;">{b['icon']} <strong>{b['color']} Bin:</strong> {b['name']}</span>
          <div style="font-size: 13px; opacity: 0.9; margin-top: 2px;">{b['notes']}</div>
        </div>
        """

    if sched["is_recycling_week"]:
        note_recycling = "<p style='font-size: 14px; color: #2B6CB0; font-weight: 600; margin: 12px 0;'>⭐ Recycling week: Blue bin goes out tonight with Trash and Organics!</p>"
    else:
        note_recycling = "<p style='font-size: 13px; color: #718096; margin: 12px 0;'>ℹ️ Recycling is next week — leave the blue bin in tonight.</p>"

    holiday_alert = ""
    if sched["holiday_delayed"]:
        holiday_alert = "<div style='background: #FFF5F5; border-left: 4px solid #E53E3E; padding: 10px 14px; border-radius: 4px; color: #C53030; font-size: 14px; margin-bottom: 14px;'>⚠️ <strong>Holiday Delay:</strong> City pickup shifted by 1 day!</div>"

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; color: #2D3748; line-height: 1.5;">
      <h2 style="color: #2B6CB0; margin-bottom: 4px;">🗑️ Trash & Recycling Staging Reminder</h2>
      <p style="font-size: 14px; color: #718096; margin-top: 0;">5522 Bloch St, San Diego, CA 92122 &bull; Automated Dispatch from Leo</p>
      <hr style="border: none; border-top: 1px solid #E2E8F0; margin: 16px 0;">
      
      {holiday_alert}

      <p style="font-size: 15px; margin-bottom: 16px;">
        Curbside pickup is tomorrow (<strong>{sched['collection_day_name']}, {sched['collection_date']}</strong> by 6:00 AM).
        Please roll out the bins tonight at <strong>7:00 PM</strong>:
      </p>

      {bin_badges}
      {note_recycling}

      <div style="margin: 24px 0 16px 0;">
        <a href="{gcal_url}" style="display: inline-block; background-color: #3182CE; color: #ffffff; text-decoration: none; padding: 10px 18px; border-radius: 6px; font-size: 14px; font-weight: 600;">+ Add to Google Calendar</a>
      </div>

      <p style="font-size: 12px; color: #A0AEC0; margin-top: 24px;">
        A native calendar invitation is attached to this email and automatically added to your Google Calendar.
      </p>
    </div>
    """

    if dry_run:
        print(f"📧 [Dry Run] Subject: {subject}")
        print("   Recipients: lmdobashi@gmail.com, dailey.kluck@gmail.com")
        print("   From: Leo (LDK Ops) <leo@ldk-international.com>")
        print("   Attachment: trash_staging.ics (METHOD:REQUEST)")
        return True

    print(f"📧 Dispatching calendar invite email to Lauren & Dailey...")
    success = send_email(
        subject=subject,
        body=html_body,
        recipients=["lmdobashi@gmail.com", "dailey.kluck@gmail.com"],
        from_account="leo",
        is_html=True,
        ics_content=ics_invite,
        ics_filename="trash_staging.ics"
    )
    return success

def get_access_token():
    """
    Resolves a valid Google OAuth access token.
    Prioritizes .google_calendar_token.json (refreshing if needed),
    then falls back to service_account.json.
    """
    if TOKEN_FILE.exists():
        try:
            token_data = json.loads(TOKEN_FILE.read_text())
            refresh_token = token_data.get("refresh_token")
            client_id = token_data.get("client_id")
            client_secret = token_data.get("client_secret")
            token_uri = token_data.get("token_uri", "https://oauth2.googleapis.com/token")

            # Refresh token to get fresh access token
            data = urllib.parse.urlencode({
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }).encode("utf-8")
            req = urllib.request.Request(token_uri, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                refreshed = json.loads(resp.read().decode("utf-8"))
                new_access_token = refreshed.get("access_token")
                token_data["access_token"] = new_access_token
                TOKEN_FILE.write_text(json.dumps(token_data, indent=2))
                return new_access_token
        except Exception as e:
            print(f"⚠️ Error refreshing OAuth token from {TOKEN_FILE.name}: {e}")

    # Fallback to service account if valid
    if SERVICE_ACCOUNT_FILE.exists():
        try:
            from google.oauth2 import service_account
            import google.auth.transport.requests
            creds = service_account.Credentials.from_service_account_file(
                str(SERVICE_ACCOUNT_FILE),
                scopes=["https://www.googleapis.com/auth/calendar"]
            )
            req = google.auth.transport.requests.Request()
            creds.refresh(req)
            return creds.token
        except Exception:
            pass

    return None

def push_to_family_calendar(sched: dict, calendar_id: str = None):
    """
    Pushes the trash event directly to the Google Family Calendar.
    Discovers the 'Family' calendar automatically if calendar_id is not specified.
    """
    try:
        import requests
    except ImportError:
        print("❌ 'requests' package required to push to Google Calendar.")
        return False

    token = get_access_token()
    if not token:
        print("\n⚠️ Google Calendar authorization needed.")
        print("Run this one-time command to link your Google Calendar:")
        print("   python3 calendar_oauth_helper.py\n")
        print("Or use the 1-click Google Calendar web link:")
        print(generate_gcal_link(sched))
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    target_cal_id = calendar_id or os.environ.get("FAMILY_CALENDAR_ID")
    if not target_cal_id:
        url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                cals = res.json().get("items", [])
                for c in cals:
                    summary = c.get("summary", "").strip()
                    if "family" in summary.lower():
                        target_cal_id = c["id"]
                        print(f"🎯 Auto-detected Family Calendar: '{summary}' ({target_cal_id})")
                        break
                if not target_cal_id and cals:
                    # Look for primary
                    for c in cals:
                        if c.get("primary"):
                            target_cal_id = c["id"]
                            print(f"🎯 Using primary calendar: '{c.get('summary')}' ({target_cal_id})")
                            break
        except Exception as e:
            print(f"⚠️ Network error querying calendars: {e}")

    if not target_cal_id:
        print("⚠️ No suitable Google Calendar detected.")
        return False

    staging_dt = datetime.datetime.strptime(sched["staging_sunday"], "%Y-%m-%d")
    time_min = f"{staging_dt.isoformat()}T00:00:00Z"
    time_max = f"{(staging_dt + datetime.timedelta(days=2)).isoformat()}T23:59:59Z"

    list_url = f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(target_cal_id)}/events"
    params = {
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "q": "Bins"
    }
    
    start_time = f"{sched['staging_sunday']}T19:00:00"
    end_time = f"{sched['staging_sunday']}T19:30:00"
    
    bin_desc = "\n".join([f"• {b['color']} ({b['name']}): {b['notes']}" for b in sched["bins"]])
    description = (
        f"City of San Diego Trash Collection for {sched['address']}.\n\n"
        f"Bins to put out tonight:\n{bin_desc}\n\n"
        f"Collection: {sched['collection_day_name']}, {sched['collection_date']} (by 6:00 AM)\n"
        f"{'⚠️ Holiday Delay: Collection shifted by 1 day.\n' if sched['holiday_delayed'] else ''}\n"
        f"Portal: {PORTAL_URL}"
    )

    event_body = {
        "summary": sched["title"],
        "location": sched["address"],
        "description": description,
        "start": {
            "dateTime": f"{start_time}-07:00",
            "timeZone": "America/Los_Angeles"
        },
        "end": {
            "dateTime": f"{end_time}-07:00",
            "timeZone": "America/Los_Angeles"
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 0},
                {"method": "popup", "minutes": 60}
            ]
        }
    }

    try:
        existing_res = requests.get(list_url, headers=headers, params=params, timeout=10)
        existing_events = existing_res.json().get("items", []) if existing_res.status_code == 200 else []

        if existing_events:
            event_id = existing_events[0]["id"]
            patch_url = f"{list_url}/{event_id}"
            patch_res = requests.patch(patch_url, headers=headers, json=event_body, timeout=10)
            if patch_res.status_code == 200:
                print(f"✅ Updated existing calendar event: '{sched['title']}' on {sched['staging_sunday']}")
                return True
            else:
                print(f"❌ Failed to update calendar event: {patch_res.text}")
                return False
        else:
            post_res = requests.post(list_url, headers=headers, json=event_body, timeout=10)
            if post_res.status_code in (200, 201):
                print(f"🎉 Successfully inserted event to Family Calendar: '{sched['title']}' on {sched['staging_sunday']}")
                return True
            else:
                print(f"❌ Failed to insert calendar event: {post_res.text}")
                return False
    except Exception as e:
        print(f"❌ Error communicating with Google Calendar API: {e}")
        return False

def get_keep_checklist_text(sched: dict):
    """Outputs clean checklist text suitable for Google Keep."""
    lines = [
        f"Chore: Sunday Night Trash ({sched['staging_sunday']})",
        f"Address: {sched['address']}",
        f"Collection: {sched['collection_day_name']} {sched['collection_date']}",
        "",
        "Bins to Roll Out Curbside:"
    ]
    for b in sched["bins"]:
        lines.append(f"[ ] {b['icon']} {b['color']} Bin — {b['name']} ({b['notes']})")
    
    if not sched["is_recycling_week"]:
        lines.append("(Note: Blue Recycling bin stays in this week)")
    else:
        lines.append("⭐ Recycling week: ALL 3 BINS go out!")
    
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="LDK Ops Trash & Recycling Schedule Engine")
    parser.add_argument("--status", action="store_true", help="Print upcoming trash & recycling status")
    parser.add_argument("--send-invite", action="store_true", help="Send native calendar invite email from Leo to Lauren & Dailey")
    parser.add_argument("--dry-run", action="store_true", help="Preview email invite without dispatching")
    parser.add_argument("--push-calendar", action="store_true", help="Push upcoming event directly to Google Family Calendar")
    parser.add_argument("--calendar-id", help="Override Google Calendar ID")
    parser.add_argument("--gcal-link", action="store_true", help="Print 1-click Google Calendar web link")
    parser.add_argument("--ics", action="store_true", help="Export .ics file to output/trash_schedule.ics")
    parser.add_argument("--keep-text", action="store_true", help="Print checklist text formatted for Google Keep")
    parser.add_argument("--date", help="Inspect schedule for a specific date (YYYY-MM-DD)")
    args = parser.parse_args()

    target_dt = None
    if args.date:
        target_dt = datetime.date.fromisoformat(args.date)

    sched = get_upcoming_schedule(target_dt)

    executed_action = False
    if args.send_invite:
        send_trash_invite(sched, dry_run=args.dry_run)
        executed_action = True

    if args.push_calendar:
        push_to_family_calendar(sched, calendar_id=args.calendar_id)
        executed_action = True

    if args.gcal_link:
        print(generate_gcal_link(sched))
        executed_action = True

    if args.ics:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ics_path = OUTPUT_DIR / "trash_schedule.ics"
        ics_path.write_text(generate_ics_content(sched), encoding="utf-8")
        print(f"✅ Generated ICS calendar file: {ics_path}")
        executed_action = True

    if args.keep_text:
        print(get_keep_checklist_text(sched))
        executed_action = True

    if executed_action:
        return

    print(f"\n🗑️  LDK Ops Trash Schedule Engine")
    print(f"📍 Address: {sched['address']}")
    print(f"📅 Upcoming Staging Night: Sunday, {sched['staging_sunday']} (~7:00 PM)")
    print(f"🚛 Collection Day: {sched['collection_day_name']}, {sched['collection_date']} (curbside by 6:00 AM)")
    print(f"♻️  Recycling Week: {'YES (All 3 Bins)' if sched['is_recycling_week'] else 'NO (Trash & Organics only)'}")
    print(f"📦 Bins to roll out:")
    for b in sched["bins"]:
        print(f"   • {b['icon']} {b['color']} Bin: {b['name']} ({b['notes']})")
    if sched["holiday_delayed"]:
        print(f"⚠️  Holiday collection delay in effect!")
    print(f"\n1-Click Google Calendar Link:")
    print(generate_gcal_link(sched))
    print()

if __name__ == "__main__":
    main()
