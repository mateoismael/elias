#!/usr/bin/env python3
"""
Test script to verify Supabase database schema for MercadoPago integration
Uses service_role key to access all tables and data
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
        
        # Check subscription_plans table
        print("\n[SUBSCRIPTION PLANS]:")
        plans_response = supabase.table('subscription_plans').select('*').order('id').execute()
        if plans_response.data:
            for plan in plans_response.data:
                print(f"  Plan {plan['id']}: {plan['name']} - {plan['display_name']} - S/{plan['price_soles']}")
        else:
            print("  [ERROR] No subscription plans found")
        
        # Check payments table structure
        print("\n[PAYMENTS TABLE STRUCTURE]:")
        try:
            # Get sample payment to check columns
            payment_response = supabase.table('payments').select('*').limit(1).execute()
            if payment_response.data:
                payment = payment_response.data[0]
                print("  [OK] Payments table exists with columns:")
                for key in payment.keys():
                    print(f"    - {key}")
            else:
                print("  [INFO] Payments table exists but no data yet")
                # Try to get table info another way
                dummy_response = supabase.table('payments').select('id').limit(0).execute()
                print("  [OK] Payments table is accessible")
        except Exception as e:
            print(f"  [ERROR] Error accessing payments table: {e}")
        
        # Check webhook_secrets table
        print("\n[WEBHOOK SECRETS]:")
        try:
            secrets_response = supabase.table('webhook_secrets').select('*').execute()
            if secrets_response.data:
                for secret in secrets_response.data:
                    print(f"  Service: {secret['service']} | Environment: {secret['environment']} | Secret: {secret['secret_key'][:20]}...")
            else:
                print("  [ERROR] No webhook secrets found")
        except Exception as e:
            print(f"  [ERROR] webhook_secrets table not found: {e}")
        
        # Check users and subscriptions
        print("\n[USERS & SUBSCRIPTIONS]:")
        users_response = supabase.table('users').select('id, email, created_at').limit(5).execute()
        print(f"  Total users sample: {len(users_response.data) if users_response.data else 0}")
        
        subscriptions_response = supabase.table('subscriptions').select('user_id, plan_id, status').execute()
        if subscriptions_response.data:
            active_subs = [s for s in subscriptions_response.data if s['status'] == 'active']
            print(f"  Active subscriptions: {len(active_subs)}")
            # Count by plan
            plan_counts = {}
            for sub in active_subs:
                plan_id = sub['plan_id']
                plan_counts[plan_id] = plan_counts.get(plan_id, 0) + 1
            print("  Distribution by plan:")
            for plan_id, count in sorted(plan_counts.items()):
                print(f"    Plan {plan_id}: {count} users")
        
        # Check email_logs table
        print("\n[EMAIL LOGS]:")
        try:
            logs_response = supabase.table('email_logs').select('*').limit(5).order('sent_at', desc=True).execute()
            if logs_response.data:
                print(f"  Recent email logs: {len(logs_response.data)}")
                for log in logs_response.data[:3]:
                    print(f"    {log['sent_at']}: {log['user_email']} - {log['phrase_content'][:50]}...")
            else:
                print("  [INFO] No email logs yet")
        except Exception as e:
            print(f"  [ERROR] email_logs table issue: {e}")
        
        print("\n[OK] Database verification completed successfully!")
        
    except Exception as e:
        print(f"[ERROR] Error connecting to Supabase: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()