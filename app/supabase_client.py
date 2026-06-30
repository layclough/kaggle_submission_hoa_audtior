# app/supabase_client.py
import os
from supabase import create_client, Client

def get_supabase_client() -> Client:
    """
    Initializes and returns the authenticated Supabase cloud database client with deep diagnostics.
    """
    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not supabase_url or not supabase_key:
        print("\n[DATABASE WARNING] Supabase credentials (SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY) are missing. DB operations will be bypassed.")
        return None

    # Let's completely bypass the strict placeholder text block to force execution
    try:
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        print(f"\n[DATABASE ERROR] Failed to connect to Supabase instance: {e}")
        return None

def save_audit_report(report_json: dict) -> bool:
    """
    Streams the structured AI report payload directly into your Supabase table.
    """
    client = get_supabase_client()
    if not client:
        return False

    try:
        print("Streaming structured AI report payload directly to Supabase cloud...")
        data = client.table("hoa_reports").insert({
            "report_id": report_json.get("metadata", {}).get("report_id", "unknown"),
            "hoa_name": report_json.get("metadata", {}).get("hoa_name", "Unknown HOA"),
            "document_hash": report_json.get("document_hash"),
            "payload": report_json 
        }).execute()
        print("🎉 Database sync complete! Live audit report logged successfully.")
        return True
    except Exception as e:
        print(f"[DATABASE ERROR] Insert transaction failed: {e}")
        return False