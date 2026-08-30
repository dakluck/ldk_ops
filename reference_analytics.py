import os
import sys
from google.cloud import firestore

PROJECT_ID = "reference-482005"

def run_analytics_report():
    print("========================================================================")
    print(f"  THE REFERENCE APP — FIRESTORE ANALYTICS & USER AUDIT")
    print(f"  Project: {PROJECT_ID}")
    print("========================================================================\n")
    
    try:
        db = firestore.Client(project=PROJECT_ID)
    except Exception as e:
        print(f"❌ Error connecting to Firestore: {e}")
        return

    # 1. Feedback
    print("💬 [FEEDBACK SUBMISSIONS]")
    try:
        feedback_docs = list(db.collection("feedback").stream())
        print(f"  Total Feedback Submissions: {len(feedback_docs)}")
        for doc in feedback_docs:
            d = doc.to_dict()
            print(f"\n  • Feedback ID: {doc.id}")
            print(f"    User: {d.get('userEmail') or d.get('userId') or 'Anonymous'}")
            print(f"    Platform / Version: {d.get('platform', 'N/A')} v{d.get('appVersion', 'N/A')}")
            print(f"    Status: {d.get('status', 'new')}")
            if d.get('screenshotUrl'):
                print(f"    Screenshot: {d.get('screenshotUrl')}")
            if d.get('text'):
                print(f"    Text: {d.get('text')}")
    except Exception as e:
        print(f"  Error reading feedback: {e}")

    # 2. Users
    print("\n👥 [USER & COLLECTION METRICS]")
    try:
        users = list(db.collection("users").stream())
        total_users = len(users)
        premium_users = sum(1 for u in users if u.to_dict().get("isPremium"))
        
        # Use collection group for instant retrieval of all watches & collections
        watches = list(db.collection_group("watches").stream())
        collections = list(db.collection_group("collections").stream())
        
        total_watches = len(watches)
        total_collections = len(collections)
        
        brand_counts = {}
        for w in watches:
            w_data = w.to_dict()
            brand = w_data.get("brand") or "Unknown"
            brand_counts[brand] = brand_counts.get(brand, 0) + 1

        print(f"  • Total Registered Users : {total_users}")
        print(f"  • ⭐ Premium Subscribers : {premium_users} ({(premium_users/total_users*100 if total_users else 0):.1f}% conversion)")
        print(f"  • ⌚ Total Watches Logged : {total_watches}")
        print(f"  • 📁 User Collections     : {total_collections}")

        # Top Brands
        print("\n🏆 [TOP BRANDS CATALOGED]")
        sorted_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for brand, count in sorted_brands:
            pct = (count / total_watches * 100) if total_watches else 0
            print(f"  • {brand:<22}: {count:>3} watches ({pct:4.1f}%)")

    except Exception as e:
        print(f"  Error reading user metrics: {e}")

    # 3. Additional Platform Collections
    print("\n📁 [PLATFORM COLLECTIONS]")
    try:
        showcase = list(db.collection("public_showcase").stream())
        shared = list(db.collection("shared_links").stream())
        print(f"  • Public Showcases (/public_showcase) : {len(showcase)} published")
        print(f"  • Shared Links (/shared_links)         : {len(shared)} active links")
    except Exception as e:
        print(f"  Error reading platform collections: {e}")

    print("\n========================================================================\n")

if __name__ == "__main__":
    run_analytics_report()
