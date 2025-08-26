-- ACTUALIZACIÓN SCHEMA PARA GOOGLE SIGN-IN
-- Ejecutar en Supabase SQL Editor DESPUÉS del schema actual

-- Agregar campos para autenticación Google
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS name VARCHAR(255),
ADD COLUMN IF NOT EXISTS google_id VARCHAR(255) UNIQUE,
ADD COLUMN IF NOT EXISTS avatar_url TEXT,
ADD COLUMN IF NOT EXISTS auth_method VARCHAR(20) DEFAULT 'email';

-- Índice para búsquedas rápidas por Google ID
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
CREATE INDEX IF NOT EXISTS idx_users_auth_method ON users(auth_method);

-- Actualizar constraint para permitir email NULL si usa Google
ALTER TABLE users ALTER COLUMN email DROP NOT NULL;

-- Agregar constraint: debe tener email O google_id
ALTER TABLE users ADD CONSTRAINT users_auth_check 
CHECK (
  (email IS NOT NULL AND email != '') OR 
  (google_id IS NOT NULL AND google_id != '')
);

-- Ver estructura actualizada
\d users;

-- Comentarios para documentación:
COMMENT ON COLUMN users.google_id IS 'Google OAuth unique identifier (sub claim)';
COMMENT ON COLUMN users.name IS 'User full name from Google profile';
COMMENT ON COLUMN users.avatar_url IS 'Google profile picture URL';
COMMENT ON COLUMN users.auth_method IS 'Authentication method: email, google, or both';