"""
Database module for subscription management with Supabase
UPDATED FOR 2025 DELIVERABILITY-SAFE FREEMIUM MODEL (Plan ID = Emails por día):
- Plan 0: Free (56h = 3/semana L-M-V)
- Plan 1: Premium 1/día (24h)
- Plan 2: Premium 2/día (12h)
- Plan 3: Premium 3/día (8h)
- Plan 4: Premium 4/día (6h)
- Plan 13: Premium Power User 13/día (1h = VIP/manual)
"""
import os
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import structlog
from supabase import create_client, Client

logger = structlog.get_logger()

@dataclass
class User:
    id: str
    email: str
    created_at: datetime
    name: Optional[str] = None
    google_id: Optional[str] = None
    avatar_url: Optional[str] = None
    auth_method: Optional[str] = None

@dataclass 
class SubscriptionPlan:
    id: int
    name: str
    display_name: str
    price_soles: float
    frequency_hours: int
    max_emails_per_day: int
    description: str
    is_active: bool

@dataclass
class Subscription:
    id: str
    user_id: str
    plan_id: int
    status: str
    started_at: datetime
    expires_at: Optional[datetime] = None
    mercadopago_subscription_id: Optional[str] = None

class SupabaseManager:
    """Manages all database operations with Supabase"""
    
    def __init__(self):
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")
        
        self.supabase: Client = create_client(url, key)
        logger.info("Supabase client initialized")
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        try:
            response = self.supabase.table('users').select('*').eq('email', email).execute()
            
            if response.data:
                data = response.data[0]
                return User(
                    id=data['id'],
                    email=data['email'],
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
                    name=data.get('name'),
                    google_id=data.get('google_id'),
                    avatar_url=data.get('avatar_url'),
                    auth_method=data.get('auth_method')
                )
            return None
            
        except Exception as e:
            logger.error("Failed to get user by email", email=email, error=str(e))
            return None
    
    def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        """Get user by Google ID"""
        try:
            response = self.supabase.table('users').select('*').eq('google_id', google_id).execute()
            
            if response.data:
                data = response.data[0]
                return User(
                    id=data['id'],
                    email=data['email'],
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
                    name=data.get('name'),
                    google_id=data.get('google_id'),
                    avatar_url=data.get('avatar_url'),
                    auth_method=data.get('auth_method')
                )
            return None
            
        except Exception as e:
            logger.error("Failed to get user by Google ID", google_id=google_id, error=str(e))
            return None
    
    def create_user(self, email: str) -> Optional[User]:
        """Create new user (legacy email method)"""
        try:
            response = self.supabase.table('users').insert({
                'email': email,
                'auth_method': 'email'
            }).execute()
            
            if response.data:
                data = response.data[0]
                logger.info("User created", email=email, user_id=data['id'])
                return User(
                    id=data['id'],
                    email=data['email'],
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
                    name=data.get('name'),
                    google_id=data.get('google_id'),
                    avatar_url=data.get('avatar_url'),
                    auth_method=data.get('auth_method')
                )
            return None
            
        except Exception as e:
            logger.error("Failed to create user", email=email, error=str(e))
            return None
    
    def create_user_google(self, email: str, name: str, google_id: str, avatar_url: str = None) -> Optional[User]:
        """Create new user with Google authentication"""
        try:
            user_data = {
                'email': email,
                'name': name,
                'google_id': google_id,
                'auth_method': 'google'
            }
            if avatar_url:
                user_data['avatar_url'] = avatar_url
                
            response = self.supabase.table('users').insert(user_data).execute()
            
            if response.data:
                data = response.data[0]
                logger.info("User created with Google", email=email, google_id=google_id, user_id=data['id'])
                return User(
                    id=data['id'],
                    email=data['email'],
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
                    name=data.get('name'),
                    google_id=data.get('google_id'),
                    avatar_url=data.get('avatar_url'),
                    auth_method=data.get('auth_method')
                )
            return None
            
        except Exception as e:
            logger.error("Failed to create user with Google", email=email, google_id=google_id, error=str(e))
            return None
    
    def get_user_subscription(self, email: str) -> Optional[Subscription]:
        """Get active subscription for user"""
        try:
            # Join users and subscriptions tables
            response = self.supabase.table('subscriptions').select(
                '*, users!inner(email)'
            ).eq('users.email', email).eq('status', 'active').execute()
            
            if response.data:
                data = response.data[0]
                expires_at = None
                if data['expires_at']:
                    expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
                
                return Subscription(
                    id=data['id'],
                    user_id=data['user_id'],
                    plan_id=data['plan_id'],
                    status=data['status'],
                    started_at=datetime.fromisoformat(data['started_at'].replace('Z', '+00:00')),
                    expires_at=expires_at,
                    mercadopago_subscription_id=data.get('mercadopago_subscription_id')
                )
            return None
            
        except Exception as e:
            logger.error("Failed to get user subscription", email=email, error=str(e))
            return None
    
    def get_subscription_plan(self, plan_id: int) -> Optional[SubscriptionPlan]:
        """Get subscription plan by ID"""
        try:
            response = self.supabase.table('subscription_plans').select('*').eq('id', plan_id).execute()
            
            if response.data:
                data = response.data[0]
                return SubscriptionPlan(
                    id=data['id'],
                    name=data['name'],
                    display_name=data['display_name'],
                    price_soles=float(data['price_soles']),
                    frequency_hours=data['frequency_hours'],
                    max_emails_per_day=data['max_emails_per_day'],
                    description=data['description'],
                    is_active=data['is_active']
                )
            return None
            
        except Exception as e:
            logger.error("Failed to get subscription plan", plan_id=plan_id, error=str(e))
            return None
    
    def get_all_active_subscribers(self) -> List[Dict[str, any]]:
        """Get all users with active subscriptions and their plan details"""
        try:
            response = self.supabase.table('subscriptions').select(
                '*, users!inner(email), subscription_plans!inner(*)'
            ).eq('status', 'active').execute()
            
            subscribers = []
            for data in response.data:
                subscribers.append({
                    'email': data['users']['email'],
                    'frequency_hours': data['subscription_plans']['frequency_hours'],
                    'plan_name': data['subscription_plans']['name'],
                    'max_emails_per_day': data['subscription_plans']['max_emails_per_day']
                })
            
            logger.info("Retrieved active subscribers", count=len(subscribers))
            return subscribers
            
        except Exception as e:
            logger.error("Failed to get active subscribers", error=str(e))
            return []
    
    def create_free_subscription(self, email: str) -> bool:
        """Create free subscription for new user (NEW 2025 MODEL)"""
        try:
            # Get or create user
            user = self.get_user_by_email(email)
            if not user:
                user = self.create_user(email)
            
            if not user:
                return False
            
            # Create free subscription (plan_id = 0 = 3/semana L-M-V deliverability-safe)
            response = self.supabase.table('subscriptions').insert({
                'user_id': user.id,
                'plan_id': 0,  # Plan 0 = free plan (56h = 3/semana L-M-V)
                'status': 'active'
            }).execute()
            
            if response.data:
                logger.info("Free subscription created", email=email, user_id=user.id)
                return True
            return False
            
        except Exception as e:
            logger.error("Failed to create free subscription", email=email, error=str(e))
            return False

# Global instance
db = None

def get_db() -> SupabaseManager:
    """Get database manager instance"""
    global db
    if db is None:
        db = SupabaseManager()
    return db