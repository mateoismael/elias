#!/usr/bin/env python3
"""
Script de prueba para verificar el sistema de desuscripción
"""
import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Cargar variables de entorno
load_dotenv()

# Import Supabase
try:
    from supabase import create_client, Client
except ImportError:
    print("[ERROR] Supabase not installed. Run: pip install supabase")
    sys.exit(1)

# Colores para la terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def get_supabase():
    """Get Supabase client"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        print(f"{Colors.RED}❌ ERROR: SUPABASE_URL y SUPABASE_KEY son requeridos en .env{Colors.END}")
        sys.exit(1)
    
    return create_client(url, key)

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")

def test_unsubscribe_api(email: str, webhook_url: str = "https://elias-indol.vercel.app/unsubscribe"):
    """Test the unsubscribe API endpoint"""
    print_header(f"🧪 Testing Unsubscribe API for: {email}")
    
    try:
        print(f"\n📡 Sending POST request to: {webhook_url}")
        print(f"   Payload: {{'email': '{email}'}}")
        
        response = requests.post(
            webhook_url,
            json={'email': email},
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"{Colors.GREEN}✅ SUCCESS: {result.get('message', 'Desuscripción exitosa')}{Colors.END}")
            return True
            
        elif response.status_code == 404:
            result = response.json()
            print(f"{Colors.YELLOW}⚠️  NOT FOUND: {result.get('message', 'Email no encontrado')}{Colors.END}")
            return False
            
        else:
            result = response.json() if response.text else {'message': 'Unknown error'}
            print(f"{Colors.RED}❌ ERROR: {result.get('message', 'Error desconocido')}{Colors.END}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"{Colors.RED}❌ ERROR: Timeout - El servidor no respondió{Colors.END}")
        return False
        
    except requests.exceptions.ConnectionError:
        print(f"{Colors.RED}❌ ERROR: No se pudo conectar al servidor{Colors.END}")
        return False
        
    except Exception as e:
        print(f"{Colors.RED}❌ ERROR: {str(e)}{Colors.END}")
        return False

def verify_in_database(email: str):
    """Verify the subscription status in database"""
    print_header(f"🔍 Verificando en Base de Datos: {email}")
    
    supabase = get_supabase()
    
    # 1. Buscar usuario
    print(f"\n1️⃣  Buscando usuario...")
    try:
        user_response = supabase.table('users').select('*').eq('email', email).execute()
        
        if not user_response.data:
            print(f"{Colors.YELLOW}   ⚠️  Usuario NO encontrado{Colors.END}")
            return None
        
        user = user_response.data[0]
        print(f"{Colors.GREEN}   ✅ Usuario encontrado: {user['id']}{Colors.END}")
        
    except Exception as e:
        print(f"{Colors.RED}   ❌ Error: {e}{Colors.END}")
        return None
    
    # 2. Buscar suscripciones
    print(f"\n2️⃣  Buscando suscripciones...")
    try:
        subs_response = supabase.table('subscriptions').select(
            '*, subscription_plans!inner(*)'
        ).eq('user_id', user['id']).execute()
        
        if not subs_response.data:
            print(f"{Colors.YELLOW}   ⚠️  No hay suscripciones{Colors.END}")
            return 'no_subscription'
        
        # Contar suscripciones por estado
        active_count = 0
        cancelled_count = 0
        
        for sub in subs_response.data:
            if sub['status'] == 'active':
                active_count += 1
                print(f"{Colors.YELLOW}   ⚠️  Suscripción ACTIVA encontrada (ID: {sub['id'][:8]}...){Colors.END}")
            elif sub['status'] == 'cancelled':
                cancelled_count += 1
                print(f"{Colors.GREEN}   ✅ Suscripción CANCELADA (ID: {sub['id'][:8]}...){Colors.END}")
        
        print(f"\n   📊 Resumen:")
        print(f"      - Activas: {active_count}")
        print(f"      - Canceladas: {cancelled_count}")
        
        if active_count > 0:
            return 'has_active'
        elif cancelled_count > 0:
            return 'all_cancelled'
        else:
            return 'unknown_status'
            
    except Exception as e:
        print(f"{Colors.RED}   ❌ Error: {e}{Colors.END}")
        return None

def create_test_subscription(email: str, frequency_hours: int = 24):
    """Create a test subscription for testing unsubscribe"""
    print_header(f"➕ Creando suscripción de prueba: {email}")
    
    supabase = get_supabase()
    
    # Mapeo de frecuencias
    frequency_map = {1: 4, 3: 3, 6: 2, 24: 1}
    plan_id = frequency_map.get(frequency_hours, 1)
    
    try:
        # 1. Crear o obtener usuario
        user_response = supabase.table('users').select('*').eq('email', email).execute()
        
        if not user_response.data:
            print(f"   Creando nuevo usuario...")
            create_response = supabase.table('users').insert({'email': email}).execute()
            if not create_response.data:
                print(f"{Colors.RED}   ❌ Error creando usuario{Colors.END}")
                return False
            user = create_response.data[0]
            print(f"{Colors.GREEN}   ✅ Usuario creado{Colors.END}")
        else:
            user = user_response.data[0]
            print(f"   ✅ Usuario existente encontrado")
        
        # 2. Cancelar suscripciones previas
        print(f"   Cancelando suscripciones previas...")
        cancel_response = supabase.table('subscriptions').update({
            'status': 'cancelled',
            'cancelled_at': datetime.utcnow().isoformat()
        }).eq('user_id', user['id']).eq('status', 'active').execute()
        
        if cancel_response.data:
            print(f"   ✅ {len(cancel_response.data)} suscripción(es) cancelada(s)")
        
        # 3. Crear nueva suscripción activa
        print(f"   Creando nueva suscripción activa...")
        new_sub = supabase.table('subscriptions').insert({
            'user_id': user['id'],
            'plan_id': plan_id,
            'status': 'active',
            'started_at': datetime.utcnow().isoformat()
        }).execute()
        
        if new_sub.data:
            print(f"{Colors.GREEN}   ✅ Suscripción activa creada exitosamente{Colors.END}")
            return True
        else:
            print(f"{Colors.RED}   ❌ Error creando suscripción{Colors.END}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}   ❌ Error: {e}{Colors.END}")
        return False

def run_complete_test(test_email: str):
    """Run a complete test cycle"""
    print_header(f"🚀 PRUEBA COMPLETA DEL SISTEMA DE UNSUBSCRIBE")
    print(f"   Email de prueba: {test_email}")
    
    # Paso 1: Crear suscripción de prueba
    print(f"\n{Colors.BOLD}PASO 1: Preparar datos de prueba{Colors.END}")
    if not create_test_subscription(test_email):
        print(f"{Colors.RED}❌ No se pudo crear la suscripción de prueba{Colors.END}")
        return False
    
    input(f"\n{Colors.YELLOW}Presiona Enter para continuar con la desuscripción...{Colors.END}")
    
    # Paso 2: Verificar estado inicial
    print(f"\n{Colors.BOLD}PASO 2: Verificar estado inicial{Colors.END}")
    initial_status = verify_in_database(test_email)
    if initial_status != 'has_active':
        print(f"{Colors.YELLOW}⚠️  Estado inesperado: {initial_status}{Colors.END}")
    
    input(f"\n{Colors.YELLOW}Presiona Enter para ejecutar la desuscripción...{Colors.END}")
    
    # Paso 3: Ejecutar desuscripción
    print(f"\n{Colors.BOLD}PASO 3: Ejecutar desuscripción via API{Colors.END}")
    unsubscribe_success = test_unsubscribe_api(test_email)
    
    if not unsubscribe_success:
        print(f"{Colors.RED}❌ La desuscripción falló{Colors.END}")
        return False
    
    # Paso 4: Verificar estado final
    print(f"\n{Colors.BOLD}PASO 4: Verificar estado final{Colors.END}")
    final_status = verify_in_database(test_email)
    
    # Resultado final
    print_header("📊 RESULTADO DE LA PRUEBA")
    if final_status == 'all_cancelled':
        print(f"{Colors.GREEN}✅ PRUEBA EXITOSA: La suscripción fue cancelada correctamente{Colors.END}")
        return True
    elif final_status == 'has_active':
        print(f"{Colors.RED}❌ PRUEBA FALLIDA: Aún hay suscripciones activas{Colors.END}")
        return False
    else:
        print(f"{Colors.YELLOW}⚠️  RESULTADO INCONCLUSO: Estado final = {final_status}{Colors.END}")
        return False

def test_edge_cases():
    """Test edge cases for unsubscribe"""
    print_header("🔬 PRUEBAS DE CASOS EDGE")
    
    test_cases = [
        {
            'name': 'Email no existente',
            'email': 'noexiste@ejemplo.com',
            'expected_status': 404
        },
        {
            'name': 'Email inválido',
            'email': 'invalido',
            'expected_status': 400
        },
        {
            'name': 'Email vacío',
            'email': '',
            'expected_status': 400
        },
        {
            'name': 'Email con espacios',
            'email': '  test@ejemplo.com  ',
            'expected_status': 404  # Should be trimmed and processed
        }
    ]
    
    webhook_url = "https://elias-indol.vercel.app/unsubscribe"
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{Colors.BOLD}Test {i}: {test_case['name']}{Colors.END}")
        print(f"   Email: '{test_case['email']}'")
        
        try:
            response = requests.post(
                webhook_url,
                json={'email': test_case['email']},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == test_case['expected_status']:
                print(f"{Colors.GREEN}   ✅ PASS: Status {response.status_code} como esperado{Colors.END}")
            else:
                print(f"{Colors.RED}   ❌ FAIL: Status {response.status_code}, esperado {test_case['expected_status']}{Colors.END}")
                
        except Exception as e:
            print(f"{Colors.RED}   ❌ ERROR: {str(e)}{Colors.END}")

def main():
    """Main menu"""
    print(f"\n{Colors.BOLD}🔧 SISTEMA DE PRUEBAS - UNSUBSCRIBE{Colors.END}")
    print("=" * 60)
    
    while True:
        print("\n¿Qué deseas hacer?")
        print("1. Prueba completa con email de test")
        print("2. Solo verificar API de unsubscribe")
        print("3. Solo verificar estado en base de datos")
        print("4. Crear suscripción de prueba")
        print("5. Probar casos edge (emails inválidos, etc)")
        print("6. Salir")
        
        choice = input(f"\n{Colors.YELLOW}Selecciona una opción (1-6): {Colors.END}").strip()
        
        if choice == '1':
            email = input("Email de prueba (o Enter para usar test@ejemplo.com): ").strip()
            if not email:
                email = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@ejemplo.com"
                print(f"Usando email temporal: {email}")
            run_complete_test(email)
            
        elif choice == '2':
            email = input("Email a desuscribir: ").strip().lower()
            if email:
                test_unsubscribe_api(email)
                
        elif choice == '3':
            email = input("Email a verificar: ").strip().lower()
            if email:
                verify_in_database(email)
                
        elif choice == '4':
            email = input("Email para crear suscripción: ").strip().lower()
            if email:
                freq = input("Frecuencia en horas (1/3/6/24): ").strip()
                freq_hours = int(freq) if freq in ['1', '3', '6', '24'] else 24
                create_test_subscription(email, freq_hours)
                
        elif choice == '5':
            test_edge_cases()
            
        elif choice == '6':
            print(f"\n{Colors.GREEN}👋 ¡Hasta luego!{Colors.END}")
            break
            
        else:
            print(f"{Colors.RED}❌ Opción inválida{Colors.END}")

if __name__ == "__main__":
    main()