-- SCHEMA SIMPLE PARA FRASES CON UUID
-- Ejecutar en Supabase SQL Editor

CREATE TABLE phrases (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    text TEXT NOT NULL,
    author VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índice para búsquedas por autor
CREATE INDEX idx_phrases_author ON phrases(author);

-- Comentarios para documentación
COMMENT ON TABLE phrases IS 'Frases motivacionales para el sistema de emails';
COMMENT ON COLUMN phrases.text IS 'Contenido completo de la frase';
COMMENT ON COLUMN phrases.author IS 'Autor de la frase';