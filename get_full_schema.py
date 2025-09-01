#!/usr/bin/env python3
"""
Get complete database schema from Supabase
"""

import os
import json
import sys
from supabase import create_client, Client
from typing import List, Dict, Any

def main():
    # Supabase connection
    url = "https://jgbczrhhcdvuwddbloit.supabase.co"
    service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpnYmN6cmhoY2R2dXdkZGJsb2l0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTY0MTU4NywiZXhwIjoyMDcxMjE3NTg3fQ.Co86-x0fbxJlT2ERO1QaYQNCFKsCMIStdZvpfrNqKys"
    
    try:
        supabase: Client = create_client(url, service_key)
        print("[OK] Connected to Supabase with service_role key")
        
        # List of known tables to check
        tables_to_check = [
            'users',
            'subscription_plans', 
            'subscriptions',
            'payments',
            'email_logs',
            'webhook_secrets',
            'phrases'
        ]
        
        existing_tables = []
        
        for table_name in tables_to_check:
            print(f"\n[CHECKING TABLE: {table_name}]")
            try:
                # Try to get one record to see table structure
                response = supabase.table(table_name).select('*').limit(1).execute()
                
                if response.data:
                    # Table exists and has data
                    sample_record = response.data[0]
                    print(f"  [OK] Table exists with {len(sample_record)} columns")
                    print("  COLUMNS:")
                    for column, value in sample_record.items():
                        value_type = type(value).__name__
                        value_preview = str(value)[:50] if value else "NULL"
                        print(f"    {column}: {value_type} = {value_preview}")
                    
                    # Get row count
                    count_response = supabase.table(table_name).select('*', count='exact').execute()
                    row_count = count_response.count if hasattr(count_response, 'count') else len(count_response.data)
                    print(f"  ROWS: {row_count}")
                    
                    existing_tables.append(table_name)
                    
                else:
                    # Table exists but no data
                    print("  [INFO] Table exists but no data")
                    existing_tables.append(table_name)
                    
            except Exception as e:
                if "Could not find the table" in str(e):
                    print(f"  [MISSING] Table does not exist")
                else:
                    print(f"  [ERROR] {e}")
        
        print(f"\n[SUMMARY]")
        print(f"Existing tables: {existing_tables}")
        print(f"Missing tables: {[t for t in tables_to_check if t not in existing_tables]}")
        
        # Check for any other tables we might have missed
        print(f"\n[ATTEMPTING TO DISCOVER OTHER TABLES]")
        try:
            # Try to get system tables or metadata - this might not work with anon key
            pass
        except Exception as e:
            print(f"  [INFO] Cannot access system metadata with current key")
        
        print(f"\n[COMPLETE]")
        
    except Exception as e:
        print(f"[ERROR] Error connecting to Supabase: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()