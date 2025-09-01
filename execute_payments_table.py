#!/usr/bin/env python3
"""
Execute payments table creation in Supabase
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
        
        # Read the SQL file
        with open('create_payments_table.sql', 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print("[INFO] Executing payments table creation...")
        
        # Execute SQL using rpc call or direct SQL execution
        # Note: Supabase client doesn't have direct SQL execution, so we'll use individual statements
        
        # Create the table
        create_table_sql = """
        CREATE TABLE payments (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            subscription_id UUID REFERENCES subscriptions(id),
            mercadopago_payment_id VARCHAR(100),
            amount DECIMAL(10,2) NOT NULL,
            currency VARCHAR(3) DEFAULT 'PEN',
            status VARCHAR(20),
            payment_date TIMESTAMP WITH TIME ZONE,
            payment_method VARCHAR(20) DEFAULT 'mercadopago',
            yape_phone VARCHAR(15),
            payment_preference_id VARCHAR(100), 
            payment_type_id VARCHAR(50),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        try:
            result = supabase.rpc('exec_sql', {'sql': create_table_sql}).execute()
            print("[OK] Payments table created successfully")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("[INFO] Payments table already exists")
            else:
                print(f"[ERROR] Creating table: {e}")
                return
        
        # Test the table was created
        print("[INFO] Testing payments table access...")
        try:
            test_response = supabase.table('payments').select('*').limit(0).execute()
            print("[OK] Payments table is accessible")
        except Exception as e:
            print(f"[ERROR] Cannot access payments table: {e}")
            return
        
        print("[SUCCESS] Payments table creation completed!")
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()