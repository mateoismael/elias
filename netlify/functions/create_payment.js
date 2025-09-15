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
    
    // Debug: Log environment variables (without sensitive data)
    console.log('Environment check:', {
      shopId: shopId,
      testMode: testMode,
      apiUrl: apiUrl,
      hasTestPassword: !!process.env.IZIPAY_TEST_PASSWORD,
      hasProdPassword: !!process.env.IZIPAY_PROD_PASSWORD,
      hasTestKey: !!process.env.IZIPAY_PUBLIC_TEST_KEY,
      hasProdKey: !!process.env.IZIPAY_PUBLIC_PROD_KEY
    });
    
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
          mode: testMode ? 'test' : 'production',
          debug: {
            hasPassword: !!password,
            hasPublicKey: !!publicKey,
            shopId: shopId
          }
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

    // For now, return a mock success response to test the frontend
    // TODO: Implement actual Izipay API call once credentials are confirmed
    console.log('Mock payment creation for:', {
      plan: plan,
      orderId: orderId,
      testMode: testMode
    });

    // Return mock successful response
    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        success: true,
        token: `mock_token_${Date.now()}`, // Mock token for testing
        publicKey: publicKey,
        orderId: orderId,
        amount: selectedPlan.amount,
        currency: selectedPlan.currency,
        description: selectedPlan.description,
        testMode: testMode,
        shopId: shopId,
        mock: true // Indicates this is a mock response
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