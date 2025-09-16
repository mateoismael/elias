// Izipay Webhook Handler - Septiembre 2025
// Corrige verificación HMAC y parsing (kr-answer/kr-hash) según documentación Izipay V4
// - Acepta JSON (desde frontend) y x-www-form-urlencoded (IPN de Izipay)
// - Usa claves HMAC correctas (no la contraseña)
// - Actualiza pagos y suscripciones en Supabase
// - Responde en < 10s con 'OK' cuando todo está correcto

const crypto = require('crypto');

exports.handler = async (event, context) => {
  // CORS headers
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, Kr-Hash-Algorithm, Kr-Hash',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
  };

  // Handle preflight OPTIONS request
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  // Only allow POST requests
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'Method not allowed' }) };
  }

  const start = Date.now();

  try {
    const testMode = (process.env.IZIPAY_TEST_MODE || 'true').toLowerCase() === 'true';

    // Use the proper HMAC keys from Back Office (NOT the password)
    const hmacKey = testMode
      ? process.env.IZIPAY_HMAC_TEST_KEY
      : process.env.IZIPAY_HMAC_PROD_KEY;

    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_KEY;

    if (!hmacKey) {
      console.error('Missing HMAC key. Check IZIPAY_HMAC_TEST_KEY/IZIPAY_HMAC_PROD_KEY');
      return { statusCode: 500, headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'Missing HMAC key' }) };
    }

    if (!supabaseUrl || !supabaseKey) {
      console.warn('Missing Supabase env vars; proceeding without DB write');
    }

    // Parse incoming body
    const contentType = (event.headers['content-type'] || event.headers['Content-Type'] || '').toLowerCase();
    let formData = {};
    let krAnswerStr = '';
    let krHash = '';
    let krHashAlg = '';

    if (contentType.includes('application/x-www-form-urlencoded')) {
      // IPN from Izipay (server-to-server)
      const params = new URLSearchParams(event.body || '');
      for (const [k, v] of params.entries()) {
        formData[k] = v;
      }
      krAnswerStr = formData['kr-answer'] || '';
      krHash = formData['kr-hash'] || '';
      krHashAlg = (formData['kr-hash-algorithm'] || '').toLowerCase();
    } else {
      // JSON (from frontend validatePayment)
      let parsed = {};
      try {
        parsed = JSON.parse(event.body || '{}');
      } catch (_) {
        return { statusCode: 400, headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'Invalid JSON body' }) };
      }
      formData = parsed;
      krAnswerStr = typeof parsed['kr-answer'] === 'string' ? parsed['kr-answer'] : JSON.stringify(parsed['kr-answer'] || {});
      krHash = parsed['kr-hash'] || '';
      krHashAlg = (parsed['kr-hash-algorithm'] || '').toLowerCase();
    }

    // Validate required fields
    if (!krAnswerStr || !krHash) {
      console.error('Missing kr-answer or kr-hash');
      return { statusCode: 400, headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'Missing kr-answer or kr-hash' }) };
    }
    if (krHashAlg && krHashAlg !== 'sha256_hmac') {
      console.error('Unsupported kr-hash-algorithm:', krHashAlg);
      return { statusCode: 400, headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'Unsupported kr-hash-algorithm' }) };
    }

    // Compute expected HMAC on the EXACT kr-answer string
    const expectedHash = crypto.createHmac('sha256', hmacKey).update(krAnswerStr, 'utf8').digest('hex');

    // Compare case-insensitively
    if ((krHash || '').toLowerCase() !== expectedHash.toLowerCase()) {
      console.error('HMAC verification failed', { received: krHash?.slice(0, 12), expected: expectedHash.slice(0, 12) });
      return { statusCode: 401, headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'Invalid signature' }) };
    }

    // Parse kr-answer JSON
    let krAnswer;
    try {
      krAnswer = typeof formData['kr-answer'] === 'object'
        ? formData['kr-answer']
        : JSON.parse(krAnswerStr);
    } catch (e) {
      console.error('Invalid kr-answer JSON:', e.message);
      return { statusCode: 400, headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'Invalid kr-answer JSON' }) };
    }

    // Extract data
    const orderDetails = krAnswer.orderDetails || {};
    const customer = krAnswer.customer || {};
    const orderInfo = krAnswer.orderInfo || {};
    const transactions = Array.isArray(krAnswer.transactions) ? krAnswer.transactions : [];
    const tx = transactions[0] || {};

    const orderId = orderDetails.orderId || '';
    const orderStatus = krAnswer.orderStatus || tx.transactionStatusLabel || '';
    const transactionUuid = tx.uuid || '';
    const amount = tx.amount || 0; // cents
    const currency = tx.currency || 'PEN';
    const customerEmail = customer.email || '';

    console.log('[WEBHOOK] OK signature | order:', orderId, '| status:', orderStatus, '| email:', customerEmail);

    // Optionally persist payment + subscription
    if (supabaseUrl && supabaseKey && customerEmail) {
      await persistPaymentAndSubscription({
        supabaseUrl,
        supabaseKey,
        payment: {
          order_id: orderId,
          transaction_id: transactionUuid,
          amount,
          currency,
          status: orderStatus,
          payment_method: tx.paymentMethodType || 'card',
          customer_email: customerEmail,
          processed_at: new Date().toISOString(),
          webhook_data: krAnswer,
          test_mode: testMode,
        },
        planId: extractPlanFromOrderId(orderId),
      });
    }

    const ms = Date.now() - start;
    console.log(`[PERF] Webhook processed in ${ms}ms`);

    // Izipay expects simple OK on success
    return {
      statusCode: 200,
      headers: { ...headers, 'Content-Type': 'text/plain' },
      body: 'OK',
    };
  } catch (error) {
    console.error('Webhook processing error:', error);
    return {
      statusCode: 500,
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'Internal server error' }),
    };
  }
};

