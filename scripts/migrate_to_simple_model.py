#!/usr/bin/env python3
"""
Script para migrar al modelo freemium simplificado
GRATIS (6h) vs PREMIUM S/5 (todas las demás)
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Import database module
try:
    from database import get_db
except ImportError:
    print("[ERROR] Database module not found.")
    sys.exit(1)

def main():
    """Migrar todos los usuarios al modelo simplificado"""
    
    print("[INFO] MIGRACION AL MODELO SIMPLIFICADO")
    print("[INFO] GRATIS (6h) vs PREMIUM S/5.00 (todas las demas)")
    print("-" * 60)
    
    try:
        # Conectar a Supabase
        db = get_db()
        supabase = db.supabase
        
        # PASO 1: Mostrar estado actual
        print("\n[STEP 1] Estado actual:")
        current_response = supabase.table('subscriptions').select(
            '*, users!inner(email), subscription_plans!inner(name, display_name, frequency_hours, price_soles)'
        ).eq('status', 'active').execute()
        
        current_plans = {}
        for sub in current_response.data:
            plan_name = sub['subscription_plans']['display_name']
            frequency = sub['subscription_plans']['frequency_hours'] 
            price = sub['subscription_plans']['price_soles']
            current_plans[plan_name] = current_plans.get(plan_name, 0) + 1
            print(f"  {sub['users']['email']:<35} | {plan_name:<12} | {frequency:>2}h | S/ {price}")
        
        print(f"\n[CURRENT] Distribucion por plan:")
        for plan, count in current_plans.items():
            print(f"   {plan}: {count} usuarios")
        
        # PASO 2: Actualizar schema de planes
        print(f"\n[STEP 2] Actualizando schema de planes...")
        
        # Actualizar plan de 6 horas a GRATUITO
        supabase.table('subscription_plans').update({
            'name': 'free',
            'display_name': 'Gratuito', 
            'price_soles': 0.00,
            'description': 'Recibe 3 frases motivacionales cada día'
        }).eq('frequency_hours', 6).execute()
        print("  [OK] Plan 6h -> Gratuito (S/ 0.00)")
        
        # Actualizar plan de 24 horas a PREMIUM
        supabase.table('subscription_plans').update({
            'name': 'premium_daily',
            'display_name': 'Premium', 
            'price_soles': 5.00,
            'description': 'Acceso completo: elige cualquier frecuencia'
        }).eq('frequency_hours', 24).execute()
        print("  [OK] Plan 24h -> Premium (S/ 5.00)")
        
        # Actualizar plan de 3 horas a PREMIUM
        supabase.table('subscription_plans').update({
            'name': 'premium_3h',
            'display_name': 'Premium', 
            'price_soles': 5.00,
            'description': 'Acceso completo: elige cualquier frecuencia'
        }).eq('frequency_hours', 3).execute()
        print("  [OK] Plan 3h -> Premium (S/ 5.00)")
        
        # Actualizar plan de 1 hora a PREMIUM
        supabase.table('subscription_plans').update({
            'name': 'premium_1h',
            'display_name': 'Premium', 
            'price_soles': 5.00,
            'description': 'Acceso completo: elige cualquier frecuencia'
        }).eq('frequency_hours', 1).execute()
        print("  [OK] Plan 1h -> Premium (S/ 5.00)")
        
        # PASO 3: Migrar usuarios no-gratuitos al plan gratuito
        print(f"\n[STEP 3] Migrando usuarios a plan gratuito...")
        
        # Obtener ID del plan gratuito (6h)
        free_plan_response = supabase.table('subscription_plans').select('id').eq('frequency_hours', 6).execute()
        if not free_plan_response.data:
            print("[ERROR] No se encontro plan gratuito")
            return 1
        free_plan_id = free_plan_response.data[0]['id']
        print(f"  [INFO] Plan gratuito ID: {free_plan_id}")
        
        # Migrar TODOS los usuarios al plan gratuito (temporalmente)
        update_response = supabase.table('subscriptions').update({
            'plan_id': free_plan_id,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('status', 'active').execute()
        
        migrated_count = len(update_response.data) if update_response.data else 0
        print(f"  [OK] {migrated_count} usuarios migrados al plan gratuito")
        
        # PASO 4: Mostrar estado final
        print(f"\n[STEP 4] Estado final:")
        final_response = supabase.table('subscriptions').select(
            '*, users!inner(email), subscription_plans!inner(name, display_name, frequency_hours, price_soles)'
        ).eq('status', 'active').execute()
        
        final_plans = {}
        for sub in final_response.data:
            plan_name = sub['subscription_plans']['display_name']
            frequency = sub['subscription_plans']['frequency_hours']
            price = sub['subscription_plans']['price_soles'] 
            final_plans[plan_name] = final_plans.get(plan_name, 0) + 1
            print(f"  {sub['users']['email']:<35} | {plan_name:<12} | {frequency:>2}h | S/ {price}")
        
        print(f"\n[FINAL] Distribucion por plan:")
        for plan, count in final_plans.items():
            print(f"   {plan}: {count} usuarios")
        
        print(f"\n[SUCCESS] Migracion completada:")
        print(f"  - TODOS los usuarios estan en plan GRATUITO (6h, 3 frases/dia)")
        print(f"  - Schema actualizado para modelo simplificado")
        print(f"  - Listo para implementar pagos Premium (S/ 5.00)")
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Error durante migracion: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())