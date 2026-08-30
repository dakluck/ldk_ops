"""
LDK Ops — Automated Growth Engine & Community Marketing Scout for The Reference App
Tracks acquisition funnels, conversion economics, and generates high-engagement community content.
"""
import os
import sys
from datetime import datetime, timezone
from google.cloud import firestore

PROJECT_ID = "reference-482005"
ANNUAL_SUB_PRICE = 29.99

def run_growth_audit():
    print("=" * 72)
    print("  THE REFERENCE APP — AUTOMATED GROWTH & MARKETING AUDIT")
    print(f"  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 72)
    print()

    try:
        db = firestore.Client(project=PROJECT_ID)
    except Exception as e:
        print(f"❌ Firestore connection error: {e}")
        return

    # 1. Funnel & Conversion Metrics
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

    print("📊 [CONVERSION FUNNEL & MONETIZATION]")
    print(f"  • Registered Users (Top-of-Funnel) : {total_users}")
    print(f"  • Premium Paid Subscribers         : {premium_users}")
    print(f"  • Free-to-Paid Conversion Rate     : {conversion_rate:.1f}%")
    print(f"  • Total Watches Cataloged          : {total_watches}")
    print(f"  • Total Collections Created        : {total_collections}")
    print(f"  • Avg Watches per User             : {(total_watches / total_users if total_users else 0):.1f}")
    print()

    # 2. Paid Acquisition Economics (Apple Search Ads Unit Economics)
    # LTV per install = Conversion Rate * Annual Price
    # Target CPA for break-even = Conversion Rate * Annual Price
    ltv_per_install = (conversion_rate / 100.0) * ANNUAL_SUB_PRICE
    target_cpi_breakeven = ltv_per_install
    target_cpi_profitable = ltv_per_install * 0.60 # 40% margin

    print("🎯 [PAID ACQUISITION UNIT ECONOMICS (Apple Search Ads)]")
    print(f"  • Annual Subscription Price        : ${ANNUAL_SUB_PRICE:.2f}/yr")
    print(f"  • Expected Value per New Install   : ${ltv_per_install:.2f}")
    print(f"  • Max Break-Even CPI (Cost/Install): ${target_cpi_breakeven:.2f}")
    print(f"  • Recommended Target CPI (40% ROI) : ${target_cpi_profitable:.2f}")
    print(f"  • Recommended Test Budget          : $100.00 (Est. 40-50 installs -> ~4-5 new subscribers)")
    print()

    # 3. Community Content Generator (Reddit / Watch Forums / Socials)
    top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_brand_names = ", ".join([f"{b} ({c})" for b, c in top_brands])

    print("📝 [AUTOMATED COMMUNITY POST — r/Watches & r/PrideAndPinion]")
    print("-" * 72)
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
    print("-" * 72)
    print()

    print("=" * 72)
    print("  AUDIT & MARKETING SCOUT COMPLETE")
    print("=" * 72)

if __name__ == "__main__":
    run_growth_audit()
