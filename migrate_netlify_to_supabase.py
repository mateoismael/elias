#!/usr/bin/env python3
"""
Script para migrar suscriptores existentes de Netlify Forms a Supabase
Solo se ejecuta una vez para la migración inicial
"""
import os
import sys
from dotenv import load_dotenv
import structlog

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio scripts al path
sys.path.append('scripts')

from database import get_db
from send_emails import get_subscribers_from_netlify, NetlifyConfig

# Configure logging
logging = structlog.get_logger()

def migrate_netlify_subscribers():
    """Migrar todos los suscriptores de Netlify a Supabase"""
    
    print("[*] Iniciando migración de Netlify a Supabase...")
    
    try:
        # Configurar Netlify
        netlify_config = NetlifyConfig.from_env()
        if not netlify_config.site_id or not netlify_config.access_token:
            print("[ERROR] Faltan credenciales de Netlify. Verifica NETLIFY_SITE_ID y NETLIFY_ACCESS_TOKEN")
            return False
        
        # Configurar Supabase
        db = get_db()
        
        # Obtener suscriptores de Netlify
        print("[*] Obteniendo suscriptores de Netlify...")
        netlify_subscribers = get_subscribers_from_netlify(netlify_config)
        
        if not netlify_subscribers:
            print("[WARN] No se encontraron suscriptores en Netlify")
            return True
        
        print(f"[OK] Encontrados {len(netlify_subscribers)} suscriptores en Netlify")
        
        # Migrar cada suscriptor
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for subscriber in netlify_subscribers:
            email = subscriber.email
            frequency_enum = subscriber.frequency
            
            # Mapear FrequencyEnum a plan_id
            if frequency_enum.value == 1:  # HOURLY
                plan_id = 4  # Intensivo
            elif frequency_enum.value == 3:  # EVERY_3_HOURS  
                plan_id = 3  # Pro
            elif frequency_enum.value == 6:  # EVERY_6_HOURS
                plan_id = 2  # Premium
            else:  # DAILY
                plan_id = 1  # Gratuito
            
            try:
                # Verificar si el usuario ya existe en Supabase
                existing_user = db.get_user_by_email(email)
                if existing_user:
                    print(f"[SKIP] Usuario ya existe: {email}")
                    skipped_count += 1
                    continue
                
                # Crear usuario
                user = db.create_user(email)
                if not user:
                    print(f"[ERROR] No se pudo crear usuario: {email}")
                    error_count += 1
                    continue
                
                # Crear suscripción con el plan correspondiente
                response = db.supabase.table('subscriptions').insert({
                    'user_id': user.id,
                    'plan_id': plan_id,
                    'status': 'active'
                }).execute()
                
                if response.data:
                    print(f"[OK] Migrado: {email} -> Plan {plan_id}")
                    migrated_count += 1
                else:
                    print(f"[ERROR] Error creando suscripción: {email}")
                    error_count += 1
                    
            except Exception as e:
                print(f"[ERROR] Error migrando {email}: {str(e)}")
                error_count += 1
                continue
        
        # Resumen de migración
        print(f"\n[SUMMARY] Migración completada:")
        print(f"  - Migrados: {migrated_count}")
        print(f"  - Ya existían: {skipped_count}")
        print(f"  - Errores: {error_count}")
        print(f"  - Total procesados: {len(netlify_subscribers)}")
        
        if error_count == 0:
            print(f"[SUCCESS] Migración exitosa!")
        else:
            print(f"[WARN] Migración completada con algunos errores")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error durante la migración: {str(e)}")
        return False

def verify_migration():
    """Verificar que la migración fue exitosa"""
    print("\n[*] Verificando migración...")
    
    try:
        db = get_db()
        
        # Contar suscriptores en Supabase
        supabase_subscribers = db.get_all_active_subscribers()
        print(f"[OK] Suscriptores activos en Supabase: {len(supabase_subscribers)}")
        
        # Mostrar distribución por plan
        plan_counts = {}
        for sub in supabase_subscribers:
            plan_name = sub['plan_name']
            plan_counts[plan_name] = plan_counts.get(plan_name, 0) + 1
        
        print("[INFO] Distribución por plan:")
        for plan, count in plan_counts.items():
            print(f"  - {plan}: {count} usuarios")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error verificando migración: {str(e)}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("MIGRACION NETLIFY -> SUPABASE")
    print("="*60)
    
    # Ejecutar migración
    success = migrate_netlify_subscribers()
    
    if success:
        # Verificar resultados
        verify_migration()
        print("\n[FINAL] Migración completada. Tu script ahora usará Supabase.")
    else:
        print("\n[FINAL] Error en la migración. Revisa los logs.")
    
    print("="*60)