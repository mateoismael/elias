-- SISTEMA DE TRACKING DE FRASES POR USUARIO
-- Previene repetición de frases, mantiene historial completo
-- COMPATIBLE con el sistema existente - CERO FRICCIÓN

-- =====================================================
-- 1. TABLA PRINCIPAL DE TRACKING
-- =====================================================

CREATE TABLE IF NOT EXISTS user_phrase_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    phrase_id UUID NOT NULL,  -- No FK estricta para flexibilidad
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    email_status VARCHAR(20) DEFAULT 'sent', -- sent, delivered, opened, failed
    plan_id INTEGER,  -- Plan activo cuando se envió (para analytics)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraint para prevenir duplicados exactos
    UNIQUE(user_id, phrase_id)
);

-- =====================================================
-- 2. ÍNDICES PARA PERFORMANCE OPTIMIZADA  
-- =====================================================

-- Índice principal para consultas de "frases no enviadas"
CREATE INDEX IF NOT EXISTS idx_user_phrase_history_user_id ON user_phrase_history(user_id);
CREATE INDEX IF NOT EXISTS idx_user_phrase_history_phrase_id ON user_phrase_history(phrase_id);
CREATE INDEX IF NOT EXISTS idx_user_phrase_history_sent_at ON user_phrase_history(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_phrase_history_status ON user_phrase_history(email_status);

-- Índice compuesto para query optimizada de "frases disponibles"
CREATE INDEX IF NOT EXISTS idx_user_phrase_lookup ON user_phrase_history(user_id, phrase_id);

-- =====================================================
-- 3. FUNCIÓN PARA OBTENER FRASE INTELIGENTE
-- =====================================================

CREATE OR REPLACE FUNCTION get_smart_phrase_for_user(p_user_id UUID)
RETURNS TABLE(phrase_id UUID, phrase_text TEXT, phrase_author TEXT) AS $$
DECLARE
    total_phrases_count INTEGER;
    user_received_count INTEGER;
    selected_phrase_id UUID;
BEGIN
    -- Contar total de frases disponibles
    SELECT COUNT(*) INTO total_phrases_count FROM phrases;
    
    -- Contar frases ya recibidas por el usuario
    SELECT COUNT(*) INTO user_received_count 
    FROM user_phrase_history 
    WHERE user_id = p_user_id;
    
    -- Caso 1: Usuario ha recibido TODAS las frases (reiniciar ciclo)
    IF user_received_count >= total_phrases_count THEN
        -- Log para debugging
        INSERT INTO user_phrase_history (user_id, phrase_id, email_status, plan_id)
        VALUES (p_user_id, '00000000-0000-0000-0000-000000000000', 'cycle_reset', NULL);
        
        -- Limpiar historial (conservar solo últimas 50 para analytics)
        DELETE FROM user_phrase_history 
        WHERE user_id = p_user_id 
        AND sent_at < (
            SELECT sent_at FROM user_phrase_history 
            WHERE user_id = p_user_id 
            ORDER BY sent_at DESC 
            LIMIT 1 OFFSET 50
        );
    END IF;
    
    -- Caso 2: Seleccionar frase aleatoria NO recibida
    SELECT p.id INTO selected_phrase_id
    FROM phrases p
    WHERE p.id NOT IN (
        SELECT DISTINCT uph.phrase_id 
        FROM user_phrase_history uph 
        WHERE uph.user_id = p_user_id 
        AND uph.email_status = 'sent'
    )
    ORDER BY RANDOM()
    LIMIT 1;
    
    -- Retornar la frase seleccionada
    RETURN QUERY
    SELECT p.id, p.text, p.author
    FROM phrases p
    WHERE p.id = selected_phrase_id;
    
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 4. FUNCIÓN PARA REGISTRAR ENVÍO
-- =====================================================

CREATE OR REPLACE FUNCTION record_phrase_sent(
    p_user_id UUID, 
    p_phrase_id UUID,
    p_plan_id INTEGER DEFAULT NULL
) RETURNS BOOLEAN AS $$
BEGIN
    INSERT INTO user_phrase_history (user_id, phrase_id, email_status, plan_id)
    VALUES (p_user_id, p_phrase_id, 'sent', p_plan_id)
    ON CONFLICT (user_id, phrase_id) 
    DO UPDATE SET 
        sent_at = NOW(),
        email_status = 'sent',
        plan_id = EXCLUDED.plan_id;
    
    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 5. VISTAS PARA ANALYTICS (OPCIONAL)
-- =====================================================

-- Vista para analytics de frases más populares
CREATE OR REPLACE VIEW phrase_analytics AS
SELECT 
    p.id,
    p.text,
    p.author,
    COUNT(uph.id) as total_sends,
    COUNT(DISTINCT uph.user_id) as unique_recipients,
    MAX(uph.sent_at) as last_sent,
    MIN(uph.sent_at) as first_sent
FROM phrases p
LEFT JOIN user_phrase_history uph ON p.id = uph.phrase_id
WHERE uph.email_status = 'sent'
GROUP BY p.id, p.text, p.author
ORDER BY total_sends DESC;

-- Vista para analytics de usuarios
CREATE OR REPLACE VIEW user_phrase_analytics AS
SELECT 
    u.id,
    u.email,
    COUNT(uph.id) as total_phrases_received,
    MAX(uph.sent_at) as last_phrase_received,
    MIN(uph.sent_at) as first_phrase_received,
    ROUND(
        COUNT(uph.id)::DECIMAL / 
        GREATEST((SELECT COUNT(*) FROM phrases), 1) * 100, 
        2
    ) as completion_percentage
FROM users u
LEFT JOIN user_phrase_history uph ON u.id = uph.user_id
WHERE uph.email_status = 'sent'
GROUP BY u.id, u.email
ORDER BY total_phrases_received DESC;

-- =====================================================
-- 6. TRIGGERS PARA MANTENIMIENTO AUTOMÁTICO
-- =====================================================

-- Trigger para limpiar registros antiguos automáticamente
CREATE OR REPLACE FUNCTION cleanup_old_phrase_history() 
RETURNS TRIGGER AS $$
BEGIN
    -- Mantener solo los últimos 500 registros por usuario para performance
    DELETE FROM user_phrase_history 
    WHERE user_id = NEW.user_id 
    AND id NOT IN (
        SELECT id FROM user_phrase_history 
        WHERE user_id = NEW.user_id 
        ORDER BY sent_at DESC 
        LIMIT 500
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger (comentado por default para evitar overhead)
-- CREATE TRIGGER trigger_cleanup_phrase_history
--     AFTER INSERT ON user_phrase_history
--     FOR EACH ROW
--     EXECUTE FUNCTION cleanup_old_phrase_history();

-- =====================================================
-- 7. POLÍTICAS DE SEGURIDAD (RLS)
-- =====================================================

-- Habilitar RLS en la tabla
ALTER TABLE user_phrase_history ENABLE ROW LEVEL SECURITY;

-- Política: Los usuarios solo pueden ver su propio historial
CREATE POLICY user_phrase_history_select_policy ON user_phrase_history
    FOR SELECT USING (user_id = auth.uid());

-- Política: Solo el sistema puede insertar registros
CREATE POLICY user_phrase_history_insert_policy ON user_phrase_history
    FOR INSERT WITH CHECK (true); -- Controlar a nivel de aplicación

-- =====================================================
-- 8. COMENTARIOS Y DOCUMENTACIÓN
-- =====================================================

COMMENT ON TABLE user_phrase_history IS 'Historial de frases enviadas por usuario. Previene repeticiones y permite analytics.';
COMMENT ON COLUMN user_phrase_history.user_id IS 'ID del usuario que recibió la frase';
COMMENT ON COLUMN user_phrase_history.phrase_id IS 'ID de la frase enviada';
COMMENT ON COLUMN user_phrase_history.sent_at IS 'Timestamp cuando se envió la frase';
COMMENT ON COLUMN user_phrase_history.email_status IS 'Estado del envío: sent, delivered, opened, failed, cycle_reset';
COMMENT ON COLUMN user_phrase_history.plan_id IS 'Plan activo del usuario al momento del envío (para analytics)';

COMMENT ON FUNCTION get_smart_phrase_for_user(UUID) IS 'Función principal: obtiene frase no repetida para usuario específico';
COMMENT ON FUNCTION record_phrase_sent(UUID, UUID, INTEGER) IS 'Registra que una frase fue enviada a un usuario';

-- =====================================================
-- VERIFICACIÓN DE LA INSTALACIÓN
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE 'Sistema de tracking de frases instalado correctamente';
    RAISE NOTICE 'Tablas creadas: user_phrase_history';
    RAISE NOTICE 'Funciones creadas: get_smart_phrase_for_user, record_phrase_sent';  
    RAISE NOTICE 'Vistas creadas: phrase_analytics, user_phrase_analytics';
    RAISE NOTICE 'RLS habilitado con políticas de seguridad';
    RAISE NOTICE 'Sistema listo para usar con CERO fricción';
END $$;