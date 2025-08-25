#!/usr/bin/env python3
"""
Script de diagnóstico para verificar el sistema de cambio de frecuencias
"""
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Import Supabase
try:
    from supabase import create_client, Client
except ImportError:
    print("[ERROR] Supabase not installed. Run: pip install supabase")
    sys.exit(1)

def get_supabase():
    """Get Supabase client"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        print("❌ ERROR: SUPABASE_URL y SUPABASE_KEY son requeridos en .env")
        sys.exit(1)
    
    return create_client(url, key)

def diagnose_user(email: str):
    """Diagnosticar el estado de un usuario específico"""
    print(f"\n🔍 Diagnosticando usuario: {email}")
    print("=" * 60)
    
    supabase = get_supabase()
    
    # 1. Buscar usuario
    print("\n1️⃣ Buscando usuario en la tabla 'users'...")
    try:
        user_response = supabase.table('users').select('*').eq('email', email).execute()
        
        if not user_response.data:
            print(f"   ❌ Usuario NO encontrado con email: {email}")
            print("   ℹ️  El usuario necesita ser creado primero")
            return None
        
        user = user_response.data[0]
        print(f"   ✅ Usuario encontrado:")
        print(f"      - ID: {user['id']}")
        print(f"      - Email: {user['email']}")
        print(f"      - Creado: {user['created_at']}")
        
    except Exception as e:
        print(f"   ❌ Error buscando usuario: {e}")
        return None
    
    # 2. Buscar suscripciones
    print("\n2️⃣ Buscando suscripciones del usuario...")
    try:
        subs_response = supabase.table('subscriptions').select(
            '*, subscription_plans!inner(*)'
        ).eq('user_id', user['id']).execute()
        
        if not subs_response.data:
            print(f"   ⚠️  No hay suscripciones para este usuario")
            print(f"   ℹ️  Se necesita crear una nueva suscripción")
            return user
        
        print(f"   📋 Total de suscripciones encontradas: {len(subs_response.data)}")
        
        for i, sub in enumerate(subs_response.data, 1):
            plan = sub['subscription_plans']
            print(f"\n   Suscripción #{i}:")
            print(f"      - ID: {sub['id']}")
            print(f"      - Estado: {sub['status']} {'✅' if sub['status'] == 'active' else '❌'}")
            print(f"      - Plan: {plan['name']} (ID: {plan['id']})")
            print(f"      - Frecuencia: Cada {plan['frequency_hours']} hora(s)")
            print(f"      - Emails/día: {plan['max_emails_per_day']}")
            print(f"      - Precio: S/. {plan['price_soles']}")
            print(f"      - Iniciada: {sub['started_at']}")
            if sub.get('cancelled_at'):
                print(f"      - Cancelada: {sub['cancelled_at']}")
                
    except Exception as e:
        print(f"   ❌ Error buscando suscripciones: {e}")
        return user
    
    # 3. Verificar suscripción activa
    print("\n3️⃣ Verificando suscripción ACTIVA...")
    try:
        active_response = supabase.table('subscriptions').select(
            '*, subscription_plans!inner(*)'
        ).eq('user_id', user['id']).eq('status', 'active').execute()
        
        if not active_response.data:
            print(f"   ⚠️  NO hay suscripción activa")
            print(f"   ℹ️  Esto explica por qué no puede cambiar de plan")
            print(f"   💡 SOLUCIÓN: Se debe crear una nueva suscripción activa")
        else:
            active_sub = active_response.data[0]
            plan = active_sub['subscription_plans']
            print(f"   ✅ Suscripción activa encontrada:")
            print(f"      - Plan actual: {plan['name']}")
            print(f"      - Frecuencia: Cada {plan['frequency_hours']} hora(s)")
            
    except Exception as e:
        print(f"   ❌ Error verificando suscripción activa: {e}")
    
    return user

def fix_user_subscription(email: str, new_frequency: str):
    """Reparar/crear suscripción para un usuario"""
    print(f"\n🔧 Reparando suscripción para: {email}")
    print(f"   Nueva frecuencia deseada: cada {new_frequency} hora(s)")
    print("=" * 60)
    
    supabase = get_supabase()
    
    # Mapeo de frecuencias a plan_id
    frequency_map = {
        '1': 4,   # Intensivo
        '3': 3,   # Pro
        '6': 2,   # Premium
        '24': 1,  # Gratuito
    }
    
    plan_id = frequency_map.get(new_frequency)
    if not plan_id:
        print(f"❌ Frecuencia inválida: {new_frequency}")
        print("   Valores válidos: 1, 3, 6, 24")
        return False
    
    # 1. Obtener o crear usuario
    user_response = supabase.table('users').select('*').eq('email', email).execute()
    
    if not user_response.data:
        print("📝 Creando nuevo usuario...")
        create_response = supabase.table('users').insert({'email': email}).execute()
        if not create_response.data:
            print("❌ Error creando usuario")
            return False
        user = create_response.data[0]
        print(f"✅ Usuario creado con ID: {user['id']}")
    else:
        user = user_response.data[0]
        print(f"✅ Usuario existente encontrado: {user['id']}")
    
    # 2. Cancelar suscripciones activas previas
    print("\n🔄 Cancelando suscripciones activas previas...")
    cancel_response = supabase.table('subscriptions').update({
        'status': 'cancelled',
        'cancelled_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }).eq('user_id', user['id']).eq('status', 'active').execute()
    
    if cancel_response.data:
        print(f"   ✅ Canceladas {len(cancel_response.data)} suscripción(es) previa(s)")
    
    # 3. Crear nueva suscripción
    print(f"\n📋 Creando nueva suscripción con plan_id={plan_id}...")
    new_sub_response = supabase.table('subscriptions').insert({
        'user_id': user['id'],
        'plan_id': plan_id,
        'status': 'active',
        'started_at': datetime.utcnow().isoformat()
    }).execute()
    
    if not new_sub_response.data:
        print("❌ Error creando nueva suscripción")
        return False
    
    print(f"✅ Nueva suscripción creada exitosamente")
    print(f"   - ID: {new_sub_response.data[0]['id']}")
    print(f"   - Plan ID: {plan_id}")
    print(f"   - Frecuencia: cada {new_frequency} hora(s)")
    
    return True

def list_all_active_subscribers():
    """Listar todos los suscriptores activos"""
    print("\n📊 Lista de todos los suscriptores activos")
    print("=" * 60)
    
    supabase = get_supabase()
    
    try:
        response = supabase.table('subscriptions').select(
            '*, users!inner(email), subscription_plans!inner(*)'
        ).eq('status', 'active').execute()
        
        if not response.data:
            print("No hay suscriptores activos")
            return
        
        print(f"Total: {len(response.data)} suscriptores activos\n")
        
        # Agrupar por plan
        by_plan = {}
        for sub in response.data:
            plan_name = sub['subscription_plans']['name']
            if plan_name not in by_plan:
                by_plan[plan_name] = []
            by_plan[plan_name].append(sub['users']['email'])
        
        for plan_name, emails in sorted(by_plan.items()):
            print(f"\n📋 Plan: {plan_name} ({len(emails)} usuarios)")
            for email in sorted(emails)[:5]:  # Mostrar máximo 5 por plan
                print(f"   - {email}")
            if len(emails) > 5:
                print(f"   ... y {len(emails) - 5} más")
                
    except Exception as e:
        print(f"❌ Error listando suscriptores: {e}")

def main():
    """Menú principal del diagnóstico"""
    print("\n🔧 SISTEMA DE DIAGNÓSTICO - Pseudosapiens")
    print("=" * 60)
    
    while True:
        print("\n¿Qué deseas hacer?")
        print("1. Diagnosticar un usuario específico")
        print("2. Reparar/crear suscripción para un usuario")
        print("3. Listar todos los suscriptores activos")
        print("4. Probar cambio de frecuencia (1→3→6→24→1)")
        print("5. Salir")
        
        choice = input("\nSelecciona una opción (1-5): ").strip()
        
        if choice == '1':
            email = input("Ingresa el email del usuario: ").strip().lower()
            if email:
                diagnose_user(email)
        
        elif choice == '2':
            email = input("Ingresa el email del usuario: ").strip().lower()
            if email:
                print("\nFrecuencias disponibles:")
                print("  1 = Cada hora (Intensivo)")
                print("  3 = Cada 3 horas (Pro)")
                print("  6 = Cada 6 horas (Premium)")
                print("  24 = Una vez al día (Gratuito)")
                freq = input("Nueva frecuencia (1/3/6/24): ").strip()
                if freq in ['1', '3', '6', '24']:
                    fix_user_subscription(email, freq)
                else:
                    print("❌ Frecuencia inválida")
        
        elif choice == '3':
            list_all_active_subscribers()
        
        elif choice == '4':
            email = input("Ingresa el email para prueba: ").strip().lower()
            if email:
                print("\n🧪 Iniciando prueba de cambio de frecuencias...")
                frequencies = ['1', '3', '6', '24', '1']
                for freq in frequencies:
                    print(f"\n➡️  Cambiando a frecuencia: {freq} hora(s)")
                    success = fix_user_subscription(email, freq)
                    if not success:
                        print("❌ Prueba fallida")
                        break
                    input("Presiona Enter para continuar...")
                print("\n✅ Prueba completada")
        
        elif choice == '5':
            print("\n👋 ¡Hasta luego!")
            break
        
        else:
            print("❌ Opción inválida")

if __name__ == "__main__":
    main()