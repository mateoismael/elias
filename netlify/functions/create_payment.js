// Izipay Payment Token API - Septiembre 2025
// Endpoint para crear tokens de formulario de pago
// Optimizado para Netlify Functions JavaScript

const crypto = require('crypto');

exports.handler = async (event, context) => {
  // CORS headers
  const headers = {
    'Access-Control-Allow-Origin': 'https://pseudosapiens.com',
    'Access-Control-Allow-Headers': 'Content-Type',
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
    // Parse request body
    const requestData = JSON.parse(event.body || '{}');
    const { plan } = requestData;

    // Environment variables
    const shopId = process.env.IZIPAY_SHOP_ID || '34172081';
    const testMode = (process.env.IZIPAY_TEST_MODE || 'true').toLowerCase() === 'true';
    const apiUrl = process.env.IZIPAY_API_URL || 'https://api.micuentaweb.pe';
    
    // Credentials based on mode
    const password = testMode 
      ? process.env.IZIPAY_TEST_PASSWORD 
      : process.env.IZIPAY_PROD_PASSWORD;
    const publicKey = testMode 
      ? process.env.IZIPAY_PUBLIC_TEST_KEY 
      : process.env.IZIPAY_PUBLIC_PROD_KEY;

    if (!password || !publicKey) {
      return {
        statusCode: 500,
        headers,
        body: JSON.stringify({ 
          error: 'Missing Izipay credentials',
          mode: testMode ? 'test' : 'production'
        })
      };
    }

    // Plan configuration
    const plans = {
      'basico': { amount: 5, currency: 'PEN', description: 'Plan Básico S/5' },
      'premium': { amount: 10, currency: 'PEN', description: 'Plan Premium S/10' }
    };

    const selectedPlan = plans[plan];
    if (!selectedPlan) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ error: 'Invalid plan', availablePlans: Object.keys(plans) })
      };
    }

    // Generate unique order ID
    const orderId = `ORDER_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // Create payment data
    const paymentData = {
      amount: selectedPlan.amount * 100, // Convert to cents
      currency: selectedPlan.currency,
      orderId: orderId,
      customer: {
        email: requestData.email || 'test@pseudosapiens.com'
      },
      customData: {
        plan: plan,
        timestamp: new Date().toISOString()
      }
    };

    // Create HMAC signature for authentication
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const nonce = crypto.randomBytes(16).toString('hex');
    
    // Create signature string
    const signatureString = `POST\n${apiUrl}/api-payment/V4/Charge/CreatePayment\n${JSON.stringify(paymentData)}\n${timestamp}\n${nonce}`;
    const signature = crypto.createHmac('sha256', password).update(signatureString).digest('base64');

    // Make request to Izipay API
    const response = await fetch(`${apiUrl}/api-payment/V4/Charge/CreatePayment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Basic ${Buffer.from(`${shopId}:${password}`).toString('base64')}`,
        'X-Timestamp': timestamp,
        'X-Nonce': nonce,
        'X-Signature': signature
      },
      body: JSON.stringify(paymentData)
    });

    const responseData = await response.json();

    if (!response.ok) {
      return {
        statusCode: response.status,
        headers,
        body: JSON.stringify({
          error: 'Izipay API error',
          details: responseData,
          testMode: testMode
        })
      };
    }

    // Return successful response with token and public key
    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        success: true,
        token: responseData.answer?.formToken || responseData.formToken,
        publicKey: publicKey,
        orderId: orderId,
        amount: selectedPlan.amount,
        currency: selectedPlan.currency,
        description: selectedPlan.description,
        testMode: testMode,
        shopId: shopId
      })
    };

  } catch (error) {
    console.error('Create payment error:', error);
    
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