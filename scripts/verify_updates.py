#!/usr/bin/env python3
"""
Script para verificar el estado actual de frecuencias de usuarios
"""
import os
import sys
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
    """Verificar estado actual de todos los usuarios"""
    
    try:
        # Conectar a Supabase
        db = get_db()
        supabase = db.supabase
        
        # Obtener todos los usuarios con suscripciones activas
        response = supabase.table('subscriptions').select(
            '*, users!inner(email), subscription_plans!inner(name, display_name, frequency_hours)'
        ).eq('status', 'active').execute()
        
        if not response.data:
            print("[ERROR] No se encontraron suscripciones activas")
            return 1
        
        total_users = len(response.data)
        print(f"[INFO] Estado actual de {total_users} usuarios:")
        print(f"{'Email':<35} | {'Plan':<12} | {'Frecuencia':<10} | {'Frases/día'}")
        print("-" * 75)
        
        # Contar por plan
        plan_counts = {}
        
        for subscription in response.data:
            email = subscription['users']['email']
            plan_name = subscription['subscription_plans']['display_name']
            frequency_hours = subscription['subscription_plans']['frequency_hours']
            
            # Calcular frases por día
            if frequency_hours == 1:
                frases_per_day = "19"
            elif frequency_hours == 3:
                frases_per_day = "8" 
            elif frequency_hours == 6:
                frases_per_day = "3"
            elif frequency_hours == 24:
                frases_per_day = "1"
            else:
                frases_per_day = "?"
            
            print(f"{email:<35} | {plan_name:<12} | {frequency_hours:>2}h        | {frases_per_day}")
            
            # Contar por plan
            plan_counts[plan_name] = plan_counts.get(plan_name, 0) + 1
        
        print("-" * 75)
        print("[INFO] Resumen por plan:")
        for plan, count in plan_counts.items():
            print(f"   {plan}: {count} usuarios")
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())