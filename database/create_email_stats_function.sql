-- Crear función para incrementar estadísticas de email
-- Ejecutar en Supabase SQL Editor

CREATE OR REPLACE FUNCTION increment_user_email_stats(
    user_email_param TEXT,
    sent_at_param TIMESTAMPTZ
)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result_record RECORD;
BEGIN
    -- Update user statistics atomically
    UPDATE users 
    SET 
        total_emails_sent = COALESCE(total_emails_sent, 0) + 1,
        last_email_sent_at = sent_at_param,
        updated_at = NOW()
    WHERE email = user_email_param
    RETURNING 
        id, 
        email, 
        total_emails_sent, 
        last_email_sent_at
    INTO result_record;
    
    -- Check if user was found and updated
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User not found with email: %', user_email_param;
    END IF;
    
    -- Return success with updated stats
    RETURN json_build_object(
        'success', true,
        'user_id', result_record.id,
        'email', result_record.email,
        'total_emails_sent', result_record.total_emails_sent,
        'last_email_sent_at', result_record.last_email_sent_at,
        'updated_at', NOW()
    );
    
EXCEPTION
    WHEN OTHERS THEN
        -- Return error information
        RETURN json_build_object(
            'success', false,
            'error', SQLERRM,
            'email', user_email_param
        );
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION increment_user_email_stats(TEXT, TIMESTAMPTZ) TO authenticated;
GRANT EXECUTE ON FUNCTION increment_user_email_stats(TEXT, TIMESTAMPTZ) TO service_role;

-- Test the function
SELECT increment_user_email_stats('test@example.com', NOW());