import streamlit as st
from django.db import connections
from datetime import datetime

def log_action(username, action, module, status="success"):
    """
    Saves a system event to the audit_logs table.
    Usage: log_action("Admin", "Uploaded Document", "Knowledge Manager")
    """
    try:
        # Use the Django connection managed in your settings
        conn = connections["birai_db"]
        
        with conn.cursor() as cursor:
            query = """
                INSERT INTO audit_logs (timestamp, username, action, module, status)
                VALUES (%s, %s, %s, %s, %s)
            """
            # Use %s placeholders to prevent SQL Injection
            cursor.execute(query, [
                datetime.now(), 
                username, 
                action, 
                module, 
                status.lower()
            ])
            # Django's 'connections' usually auto-commits, but just in case:
            if not conn.get_autocommit():
                conn.commit()
                
    except Exception as e:
        # We don't want a logging error to crash the whole app
        print(f"FAILED TO WRITE TO AUDIT LOG: {e}")