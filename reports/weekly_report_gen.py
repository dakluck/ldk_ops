import os
import datetime
from google.cloud import firestore

def generate_weekly_report():
    # Project ID from google-services.json
    import json
    with open(os.path.expanduser("~/Development/ldk_ops/service_account.json"), 'r') as f:
        project_id = json.load(f).get("project_id")
    
    # Set the credentials environment variable
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.expanduser("~/Development/ldk_ops/service_account.json")
    
    try:
        db = firestore.Client(project=project_id)
    except Exception as e:
        print(f"Error connecting to Firestore: {e}")
        return

    now = datetime.datetime.utcnow()
    one_week_ago = now - datetime.timedelta(days=7)
    
    print("=== Weekly Business Rundown: Reference Project ===")
    print(f"Period: {one_week_ago.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}\n")
    
    # 1. New Users
    try:
        users_ref = db.collection('users')
        # Using a generic 'createdAt' field. If not exists, this might return 0.
        new_users_query = users_ref.where('createdAt', '>=', one_week_ago).stream()
        new_users_count = len(list(new_users_query))
    except Exception as e:
        new_users_count = "Error"
        print(f"Note: Could not fetch new users ({e})")

    # 2. Service Records
    try:
        services_ref = db.collection('service_records')
        # We'll fetch all and filter in Python to be safe about date formats
        all_services = services_ref.stream()
        
        completed_services = 0
        pending_services = []
        total_revenue = 0
        
        for service in all_services:
            data = service.to_dict()
            date_str = data.get('date', '')
            
            # Simple date filter (assuming YYYY-MM-DD)
            if date_str:
                try:
                    service_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
                    if service_date >= one_week_ago:
                        if data.get('status') == 'completed':
                            completed_services += 1
                        elif data.get('status') in ['pending', 'issue']:
                            pending_services.append(data)
                        total_revenue += data.get('amount', 0)
                except ValueError:
                    pass

        # 3. Collections (Revenue/Payments)
        # We can also check a 'collections' or 'payments' collection
        # But we'll use service_records for now as a primary source
    except Exception as e:
        completed_services = "Error"
        pending_services = []
        total_revenue = "Error"
        print(f"Note: Could not fetch service records ({e})")

    print(f"🚀 New Users: {new_users_count}")
    print(f"🛠️ Completed Services: {completed_services}")
    if total_revenue != "Error":
        print(f"💰 Estimated Revenue: ${total_revenue:.2f}")
    else:
        print(f"💰 Estimated Revenue: Error")
    
    print("\n--- Key Highlights ---")
    if isinstance(completed_services, int) and completed_services > 0:
        print(f"- Successfully completed {completed_services} services this week.")
    if isinstance(new_users_count, int) and new_users_count > 0:
        print(f"- Welcomed {new_users_count} new users to the platform.")
    if total_revenue != "Error" and total_revenue > 0:
        print(f"- Generated ${total_revenue:.2f} in revenue.")
    if (isinstance(completed_services, int) and completed_services == 0 and 
        isinstance(new_users_count, int) and new_users_count == 0 and 
        total_revenue == 0):
        print("- No major activity recorded this week.")
    else:
        print("- Activity was recorded for the period.")

    print("\n--- Items Requiring Attention ---")
    if pending_services:
        for ps in pending_services:
            print(f"- [!] {ps.get('service_type', 'Unknown Service')} for {ps.get('user_id', 'Unknown User')} (Status: {ps.get('status')})")
    else:
        print("- No urgent items requiring attention.")

    print("\n==================================================")

if __name__ == "__main__":
    generate_weekly_report()
