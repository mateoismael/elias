#!/usr/bin/env python3
"""
Test script para verificar la conexión con Supabase
"""
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio scripts al path
sys.path.append('scripts')

from database import get_db

def test_supabase_connection():
    """Test básico de conexión a Supabase"""
    print("[*] Probando conexion a Supabase...")
    
    try:
        # Inicializar conexión
        db = get_db()
        print("[OK] Conexion a Supabase establecida")
        
        # Probar consulta a planes de suscripción
        print("\n[*] Consultando planes de suscripcion...")
        plans_response = db.supabase.table('subscription_plans').select('*').execute()
        
        if plans_response.data:
            print(f"[OK] Encontrados {len(plans_response.data)} planes:")
            for plan in plans_response.data:
                print(f"   - {plan['display_name']}: S/ {plan['price_soles']} ({plan['frequency_hours']}h)")
        else:
            print("[ERROR] No se encontraron planes. Ejecutaste el schema.sql?")
            return False
        
        # Probar crear usuario de prueba
        print("\n[*] Probando crear usuario de prueba...")
        test_email = "test@pseudosapiens.com"
        
        # Verificar si ya existe
        user = db.get_user_by_email(test_email)
        if user:
            print(f"[OK] Usuario ya existe: {user.email}")
        else:
            user = db.create_user(test_email)
            if user:
                print(f"[OK] Usuario creado: {user.email}")
            else:
                print("[ERROR] Error creando usuario")
                return False
        
        # Probar crear suscripción gratuita
        print("\n[*] Probando crear suscripcion gratuita...")
        success = db.create_free_subscription(test_email)
        if success:
            print("[OK] Suscripcion gratuita creada")
        else:
            print("[WARN] Error o suscripcion ya existe")
        
        # Verificar suscripción
        subscription = db.get_user_subscription(test_email)
        if subscription:
            plan = db.get_subscription_plan(subscription.plan_id)
            print(f"[OK] Suscripcion activa: {plan.display_name}")
        
        # Probar obtener todos los suscriptores
        print("\n[*] Consultando suscriptores activos...")
        subscribers = db.get_all_active_subscribers()
        print(f"[OK] Encontrados {len(subscribers)} suscriptores activos")
        
        for sub in subscribers[:3]:  # Mostrar solo los primeros 3
            print(f"   - {sub['email']}: {sub['plan_name']} (cada {sub['frequency_hours']}h)")
        
        print("\n[SUCCESS] Todas las pruebas pasaron! Supabase esta funcionando correctamente.")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        print("\n[INFO] Verifica que:")
        print("  1. Creaste el proyecto en Supabase")
        print("  2. Ejecutaste el schema.sql en el SQL Editor")
        print("  3. Copiaste correctamente SUPABASE_URL y SUPABASE_KEY")
        return False

if __name__ == "__main__":
    success = test_supabase_connection()
    sys.exit(0 if success else 1)