"""
GCP Billing Export Query Utility for LDK International LLC.
Queries BigQuery billing export tables in dataset `gcp_billing_export` (project: ldk-international)
to provide granular cloud infrastructure cost attribution (COGS vs OpEx, service breakdown).
"""
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional

PROJECT_ID = "ldk-international"
DATASET_ID = "gcp_billing_export"


def get_bigquery_client():
    """Returns an authenticated BigQuery client using ADC or environment."""
    try:
        from google.cloud import bigquery
        import google.auth
        creds, _ = google.auth.default()
        return bigquery.Client(project=PROJECT_ID, credentials=creds)
    except Exception as e:
        return None


def get_gcp_billing_summary(month_date: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Fetches the GCP cost breakdown for the given month (defaults to current month).
    Returns a dictionary with status, total_cost, projects, and services.
    """
    if month_date is None:
        month_date = datetime.now(timezone.utc)
    
    invoice_month = month_date.strftime("%Y%m")
    
    client = get_bigquery_client()
    if not client:
        return {
            "status": "auth_required",
            "message": "BigQuery client unavailable. Run `gcloud auth application-default login` to authenticate."
        }
    
    try:
        # Find billing tables in dataset
        tables = list(client.list_tables(f"{PROJECT_ID}.{DATASET_ID}"))
        table_names = [t.table_id for t in tables]
        
        # Look for standard or detailed export table
        target_table = None
        for t in table_names:
            if t.startswith("gcp_billing_export_resource_v1_"):
                target_table = t
                break
            elif t.startswith("gcp_billing_export_v1_"):
                target_table = t
        
        if not target_table:
            return {
                "status": "pending_data",
                "message": f"Dataset `{DATASET_ID}` found, but Google Cloud has not yet written the first billing table. (Streaming typically begins within 1–6 hours)."
            }
        
        # Query monthly breakdown by project and service
        query = f"""
            SELECT
                COALESCE(project.id, 'unallocated') AS project_id,
                COALESCE(service.description, 'Unknown Service') AS service_name,
                ROUND(SUM(cost), 2) AS total_cost,
                ROUND(SUM(IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) c), 0)), 2) AS total_credits,
                ROUND(SUM(cost) + SUM(IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) c), 0)), 2) AS net_cost
            FROM `{PROJECT_ID}.{DATASET_ID}.{target_table}`
            WHERE invoice.month = @invoice_month
            GROUP BY project_id, service_name
            HAVING net_cost > 0.00
            ORDER BY net_cost DESC
        """
        
        from google.cloud import bigquery
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("invoice_month", "STRING", invoice_month)
            ]
        )
        
        results = list(client.query(query, job_config=job_config))
        
        total_net = sum(r.net_cost for r in results)
        by_project = {}
        by_service = {}
        
        for r in results:
            # Aggregate by project
            p = r.project_id
            by_project[p] = by_project.get(p, 0.0) + r.net_cost
            
            # Aggregate by service
            s = r.service_name
            by_service[s] = by_service.get(s, 0.0) + r.net_cost
            
        return {
            "status": "success",
            "invoice_month": invoice_month,
            "table_used": target_table,
            "total_net_cost": round(total_net, 2),
            "by_project": {k: round(v, 2) for k, v in sorted(by_project.items(), key=lambda x: x[1], reverse=True)},
            "by_service": {k: round(v, 2) for k, v in sorted(by_service.items(), key=lambda x: x[1], reverse=True)},
            "raw_count": len(results)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error querying BigQuery billing export: {str(e)}"
        }


if __name__ == "__main__":
    summary = get_gcp_billing_summary()
    print("GCP Billing Summary:")
    print(summary)
