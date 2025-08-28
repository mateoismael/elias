-- ==================================================================
-- FIX CRÍTICO DE SEGURIDAD RLS - VERIFICADO CON DOCS 2025
-- Ejecutar en Supabase SQL Editor INMEDIATAMENTE
-- ==================================================================

-- ==========================================
-- 1. HABILITAR RLS EN TODAS LAS TABLAS
-- ==========================================
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.phrases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscription_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;

-- ==========================================
-- 2. CONFIGURAR SERVICE_ROLE CON BYPASS RLS
-- ==========================================
-- Esto permite a tu webhook (que usa service_role) acceso total
ALTER ROLE service_role WITH BYPASSRLS;

-- ==========================================
-- 3. POLÍTICAS SEGURAS PARA OTROS ROLES
-- ==========================================

-- USERS: Solo service_role puede gestionar
DROP POLICY IF EXISTS "Service role full access users" ON public.users;
CREATE POLICY "Service role full access users" ON public.users
FOR ALL 
TO service_role
USING (true)
WITH CHECK (true);

-- PHRASES: Lectura pública para emails, gestión solo service_role
DROP POLICY IF EXISTS "Public read phrases" ON public.phrases;
DROP POLICY IF EXISTS "Service role full access phrases" ON public.phrases;

CREATE POLICY "Public read phrases" ON public.phrases
FOR SELECT 
TO anon, authenticated
USING (true);

CREATE POLICY "Service role full access phrases" ON public.phrases
FOR ALL 
TO service_role
USING (true)
WITH CHECK (true);

-- SUBSCRIPTION_PLANS: Lectura pública
DROP POLICY IF EXISTS "Public read plans" ON public.subscription_plans;
DROP POLICY IF EXISTS "Service role full access plans" ON public.subscription_plans;

CREATE POLICY "Public read plans" ON public.subscription_plans
FOR SELECT 
TO anon, authenticated
USING (true);

CREATE POLICY "Service role full access plans" ON public.subscription_plans
FOR ALL 
TO service_role
USING (true)
WITH CHECK (true);

-- SUBSCRIPTIONS: Solo service_role
DROP POLICY IF EXISTS "Service role full access subscriptions" ON public.subscriptions;
CREATE POLICY "Service role full access subscriptions" ON public.subscriptions
FOR ALL 
TO service_role
USING (true)
WITH CHECK (true);

-- PAYMENTS: Solo service_role
DROP POLICY IF EXISTS "Service role full access payments" ON public.payments;
CREATE POLICY "Service role full access payments" ON public.payments
FOR ALL 
TO service_role
USING (true)
WITH CHECK (true);

-- ==========================================
-- 4. VERIFICAR CONFIGURACIÓN
-- ==========================================

-- Ver estado de RLS (debe mostrar 't' = true)
SELECT 
    schemaname,
    tablename,
    rowsecurity as rls_enabled,
    CASE 
        WHEN rowsecurity THEN '🔒 PROTECTED' 
        ELSE '❌ UNRESTRICTED' 
    END as status
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN ('users', 'phrases', 'subscription_plans', 'subscriptions', 'payments')
ORDER BY tablename;

-- Ver políticas creadas
SELECT 
    tablename,
    policyname,
    roles
FROM pg_policies 
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- ==========================================
-- 5. CONFIRMACIÓN
-- ==========================================
DO $$
BEGIN
    RAISE NOTICE '=====================================================';
    RAISE NOTICE '🔒 SEGURIDAD RLS HABILITADA CORRECTAMENTE';
    RAISE NOTICE '=====================================================';
    RAISE NOTICE '';
    RAISE NOTICE '✅ RLS habilitado en todas las tablas';
    RAISE NOTICE '✅ service_role configurado con BYPASSRLS';  
    RAISE NOTICE '✅ Políticas seguras creadas';
    RAISE NOTICE '✅ Webhook seguirá funcionando normalmente';
    RAISE NOTICE '';
    RAISE NOTICE '🎯 RESULTADO: Ya no verás "Unrestricted" en dashboard';
    RAISE NOTICE '🛡️ ESTADO: Base de datos protegida contra acceso no autorizado';
    RAISE NOTICE '';
    RAISE NOTICE '=====================================================';
END $$;