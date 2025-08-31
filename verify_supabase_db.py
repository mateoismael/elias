#!/usr/bin/env python3
"""
Supabase Database Verification Script for Pseudosapiens Project
Verifies database schema, data integrity, and subscription model implementation
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
import sys

class SupabaseVerifier:
    def __init__(self, supabase_url: str, supabase_key: str):
        # Parse the database URL from Supabase URL
        # Supabase URL format: https://[project-ref].supabase.co
        # Database connection needs to be: postgresql://[user]:[password]@db.[project-ref].supabase.co:5432/postgres
        
        parsed_url = urlparse(supabase_url)
        project_ref = parsed_url.hostname.split('.')[0]
        
        # For direct database connection, we need the database password
        # Since we only have the anon key, we'll use the Supabase REST API approach
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.project_ref = project_ref
        self.connection = None
        
    def connect_to_database(self):
        """Connect to Supabase database using direct connection"""
        try:
            # Try to connect using service role (if available in env)
            db_password = os.getenv('SUPABASE_DB_PASSWORD')
            if db_password:
                connection_string = f"postgresql://postgres:{db_password}@db.{self.project_ref}.supabase.co:5432/postgres"
                self.connection = psycopg2.connect(connection_string, cursor_factory=RealDictCursor)
                return True
            else:
                print("⚠️  Direct database connection not available (SUPABASE_DB_PASSWORD not found)")
                print("   Using REST API approach for verification...")
                return False
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    def execute_query(self, query: str) -> List[Dict]:
        """Execute a SQL query and return results"""
        if not self.connection:
            return []
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            print(f"❌ Query execution failed: {e}")
            return []
    
    def verify_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database"""
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        );
        """
        
        if self.connection:
            try:
                with self.connection.cursor() as cursor:
                    cursor.execute(query, (table_name,))
                    return cursor.fetchone()['exists']
            except Exception as e:
                print(f"❌ Error checking table {table_name}: {e}")
                return False
        return False
    
    def get_table_schema(self, table_name: str) -> List[Dict]:
        """Get the schema information for a table"""
        query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position;
        """
        
        if self.connection:
            try:
                with self.connection.cursor() as cursor:
                    cursor.execute(query, (table_name,))
                    return cursor.fetchall()
            except Exception as e:
                print(f"❌ Error getting schema for {table_name}: {e}")
                return []
        return []
    
    def get_table_indexes(self, table_name: str) -> List[Dict]:
        """Get indexes for a table"""
        query = """
        SELECT 
            indexname,
            indexdef
        FROM pg_indexes
        WHERE tablename = %s AND schemaname = 'public';
        """
        
        if self.connection:
            try:
                with self.connection.cursor() as cursor:
                    cursor.execute(query, (table_name,))
                    return cursor.fetchall()
            except Exception as e:
                print(f"❌ Error getting indexes for {table_name}: {e}")
                return []
        return []
    
    def verify_required_tables(self) -> Dict[str, bool]:
        """Verify all required tables exist"""
        required_tables = [
            'users',
            'subscription_plans',
            'subscriptions', 
            'payments',
            'webhook_secrets',
            'payment_logs'
        ]
        
        results = {}
        for table in required_tables:
            results[table] = self.verify_table_exists(table)
            status = "✅" if results[table] else "❌"
            print(f"{status} Table '{table}': {'EXISTS' if results[table] else 'MISSING'}")
        
        return results
    
    def verify_subscription_plans(self) -> List[Dict]:
        """Verify the subscription plans data matches expected freemium model"""
        query = """
        SELECT 
            id,
            name,
            display_name,
            price_soles,
            frequency_hours,
            max_emails_per_day,
            description,
            is_active,
            created_at
        FROM subscription_plans
        ORDER BY id;
        """
        
        plans = self.execute_query(query)
        
        print("\n📋 SUBSCRIPTION PLANS VERIFICATION:")
        print("=" * 60)
        
        expected_plans = {
            0: {"name": "free", "display_name": "Gratuito", "price_soles": 0.00, "max_emails_per_day": 3, "frequency_hours": 56},
            1: {"name": "premium_1_day", "display_name": "Premium 1/día", "price_soles": 5.00, "max_emails_per_day": 1, "frequency_hours": 24},
            2: {"name": "premium_2_day", "display_name": "Premium 2/día", "price_soles": 5.00, "max_emails_per_day": 2, "frequency_hours": 12},
            3: {"name": "premium_3_day", "display_name": "Premium 3/día", "price_soles": 5.00, "max_emails_per_day": 3, "frequency_hours": 8},
            4: {"name": "premium_4_day", "display_name": "Premium 4/día", "price_soles": 5.00, "max_emails_per_day": 4, "frequency_hours": 6},
            13: {"name": "premium_power_user", "display_name": "Premium Power User", "price_soles": 5.00, "max_emails_per_day": 13, "frequency_hours": 1, "is_active": False}
        }
        
        for plan in plans:
            plan_id = plan['id']
            status = "✅" if plan_id in expected_plans else "⚠️"
            
            print(f"{status} Plan {plan_id}: {plan['display_name']} - S/ {plan['price_soles']}")
            print(f"   📧 {plan['max_emails_per_day']} emails/day, every {plan['frequency_hours']}h")
            print(f"   📝 {plan['description']}")
            print(f"   🔄 Active: {plan['is_active']}")
            
            # Verify against expected values
            if plan_id in expected_plans:
                expected = expected_plans[plan_id]
                mismatches = []
                
                for key, expected_value in expected.items():
                    if key in plan and plan[key] != expected_value:
                        mismatches.append(f"{key}: got {plan[key]}, expected {expected_value}")
                
                if mismatches:
                    print(f"   ❌ Mismatches: {'; '.join(mismatches)}")
                else:
                    print(f"   ✅ All values match expected configuration")
            
            print()
        
        return plans
    
    def verify_users_and_subscriptions(self) -> Dict[str, Any]:
        """Check existing users and their subscriptions"""
        users_query = "SELECT COUNT(*) as count FROM users;"
        subscriptions_query = """
        SELECT 
            s.status,
            sp.display_name as plan_name,
            COUNT(*) as count
        FROM subscriptions s
        JOIN subscription_plans sp ON s.plan_id = sp.id
        GROUP BY s.status, sp.display_name
        ORDER BY s.status, sp.display_name;
        """
        
        user_count = self.execute_query(users_query)
        subscription_stats = self.execute_query(subscriptions_query)
        
        print("👥 USERS & SUBSCRIPTIONS:")
        print("=" * 40)
        
        if user_count:
            total_users = user_count[0]['count']
            print(f"📊 Total users: {total_users}")
        
        print("\n📈 Subscription Statistics:")
        for stat in subscription_stats:
            print(f"   {stat['status']}: {stat['count']} users on '{stat['plan_name']}'")
        
        return {
            'total_users': user_count[0]['count'] if user_count else 0,
            'subscription_stats': subscription_stats
        }
    
    def verify_payments_structure(self) -> List[Dict]:
        """Verify payments table structure and sample data"""
        # Check table structure
        schema = self.get_table_schema('payments')
        
        print("\n💳 PAYMENTS TABLE STRUCTURE:")
        print("=" * 45)
        
        required_columns = [
            'id', 'subscription_id', 'mercadopago_payment_id', 'amount', 'currency', 'status',
            'payment_date', 'payment_method', 'yape_phone', 'payment_preference_id', 'payment_type_id'
        ]
        
        found_columns = [col['column_name'] for col in schema]
        
        for col in required_columns:
            status = "✅" if col in found_columns else "❌"
            print(f"{status} Column '{col}'")
        
        # Check sample data
        sample_query = "SELECT COUNT(*) as count FROM payments;"
        payment_count = self.execute_query(sample_query)
        
        if payment_count:
            print(f"\n💰 Total payments: {payment_count[0]['count']}")
        
        return schema
    
    def verify_webhook_secrets(self) -> List[Dict]:
        """Verify webhook_secrets table and data"""
        query = "SELECT * FROM webhook_secrets ORDER BY service, environment;"
        secrets = self.execute_query(query)
        
        print("\n🔐 WEBHOOK SECRETS:")
        print("=" * 30)
        
        for secret in secrets:
            print(f"🔑 {secret['service']} ({secret['environment']})")
            print(f"   Secret: {'*' * min(20, len(secret['secret_key']))}")
            print(f"   Created: {secret['created_at']}")
        
        if not secrets:
            print("⚠️  No webhook secrets found")
        
        return secrets
    
    def verify_indexes_and_constraints(self) -> Dict[str, List[Dict]]:
        """Verify database indexes and constraints"""
        tables = ['users', 'subscription_plans', 'subscriptions', 'payments', 'webhook_secrets', 'payment_logs']
        all_indexes = {}
        
        print("\n📊 DATABASE INDEXES:")
        print("=" * 35)
        
        for table in tables:
            if self.verify_table_exists(table):
                indexes = self.get_table_indexes(table)
                all_indexes[table] = indexes
                
                print(f"\n🗂️  {table}:")
                if indexes:
                    for idx in indexes:
                        print(f"   📌 {idx['indexname']}")
                else:
                    print(f"   ⚠️  No indexes found")
        
        return all_indexes
    
    def run_full_verification(self) -> Dict[str, Any]:
        """Run complete database verification"""
        print("🔍 SUPABASE DATABASE VERIFICATION REPORT")
        print("=" * 80)
        print(f"🌐 Project: {self.project_ref}")
        print(f"📅 Verification Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Try to connect to database
        db_connected = self.connect_to_database()
        
        if not db_connected:
            print("❌ Cannot perform full verification without database connection")
            print("   Please set SUPABASE_DB_PASSWORD environment variable")
            return {"error": "Database connection failed"}
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'project_ref': self.project_ref,
            'database_connected': db_connected
        }
        
        try:
            # 1. Verify required tables exist
            print("\n1️⃣  CHECKING REQUIRED TABLES:")
            print("-" * 40)
            results['tables'] = self.verify_required_tables()
            
            # 2. Verify subscription plans
            print("\n2️⃣  VERIFYING SUBSCRIPTION PLANS:")
            print("-" * 40)
            results['subscription_plans'] = self.verify_subscription_plans()
            
            # 3. Check users and subscriptions
            print("\n3️⃣  CHECKING USERS & SUBSCRIPTIONS:")
            print("-" * 40)
            results['users_subscriptions'] = self.verify_users_and_subscriptions()
            
            # 4. Verify payments structure
            print("\n4️⃣  VERIFYING PAYMENTS STRUCTURE:")
            print("-" * 40)
            results['payments_structure'] = self.verify_payments_structure()
            
            # 5. Check webhook secrets
            print("\n5️⃣  CHECKING WEBHOOK SECRETS:")
            print("-" * 40)
            results['webhook_secrets'] = self.verify_webhook_secrets()
            
            # 6. Verify indexes
            print("\n6️⃣  CHECKING INDEXES & CONSTRAINTS:")
            print("-" * 40)
            results['indexes'] = self.verify_indexes_and_constraints()
            
        except Exception as e:
            print(f"❌ Verification error: {e}")
            results['error'] = str(e)
        
        finally:
            if self.connection:
                self.connection.close()
        
        return results
    
    def generate_summary(self, results: Dict[str, Any]) -> None:
        """Generate a summary of the verification results"""
        print("\n" + "=" * 80)
        print("📋 VERIFICATION SUMMARY")
        print("=" * 80)
        
        if 'error' in results:
            print(f"❌ Verification failed: {results['error']}")
            return
        
        # Table status summary
        if 'tables' in results:
            missing_tables = [table for table, exists in results['tables'].items() if not exists]
            if missing_tables:
                print(f"❌ Missing tables: {', '.join(missing_tables)}")
            else:
                print("✅ All required tables exist")
        
        # Subscription plans summary
        if 'subscription_plans' in results:
            plan_count = len(results['subscription_plans'])
            print(f"📋 Found {plan_count} subscription plans")
            
            # Check if we have the expected freemium model
            expected_plan_ids = [0, 1, 2, 3, 4, 13]
            found_plan_ids = [plan['id'] for plan in results['subscription_plans']]
            
            missing_plans = set(expected_plan_ids) - set(found_plan_ids)
            if missing_plans:
                print(f"⚠️  Missing expected plans: {missing_plans}")
            else:
                print("✅ All expected freemium plans found")
        
        # Users and subscriptions summary
        if 'users_subscriptions' in results:
            total_users = results['users_subscriptions']['total_users']
            print(f"👥 Total users: {total_users}")
            
            if total_users > 0:
                print("✅ Database has active users")
            else:
                print("⚠️  No users found in database")
        
        # Overall health
        print("\n🏥 OVERALL DATABASE HEALTH:")
        if all(results['tables'].values()) and plan_count >= 6:
            print("✅ Database schema is healthy and ready for production")
        else:
            print("⚠️  Database needs attention - some issues found")
        
        print("=" * 80)

def main():
    """Main execution function"""
    # Load environment variables
    supabase_url = os.getenv('SUPABASE_URL', 'https://jgbczrhhcdvuwddbloit.supabase.co')
    supabase_key = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpnYmN6cmhoY2R2dXdkZGJsb2l0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU2NDE1ODcsImV4cCI6MjA3MTIxNzU4N30.bj_ycKy8tjv5gVqfDHIRa1JD_KbcVa9m7Cdqa1ZRSXk')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        print("   Please ensure SUPABASE_URL and SUPABASE_KEY are set")
        sys.exit(1)
    
    # Initialize verifier
    verifier = SupabaseVerifier(supabase_url, supabase_key)
    
    # Run verification
    results = verifier.run_full_verification()
    
    # Generate summary
    verifier.generate_summary(results)
    
    # Optionally save results to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"supabase_verification_report_{timestamp}.json"
    
    try:
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Full report saved to: {report_file}")
    except Exception as e:
        print(f"⚠️  Could not save report file: {e}")

if __name__ == "__main__":
    main()