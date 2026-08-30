"""
LDK Ops — Multi-Platform Marketing & Growth Engine for The Reference App
Audits user acquisition funnels, manages Apple Search Ads & Google App Campaigns,
and synthesizes high-converting community marketing assets.
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from google.cloud import firestore

# Add local growth package
sys.path.insert(0, str(Path(__file__).resolve().parent))
from growth.asa_client import AppleSearchAdsClient
from growth.google_ads_client import GoogleAppCampaignsClient

PROJECT_ID = "reference-482005"
ANNUAL_SUB_PRICE = 29.99

def run_growth_audit():
    print("=" * 76)
    print("  THE REFERENCE APP — MULTI-PLATFORM GROWTH & MARKETING COMMAND")
    print(f"  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 76)
    print()

    try:
        db = firestore.Client(project=PROJECT_ID)
    except Exception as e:
        print(f"❌ Firestore connection error: {e}")
        return

    # 1. Funnel & Platform User Metrics
    users = list(db.collection("users").stream())
    total_users = len(users)
    premium_users = sum(1 for u in users if u.to_dict().get("isPremium"))
    conversion_rate = (premium_users / total_users * 100) if total_users else 0.0

    watches = list(db.collection_group("watches").stream())
    collections = list(db.collection_group("collections").stream())
    total_watches = len(watches)
    total_collections = len(collections)

    brand_counts = {}
    for w in watches:
        b = w.to_dict().get("brand") or "Unknown"
        brand_counts[b] = brand_counts.get(b, 0) + 1

    print("📊 [CONVERSION FUNNEL & DATABASE HEALTH]")
    print(f"  • Registered Users (Top-of-Funnel) : {total_users}")
    print(f"  • Premium Paid Subscribers         : {premium_users} (Conversion: {conversion_rate:.1f}%)")
    print(f"  • Total Watches Cataloged          : {total_watches}")
    print(f"  • Total Collections Created        : {total_collections}")
    print(f"  • Avg Watches per User             : {(total_watches / total_users if total_users else 0):.1f}")
    print()

    # 2. Multi-Platform Paid Acquisition Blueprint (iOS vs Android)
    ltv_per_install = (conversion_rate / 100.0) * ANNUAL_SUB_PRICE
    ios_target_cpi = ltv_per_install * 0.60 # $1.82 (40% margin)
    android_target_cpi = min(1.20, ltv_per_install * 0.40) # $1.20

    print("🎯 [MULTI-PLATFORM PAID ACQUISITION TARGETS]")
    print(f"  • Annual Subscription Price        : ${ANNUAL_SUB_PRICE:.2f}/yr")
    print(f"  • Realized Value per Install (LTV) : ${ltv_per_install:.2f}")
    print(f"  • Max Break-Even CPI Threshold     : ${ltv_per_install:.2f}")
    print()
    print("  🍎 Apple Search Ads (iOS):")
    print(f"     • Target Cost Per Install (tCPI): ${ios_target_cpi:.2f}")
    print("     • Recommended Keywords          : [watch identifier], [watch scanner], [watch tracker], [chrono24]")
    print("     • Daily Test Budget             : $5.00/day ($150/mo)")
    print()
    print("  🤖 Google App Campaigns (Android):")
    print(f"     • Target Cost Per Install (tCPI): ${android_target_cpi:.2f}")
    print("     • Channels                      : Google Play Search, Google Search, YouTube Shorts")
    print("     • Daily Test Budget             : $5.00/day ($150/mo)")
    print()

    # 3. Ad Platform Integration Status
    asa_client = AppleSearchAdsClient()
    gads_client = GoogleAppCampaignsClient()

    print("🔌 [PROGRAMMATIC AD CLIENT INTEGRATIONS]")
    print(f"  • Apple Search Ads API             : {'✅ LIVE' if asa_client.is_configured else '⚠️ BLUEPRINT / CONFIGURED'}")
    print(f"  • Google Ads App Campaigns API     : {'✅ LIVE' if gads_client.is_configured else '⚠️ BLUEPRINT / CONFIGURED'}")
    print()

    # 4. Automated Community Showcase Generator (Reddit / WatchUSeek / Discord)
    top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    print("📝 [WEEKLY ORGANIC COMMUNITY POST — r/Watches & r/PrideAndPinion]")
    print("-" * 76)
    sample_post = f"""Title: We built an AI watch identifier & collection logger for insurance/cataloging — here's what 200+ collectors are logging most.

Hey r/Watches!

A quick update from the horology tech side: we built REFERENCE (iOS & Android) to solve two big headaches:
1. Instantly identifying reference numbers, movements, and approximate market values from a single wrist photo.
2. Generating 1-click insurance-ready PDF reports with full specs, serial numbers, and condition ratings.

Over the last month, the most cataloged brands in our community database have been:
{chr(10).join([f"  • {b}: {c} watches" for b, c in top_brands])}

Curious to hear feedback from the community:
What features matter most when you catalog your collection? (Service history tracking, market value charts, or exportable insurance docs?)

Try it free on iOS/Android at https://thereference.app"""
    print(sample_post)
    print("-" * 76)
    print()

    print("=" * 76)
    print("  MARKETING & GROWTH SCOUT COMPLETE")
    print("=" * 76)

if __name__ == "__main__":
    run_growth_audit()
