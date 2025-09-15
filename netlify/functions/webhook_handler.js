// Izipay Webhook Handler - Septiembre 2025
// Procesa webhooks de Izipay y actualiza base de datos Supabase
// Optimizado para Netlify Functions JavaScript

const crypto = require('crypto');

exports.handler = async (event, context) => {
  // CORS headers
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, Kr-Hash-Algorithm, Kr-Hash, Kr-Hash-Key',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Content-Type': 'application/json'
  };

  // Handle preflight OPTIONS request
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers,
      body: ''
    };
  }

  // Only allow POST requests
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      headers,
      body: JSON.stringify({ error: 'Method not allowed' })
    };
  }

  try {
    // Get environment variables
    const testMode = (process.env.IZIPAY_TEST_MODE || 'true').toLowerCase() === 'true';
    const hmacKey = testMode 
      ? process.env.IZIPAY_TEST_PASSWORD 
      : process.env.IZIPAY_HMAC_PROD_KEY;
    
    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_KEY;

    if (!hmacKey || !supabaseUrl || !supabaseKey) {
      console.error('Missing environment variables');
      return {
        statusCode: 500,
        headers,
        body: JSON.stringify({ error: 'Missing configuration' })
      };
    }

    // Get webhook data
    const rawBody = event.body || '';
    const receivedHash = event.headers['kr-hash'] || event.headers['Kr-Hash'];
    const hashAlgorithm = event.headers['kr-hash-algorithm'] || event.headers['Kr-Hash-Algorithm'] || 'sha256_hmac';

    console.log('Webhook received:', {
      algorithm: hashAlgorithm,
      hasHash: !!receivedHash,
      bodyLength: rawBody.length,
      testMode: testMode
    });

    // Verify HMAC signature
    if (receivedHash) {
      const expectedHash = crypto.createHmac('sha256', hmacKey).update(rawBody).digest('base64');
      
      if (receivedHash !== expectedHash) {
        console.error('HMAC verification failed', {
          received: receivedHash,
          expected: expectedHash
        });
        return {
          statusCode: 401,
          headers,
          body: JSON.stringify({ error: 'Invalid signature' })
        };
      }
      console.log('HMAC verification successful');
    } else {
      console.warn('No HMAC signature provided');
    }

    // Parse webhook data
    let webhookData;
    try {
      webhookData = JSON.parse(rawBody);
    } catch (parseError) {
      console.error('Failed to parse webhook data:', parseError);
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ error: 'Invalid JSON data' })
      };
    }

    // Extract payment information (Izipay kr-* format)
    const orderDetails = webhookData.orderDetails || {};
    const customerDetails = webhookData.customer || {};
    const transactionDetails = webhookData.transactions?.[0] || {};
    
    const paymentData = {
      order_id: orderDetails.orderId || 'unknown',
      transaction_id: transactionDetails.uuid || 'unknown',
      amount: transactionDetails.amount || 0,
      currency: transactionDetails.currency || 'PEN',
      status: transactionDetails.transactionStatusLabel || 'unknown',
      payment_method: transactionDetails.paymentMethodType || 'unknown',
      customer_email: customerDetails.email || 'unknown',
      processed_at: new Date().toISOString(),
      webhook_data: webhookData,
      test_mode: testMode
    };

    console.log('Processing payment:', {
      orderId: paymentData.order_id,
      amount: paymentData.amount,
      status: paymentData.status
    });

    // Save to Supabase
    const supabaseResponse = await fetch(`${supabaseUrl}/rest/v1/payments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${supabaseKey}`,
        'apikey': supabaseKey,
        'Prefer': 'return=minimal'
      },
      body: JSON.stringify(paymentData)
    });

    if (!supabaseResponse.ok) {
      const errorText = await supabaseResponse.text();
      console.error('Supabase error:', errorText);
      return {
        statusCode: 500,
        headers,
        body: JSON.stringify({ 
          error: 'Database error',
          details: errorText
        })
      };
    }

    console.log('Payment saved to database successfully');

    // Return success response
    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        success: true,
        message: 'Webhook processed successfully',
        orderId: paymentData.order_id,
        status: paymentData.status,
        timestamp: paymentData.processed_at
      })
    };

  } catch (error) {
    console.error('Webhook processing error:', error);
    
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({
        error: 'Internal server error',
        message: error.message,
        timestamp: new Date().toISOString()
      })
    };
  }
};