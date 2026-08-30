import datetime
import urllib.parse
from email_sender import send_email
import argparse
import sys

# Child Profile
DAUGHTER_DOB = datetime.date(2023, 10, 6)

def calculate_age(target_date=None):
    if target_date is None:
        target_date = datetime.date.today()
    years = target_date.year - DAUGHTER_DOB.year
    months = target_date.month - DAUGHTER_DOB.month
    if target_date.day < DAUGHTER_DOB.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    return years, months

def generate_gcal_link(title, start_dt, end_dt, description, location):
    fmt = "%Y%m%dT%H%M%SZ"
    start_str = start_dt.strftime(fmt)
    end_str = end_dt.strftime(fmt)
    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": f"{start_str}/{end_str}",
        "details": description,
        "location": location
    }
    return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"

def generate_ics(events, organizer="leo@ldk-international.com"):
    now_str = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LDK Ops//SD Weekend Scout//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]
    for ev in events:
        s_str = ev["start"].strftime("%Y%m%dT%H%M%SZ")
        e_str = ev["end"].strftime("%Y%m%dT%H%M%SZ")
        uid = f"sd-scout-{ev['id']}-{ev['start'].strftime('%Y%m%d')}@ldk-international.com"
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_str}",
            f"DTSTART:{s_str}",
            f"DTEND:{e_str}",
            f"SUMMARY:{ev['title']}",
            f"DESCRIPTION:{ev['description']}",
            f"LOCATION:{ev['location']}",
            f"ORGANIZER;CN=Leo:mailto:{organizer}",
            "ATTENDEE;ROLE=REQ-PARTICIPANT;CN=Lauren Dobashi:mailto:ldobashi@gmail.com",
            "ATTENDEE;ROLE=REQ-PARTICIPANT;CN=Dailey Kluck:mailto:dailey.kluck@gmail.com",
            "STATUS:CONFIRMED",
            "END:VEVENT"
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)

def get_upcoming_weekend_dates():
    today = datetime.date.today()
    # Find coming Saturday and Sunday
    days_to_sat = (5 - today.weekday()) % 7
    if days_to_sat == 0 and today.weekday() == 5:
        saturday = today
    else:
        saturday = today + datetime.timedelta(days=days_to_sat)
    sunday = saturday + datetime.timedelta(days=1)
    return saturday, sunday

def build_curated_recommendations(saturday, sunday):
    """
    Curates hyper-local, age-appropriate activities tailored for toddler (~almost 3 y/o).
    """
    sat_dt_morning = datetime.datetime.combine(saturday, datetime.time(9, 30))
    sat_dt_morning_end = datetime.datetime.combine(saturday, datetime.time(11, 30))

    sat_dt_afternoon = datetime.datetime.combine(saturday, datetime.time(15, 0))
    sat_dt_afternoon_end = datetime.datetime.combine(saturday, datetime.time(17, 0))

    sun_dt_morning = datetime.datetime.combine(sunday, datetime.time(9, 0))
    sun_dt_morning_end = datetime.datetime.combine(sunday, datetime.time(11, 30))

    events = [
        {
            "id": "1",
            "day": f"Saturday Morning ({saturday.strftime('%b %d')})",
            "title": "Waterfront Park Splash & Playground",
            "category": "Outdoor & Water Play",
            "location": "1600 Pacific Hwy, San Diego, CA 92101",
            "start": sat_dt_morning,
            "end": sat_dt_morning_end,
            "best_time": "9:30 AM - 11:30 AM",
            "description": "Zero-depth splash fountain basins, shaded modern play equipment, and bayside walking paths ideal for toddlers.",
            "tips": "Bring swimsuit/change of clothes, towels, and sunblock. Easy paid parking in the underground county garage."
        },
        {
            "id": "2",
            "day": f"Saturday Afternoon ({saturday.strftime('%b %d')})",
            "title": "The New Children's Museum — Toddler Exploration",
            "category": "Interactive & Indoor Art",
            "location": "200 W Island Ave, San Diego, CA 92101",
            "start": sat_dt_afternoon,
            "end": sat_dt_afternoon_end,
            "best_time": "3:00 PM - 5:00 PM",
            "description": "Dedicated 'Tiket Room' and toddler sensory climbing installations designed specifically for ages 0-4.",
            "tips": "Great shaded/indoor air-conditioned option during warmer afternoon hours."
        },
        {
            "id": "3",
            "day": f"Sunday Morning ({sunday.strftime('%b %d')})",
            "title": "San Diego Zoo: Wildlife Explorers Basecamp",
            "category": "Animals & Nature Adventure",
            "location": "2920 Zoo Dr, Balboa Park, San Diego, CA 92101",
            "start": sun_dt_morning,
            "end": sun_dt_morning_end,
            "best_time": "9:00 AM - 11:30 AM",
            "description": "Explorers Basecamp has low-height climbing, rope bridges, water squirt zones, and close-up desert/rainforest animal encounters tailored for toddlers.",
            "tips": "Arrive at 9:00 AM right when gates open to beat the heat and crowd. Stroller friendly throughout."
        }
    ]
    return events

