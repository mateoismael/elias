// Simple test function to verify Netlify Functions are working

exports.handler = async (event, context) => {
  // CORS headers
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
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

  try {
    console.log('Test function called with method:', event.httpMethod);
    console.log('Environment variables available:', {
      IZIPAY_SHOP_ID: process.env.IZIPAY_SHOP_ID ? 'YES' : 'NO',
      IZIPAY_TEST_MODE: process.env.IZIPAY_TEST_MODE,
      IZIPAY_API_URL: process.env.IZIPAY_API_URL ? 'YES' : 'NO',
      IZIPAY_TEST_PASSWORD: process.env.IZIPAY_TEST_PASSWORD ? 'YES' : 'NO',
      IZIPAY_PUBLIC_TEST_KEY: process.env.IZIPAY_PUBLIC_TEST_KEY ? 'YES' : 'NO'
    });

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        success: true,
        message: 'Test function working!',
        timestamp: new Date().toISOString(),
        method: event.httpMethod,
        envCheck: {
          shopId: process.env.IZIPAY_SHOP_ID || 'NOT_SET',
          testMode: process.env.IZIPAY_TEST_MODE || 'NOT_SET',
          hasTestPassword: !!process.env.IZIPAY_TEST_PASSWORD,
          hasPublicKey: !!process.env.IZIPAY_PUBLIC_TEST_KEY
        }
      })
    };

  } catch (error) {
    console.error('Test function error:', error);
    
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({
        error: 'Test function failed',
        message: error.message,
        stack: error.stack
      })
    };
  }
};