/**
 * Extract plan_id from orderId format:
 * pseudosapiens_plan_{planId}_{timestamp}_{hash}
 */
function extractPlanFromOrderId(orderId) {
  try {
    const match = orderId.match(/pseudosapiens_plan_(\d+)_/);
    if (match) return parseInt(match[1], 10);
  } catch (_) {}
  return null;
}

/**
 * Persist payment in payments table and activate subscription in subscriptions table.
 */
async function persistPaymentAndSubscription({ supabaseUrl, supabaseKey, payment, planId }) {
  try {
    // Map amount to decimal PEN (payments.amount DECIMAL)
    const paymentPayload = {
      amount: Math.round((payment.amount || 0)) / 100, // cents -> PEN
      currency: payment.currency || 'PEN',
      status: payment.status || 'approved',
      payment_date: new Date().toISOString(),
      mercadopago_payment_id: payment.transaction_id || null, // reuse column
    };

    // Insert payment row (without non-existent columns)
    const paymentRes = await fetch(`${supabaseUrl}/rest/v1/payments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${supabaseKey}`,
        'apikey': supabaseKey,
        'Prefer': 'return=minimal',
      },
      body: JSON.stringify(paymentPayload),
    });

    if (!paymentRes.ok) {
      const errText = await paymentRes.text();
      console.error('[DB] payments insert failed:', errText);
    } else {
      console.log('[DB] payment saved');
    }

    // If we don't have a plan, nothing else to do
    if (!planId && planId !== 0) return;

    // Resolve user by email
    const userRes = await fetch(`${supabaseUrl}/rest/v1/users?select=id,email&email=eq.${encodeURIComponent(payment.customer_email)}`, {
      headers: {
        'Authorization': `Bearer ${supabaseKey}`,
        'apikey': supabaseKey,
      },
    });

    let user = null;
    if (userRes.ok) {
      const arr = await userRes.json();
      if (arr && arr.length > 0) user = arr[0];
    }
    // Create user if not exists (only required column: email)
    if (!user) {
      const createRes = await fetch(`${supabaseUrl}/rest/v1/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${supabaseKey}`,
          'apikey': supabaseKey,
          'Prefer': 'return=representation',
        },
        body: JSON.stringify({ email: payment.customer_email }),
      });
      if (createRes.ok) {
        const created = await createRes.json();
        user = created && created[0];
      } else {
        const t = await createRes.text();
        console.error('[DB] user create failed:', t);
        return;
      }
    }

    // Cancel any existing active subscription
    await fetch(`${supabaseUrl}/rest/v1/subscriptions?user_id=eq.${encodeURIComponent(user.id)}&status=eq.active`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${supabaseKey}`,
        'apikey': supabaseKey,
        'Prefer': 'return=minimal',
      },
      body: JSON.stringify({ status: 'cancelled', updated_at: new Date().toISOString() }),
    });

    // Insert new active subscription (only existing columns)
    const subInsert = await fetch(`${supabaseUrl}/rest/v1/subscriptions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${supabaseKey}`,
        'apikey': supabaseKey,
        'Prefer': 'return=representation',
      },
      body: JSON.stringify({
        user_id: user.id,
        plan_id: planId,
        status: 'active',
        started_at: new Date().toISOString(),
      }),
    });

    if (!subInsert.ok) {
      const err = await subInsert.text();
      console.error('[DB] subscription insert failed:', err);
    } else {
      console.log('[DB] subscription activated for', payment.customer_email, 'plan', planId);
    }
  } catch (e) {
    console.error('[DB] persistence error:', e);
  }
}