#!/usr/bin/env python3
"""
Test if we can create payments table by trying to access it first
"""

import os
import sys
from supabase import create_client, Client

def main():
    # Supabase connection
    url = "https://jgbczrhhcdvuwddbloit.supabase.co"
    service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpnYmN6cmhoY2R2dXdkZGJsb2l0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTY0MTU4NywiZXhwIjoyMDcxMjE3NTg3fQ.Co86-x0fbxJlT2ERO1QaYQNCFKsCMIStdZvpfrNqKys"
    
    try:
        supabase: Client = create_client(url, service_key)
        print("[OK] Connected to Supabase")
        
        # Check if payments table exists
        print("[INFO] Checking if payments table exists...")
        try:
            test_response = supabase.table('payments').select('*').limit(0).execute()
            print("[OK] Payments table already exists!")
            
            # Get structure by trying to insert a dummy record to see what fields are expected
            try:
                # This will fail but show us the expected structure
                dummy_insert = supabase.table('payments').insert({
                    'amount': 5.00,
                    'currency': 'PEN',
                    'status': 'test'
                }).execute()
                print("[INFO] Dummy insert succeeded (unexpected)")
            except Exception as insert_error:
                print(f"[INFO] Table structure validation: {insert_error}")
                
        except Exception as e:
            if "Could not find the table" in str(e):
                print("[INFO] Payments table does not exist - needs to be created")
                print("[ACTION REQUIRED] Please execute the following SQL in Supabase SQL Editor:")
                print("")
                print("-- COPY AND PASTE THIS INTO SUPABASE SQL EDITOR:")
                print("")
                with open('create_payments_table.sql', 'r', encoding='utf-8') as f:
                    print(f.read())
                print("")
                print("[NEXT] After running the SQL, test the webhook endpoint")
            else:
                print(f"[ERROR] Unknown error: {e}")
        
    except Exception as e:
        print(f"[ERROR] Connection error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()