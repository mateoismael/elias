# 📂 Database Schema - Pseudosapiens

Esta carpeta contiene los esquemas SQL para la base de datos Supabase de Pseudosapiens.

## 📋 Archivos Activos

### ✅ `updated_freemium_schema_2025.sql`
**Esquema principal actualizado (2025)**
- Define la estructura completa de la base de datos
- Incluye planes optimizados: Plan 0 (Gratuito) y Plan 1 (Premium Básico)
- Configuración de precios y frecuencias
- **Estado**: ✅ Aplicado en producción

### ✅ `google_auth_schema.sql` 
**Extensión para autenticación Google**
- Añade campos para Google OAuth: `name`, `google_id`, `avatar_url`, `auth_method`
- Mejora la tabla `users` para soporte completo de Google Sign-In
- **Estado**: ✅ Aplicado en producción

## 🗃️ Estructura de Base de Datos Actual

```sql
-- Tablas principales:
users                  (16 registros)
subscription_plans     (6 planes, 2 activos)
subscriptions         (19 registros, 15 activos)
user_phrase_history   (195 frases enviadas)
phrases              (201 frases disponibles)
```

## 🎯 Planes Activos

- **Plan 0**: Gratuito - 3 frases/semana - S/ 0.00
- **Plan 1**: Premium Básico - 1 frase/día - S/ 5.00

## 📝 Notas de Mantenimiento

- ❌ **Archivos eliminados**: Esquemas obsoletos que no coincidían con la estructura real
- ✅ **Estado actual**: Base de datos limpia y funcional
- 🔄 **Última actualización**: Septiembre 16, 2025

## 🚀 Uso

Para aplicar cambios a la base de datos:
1. Conectar a Supabase SQL Editor
2. Ejecutar `updated_freemium_schema_2025.sql` (si es instalación nueva)
3. Ejecutar `google_auth_schema.sql` (si no se han aplicado los campos de Google Auth)

---
*Documentación generada automáticamente - Pseudosapiens 2025*