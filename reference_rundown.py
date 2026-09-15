#!/usr/bin/env python3
"""
The Reference App — Weekly Executive Rundown & Analytics Digest
Dispatched every Sunday evening to dailey@ldk-international.com and dailey.kluck@gmail.com.
Aggregates Firestore user growth, conversion metrics, catalog volume, customer feedback, and paid acquisition targets.
"""

import os
import sys
import datetime
import argparse
from pathlib import Path
from google.cloud import firestore

# Add local path for email_sender
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from email_sender import send_email

PROJECT_ID = "reference-482005"
ANNUAL_SUB_PRICE = 29.99
RECIPIENTS = ["dailey@ldk-international.com", "dailey.kluck@gmail.com"]

def get_firestore_client():
    return firestore.Client(project=PROJECT_ID)

def run_reference_rundown(send=True):
    now = datetime.datetime.now(datetime.timezone.utc)
    one_week_ago = now - datetime.timedelta(days=7)

    print(f"📊 Gathering Reference App weekly metrics for {one_week_ago.strftime('%b %d')} - {now.strftime('%b %d, %Y')}...")

    try:
        db = get_firestore_client()
    except Exception as e:
        print(f"❌ Error connecting to Firestore: {e}")
        return False

    # 1. Fetch Users
    users = list(db.collection("users").stream())
    total_users = len(users)
    premium_users = 0
    new_users_week = 0

    for u in users:
        data = u.to_dict()
        if data.get("isPremium"):
            premium_users += 1
        
        # Check creation date if available
        created_at = data.get("createdAt")
        if created_at:
            if isinstance(created_at, datetime.datetime):
                if created_at >= one_week_ago:
                    new_users_week += 1
            elif isinstance(created_at, str):
                try:
                    dt = datetime.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if dt >= one_week_ago:
                        new_users_week += 1
                except Exception:
                    pass

    conversion_rate = (premium_users / total_users * 100) if total_users else 0.0

    # 2. Fetch Watches & Collections
    watches = list(db.collection_group("watches").stream())
    collections = list(db.collection_group("collections").stream())
    total_watches = len(watches)
    total_collections = len(collections)

    brand_counts = {}
    for w in watches:
        b = w.to_dict().get("brand") or "Unknown"
        brand_counts[b] = brand_counts.get(b, 0) + 1

    top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # 3. Fetch Customer Feedback
    feedback_docs = list(db.collection("feedback").stream())
    new_feedback = []
    for doc in feedback_docs:
        d = doc.to_dict()
        new_feedback.append({
            "id": doc.id,
            "user": d.get("userEmail") or d.get("userId") or "Anonymous",
            "platform": f"{d.get('platform', 'App')} v{d.get('appVersion', '')}",
            "text": d.get("text", "(No text comment)"),
            "status": d.get("status", "new")
        })

    # 4. Growth Economics
    ltv_per_install = (conversion_rate / 100.0) * ANNUAL_SUB_PRICE
    ios_target_cpi = ltv_per_install * 0.60
    android_target_cpi = min(1.20, ltv_per_install * 0.40)

    # 5. Build HTML Email Body
    subject = f"⌚ Reference App Weekly Rundown: {total_users} Users, {premium_users} Premium ({now.strftime('%b %d')})"

    brand_rows_html = "".join([
        f"<tr><td style='padding: 6px 12px; border-bottom: 1px solid #edf2f7; font-weight: 500;'>{brand}</td>"
        f"<td style='padding: 6px 12px; border-bottom: 1px solid #edf2f7; text-align: right; color: #4a5568;'>{count} watches</td>"
        f"<td style='padding: 6px 12px; border-bottom: 1px solid #edf2f7; text-align: right; color: #718096;'>{(count/total_watches*100 if total_watches else 0):.1f}%</td></tr>"
        for brand, count in top_brands
    ])

    feedback_html = ""
    if new_feedback:
        fb_items = "".join([
            f"<li style='margin-bottom: 10px; font-size: 13px; line-height: 1.4;'>"
            f"<strong>{fb['user']}</strong> <span style='color: #718096;'>({fb['platform']})</span>: "
            f"<em>\"{fb['text']}\"</em></li>"
            for fb in new_feedback[-5:]
        ])
        feedback_html = f"""
        <div style="background-color: #f7fafc; border-left: 4px solid #4299e1; padding: 14px 18px; margin: 20px 0; border-radius: 4px;">
            <h4 style="margin: 0 0 10px 0; color: #2d3748; font-size: 14px;">💬 Recent Feedback Submissions ({len(new_feedback)} Total)</h4>
            <ul style="margin: 0; padding-left: 18px; color: #2d3748;">
                {fb_items}
            </ul>
        </div>
        """
    else:
        feedback_html = "<p style='font-size: 13px; color: #718096; margin: 15px 0;'><em>No new customer feedback tickets submitted this week.</em></p>"

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 620px; margin: 0 auto; color: #1a202c; line-height: 1.5; padding: 20px;">
        <div style="border-bottom: 2px solid #2b6cb0; padding-bottom: 12px; margin-bottom: 20px;">
            <span style="font-size: 11px; text-transform: uppercase; tracking: 1px; color: #2b6cb0; font-weight: 700;">LDK International &bull; Business Operations</span>
            <h2 style="margin: 4px 0 0 0; color: #2d3748; font-size: 22px;">The Reference App — Weekly Executive Rundown</h2>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #718096;">Week ending {now.strftime('%A, %B %d, %Y')}</p>
        </div>

        <!-- Key Metrics Cards -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 24px;">
            <div style="background: #ebf8ff; border-radius: 8px; padding: 14px; text-align: center; border: 1px solid #bee3f8;">
                <div style="font-size: 26px; font-weight: 700; color: #2b6cb0;">{total_users}</div>
                <div style="font-size: 12px; color: #4a5568; font-weight: 600; text-transform: uppercase;">Registered Users</div>
                <div style="font-size: 11px; color: #3182ce; margin-top: 4px;">+{new_users_week} new this week</div>
            </div>
            <div style="background: #f0fff4; border-radius: 8px; padding: 14px; text-align: center; border: 1px solid #c6f6d5;">
                <div style="font-size: 26px; font-weight: 700; color: #276749;">{premium_users}</div>
                <div style="font-size: 12px; color: #4a5568; font-weight: 600; text-transform: uppercase;">Premium Subscribers</div>
                <div style="font-size: 11px; color: #38a169; margin-top: 4px;">{conversion_rate:.1f}% conversion rate</div>
            </div>
            <div style="background: #faf5ff; border-radius: 8px; padding: 14px; text-align: center; border: 1px solid #e9d8fd;">
                <div style="font-size: 26px; font-weight: 700; color: #6b46c1;">{total_watches}</div>
                <div style="font-size: 12px; color: #4a5568; font-weight: 600; text-transform: uppercase;">Watches Cataloged</div>
                <div style="font-size: 11px; color: #805ad5; margin-top: 4px;">Across {total_collections} collections</div>
            </div>
            <div style="background: #fffaf0; border-radius: 8px; padding: 14px; text-align: center; border: 1px solid #feebc8;">
                <div style="font-size: 26px; font-weight: 700; color: #c05621;">${ltv_per_install:.2f}</div>
                <div style="font-size: 12px; color: #4a5568; font-weight: 600; text-transform: uppercase;">LTV per Install</div>
                <div style="font-size: 11px; color: #dd6b20; margin-top: 4px;">${ANNUAL_SUB_PRICE:.2f}/yr sub price</div>
            </div>
        </div>

        <!-- Top Brands -->
        <div style="margin-bottom: 24px;">
            <h3 style="margin: 0 0 10px 0; color: #2d3748; font-size: 16px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px;">🏆 Most Cataloged Brands</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr style="background-color: #f7fafc; color: #718096; text-align: left;">
                        <th style="padding: 8px 12px; font-weight: 600;">Brand</th>
                        <th style="padding: 8px 12px; text-align: right; font-weight: 600;">Count</th>
                        <th style="padding: 8px 12px; text-align: right; font-weight: 600;">Share</th>
                    </tr>
                </thead>
                <tbody>
                    {brand_rows_html}
                </tbody>
            </table>
        </div>

        <!-- Feedback -->
        {feedback_html}

        <!-- Paid Acquisition Targets -->
        <div style="margin-bottom: 24px; padding: 14px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;">
            <h4 style="margin: 0 0 8px 0; color: #2d3748; font-size: 14px;">🎯 Acquisition Target CPIs (Max Margin Blueprint)</h4>
            <div style="font-size: 13px; color: #4a5568;">
                • <strong>Apple Search Ads (iOS):</strong> Target CPI &le; <strong>${ios_target_cpi:.2f}</strong> ($5/day test budget)<br>
                • <strong>Google App Campaigns (Android):</strong> Target CPI &le; <strong>${android_target_cpi:.2f}</strong> ($5/day test budget)<br>
                • <strong>Production Status:</strong> <a href="https://thereference.app" style="color: #3182ce;">thereference.app</a> &bull; Project: <code>reference-482005</code>
            </div>
        </div>

        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0 16px 0;">
        <p style="font-size: 11px; color: #a0aec0; text-align: center; margin: 0;">
            Dispatched autonomously by <strong>Leo (LDK Ops)</strong> &bull; Scheduled Task: Sunday 8:00 PM PST
        </p>
    </div>
    """

    if send:
        print(f"📧 Sending Reference App Rundown email to {RECIPIENTS}...")
        success = send_email(
            subject=subject,
            body=html_body,
            recipients=RECIPIENTS,
            from_account="leo",
            is_html=True
        )
        if success:
            print("🎉 Weekly rundown successfully delivered via Leo SMTP.")
        return success
    else:
        print("\n--- PREVIEW SUBJECT ---")
        print(subject)
        print("\n--- HTML LENGTH ---")
        print(f"{len(html_body)} bytes")
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reference App Weekly Rundown")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without sending email")
    args = parser.parse_args()

    run_reference_rundown(send=not args.dry_run)