def run_weekend_scout(send=True):
    today = datetime.date.today()
    years, months = calculate_age(today)
    sat, sun = get_upcoming_weekend_dates()
    events = build_curated_recommendations(sat, sun)

    subject = f"☀️ San Diego Weekend Ideas for the Family ({sat.strftime('%b %d')} - {sun.strftime('%b %d')})"

    html_parts = [
        f"<div style='font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; max-width: 650px; margin: auto; padding: 20px; color: #2D3748;'>",
        f"<h2 style='color: #2B6CB0; margin-bottom: 4px;'>🌴 San Diego Family Weekend Guide</h2>",
        f"<p style='font-size: 14px; color: #718096; margin-top: 0;'>Curated for this weekend ({sat.strftime('%B %d')} &ndash; {sun.strftime('%B %d')}) &bull; Tailored for age ~{years} yrs {months} mos (DOB: Oct 6, 2023)</p>",
        f"<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 20px 0;'>",
        f"<p style='font-size: 15px;'>Here are 3 hyper-local, toddler-friendly ideas for this weekend with 1-click Google Calendar integration:</p>"
    ]

    for ev in events:
        gcal_url = generate_gcal_link(ev["title"], ev["start"], ev["end"], ev["description"] + "\n\nTips: " + ev["tips"], ev["location"])
        html_parts.extend([
            f"<div style='background-color: #F7FAFC; border-left: 4px solid #3182CE; padding: 16px; border-radius: 6px; margin-bottom: 20px;'>",
            f"<h3 style='margin: 0 0 6px 0; color: #2D3748;'>{ev['title']} <span style='font-size: 12px; background: #EBF8FF; color: #2B6CB0; padding: 2px 8px; border-radius: 12px; font-weight: normal; margin-left: 6px;'>{ev['category']}</span></h3>",
            f"<p style='margin: 4px 0; font-size: 14px;'><strong>📅 When:</strong> {ev['day']} &bull; {ev['best_time']}</p>",
            f"<p style='margin: 4px 0; font-size: 14px;'><strong>📍 Location:</strong> {ev['location']}</p>",
            f"<p style='margin: 8px 0; font-size: 14px; line-height: 1.5;'>{ev['description']}</p>",
            f"<p style='margin: 8px 0; font-size: 13px; color: #4A5568;'><strong>💡 Tip:</strong> {ev['tips']}</p>",
            f"<div style='margin-top: 12px;'>",
            f"<a href='{gcal_url}' style='display: inline-block; background-color: #3182CE; color: #ffffff; text-decoration: none; padding: 8px 14px; border-radius: 6px; font-size: 13px; font-weight: 600;'>+ Add to Google Calendar</a>",
            f"</div>",
            f"</div>"
        ])

    html_parts.extend([
        f"<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 20px 0;'>",
        f"<p style='font-size: 12px; color: #A0AEC0; text-align: center;'>LDK Ops &bull; Automated Family Weekend Scout</p>",
        f"</div>"
    ])

    html_body = "".join(html_parts)

    text_parts = [
        f"San Diego Family Weekend Guide ({sat.strftime('%b %d')} - {sun.strftime('%b %d')})",
        f"Tailored for age ~{years} yrs {months} mos (DOB: 10/6/2023)\n",
        "Here are 3 recommended toddler-friendly activities for this weekend:\n"
    ]
    for ev in events:
        gcal_url = generate_gcal_link(ev["title"], ev["start"], ev["end"], ev["description"], ev["location"])
        text_parts.extend([
            f"- {ev['title']} ({ev['category']})",
            f"  When: {ev['day']} ({ev['best_time']})",
            f"  Where: {ev['location']}",
            f"  Summary: {ev['description']}",
            f"  Tip: {ev['tips']}",
            f"  Add to Calendar: {gcal_url}\n"
        ])
    text_body = "\n".join(text_parts)

    if send:
        success = send_email(
            subject=subject,
            body=html_body,
            recipients=["ldobashi@gmail.com", "dailey.kluck@gmail.com"],
            from_account="leo",
            is_html=True
        )
        return success
    else:
        print("Subject:", subject)
        print("\nPlain text body:\n", text_body)
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print email body instead of sending")
    args = parser.parse_args()
    run_weekend_scout(send=not args.dry_run)
