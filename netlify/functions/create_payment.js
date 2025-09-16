// Izipay Payment Token API - Septiembre 2025
// VERSIÓN FUNCIONAL COMPLETA - NO MOCK
// Endpoint para crear tokens de formulario de pago
// Compatible con Netlify Functions

const crypto = require("crypto");

exports.handler = async (event, context) => {
  // CORS headers
  const headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Content-Type": "application/json",
  };

  // Handle preflight OPTIONS request
  if (event.httpMethod === "OPTIONS") {
    return {
      statusCode: 200,
      headers,
      body: "",
    };
  }

  // Only allow POST requests
  if (event.httpMethod !== "POST") {
    return {
      statusCode: 405,
      headers,
      body: JSON.stringify({ error: "Method not allowed" }),
    };
  }

  try {
    // Parse request body
    const requestData = JSON.parse(event.body || "{}");
    const { user_email, plan_id } = requestData;

    // Validate input
    if (!user_email || !plan_id) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({
          status: "error",
          message: "user_email and plan_id are required",
        }),
      };
    }

    // Environment variables
    const shopId = process.env.IZIPAY_SHOP_ID || "34172081";
    const testMode =
      (process.env.IZIPAY_TEST_MODE || "true").toLowerCase() === "true";
    const apiUrl = process.env.IZIPAY_API_URL || "https://api.micuentaweb.pe";

    // Get credentials based on mode
    const password = testMode
      ? process.env.IZIPAY_TEST_PASSWORD
      : process.env.IZIPAY_PROD_PASSWORD;
    const publicKey = testMode
      ? process.env.IZIPAY_PUBLIC_TEST_KEY
      : process.env.IZIPAY_PUBLIC_PROD_KEY;

    if (!password || !publicKey) {
      console.error("Missing Izipay credentials");
      return {
        statusCode: 500,
        headers,
        body: JSON.stringify({
          status: "error",
          message: "Server configuration error",
          debug: {
            hasPassword: !!password,
            hasPublicKey: !!publicKey,
            shopId: shopId,
            testMode: testMode,
          },
        }),
      };
    }

    // Plan configuration
    const plans = {
      1: { amount: 500, description: "Plan Premium Básico - S/5.00/mes" },
      2: { amount: 1000, description: "Plan Premium Plus - S/10.00/mes" },
    };

    const selectedPlan = plans[plan_id];
    if (!selectedPlan) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({
          status: "error",
          message: "Invalid plan_id. Must be 1 or 2",
          availablePlans: Object.keys(plans).map(Number),
        }),
      };
    }

    // Generate unique order ID
    const timestamp = Date.now();
    const emailHash = crypto
      .createHash("md5")
      .update(user_email)
      .digest("hex")
      .substring(0, 8);
    const orderId = `pseudosapiens_plan_${plan_id}_${timestamp}_${emailHash}`;

    // Create Basic Authentication header
    const authString = `${shopId}:${password}`;
    const authBase64 = Buffer.from(authString).toString("base64");

    // Prepare payment data for Izipay API
    const paymentData = {
      amount: selectedPlan.amount,
      currency: "PEN",
      orderId: orderId,
      customer: {
        email: user_email,
        billingDetails: {
          firstName: user_email.split("@")[0], // Use email prefix as name
          lastName: "",
          phoneNumber: "",
          identityType: "DNI",
          identityCode: "",
          address: "",
          country: "PE",
          city: "Lima",
          state: "Lima",
          zipCode: "00001",
        },
      },
      metadata: {
        plan_id: plan_id,
        description: selectedPlan.description,
        source: "pseudosapiens_dashboard",
      },
    };

    console.log("Creating payment with Izipay:", {
      orderId: orderId,
      amount: selectedPlan.amount,
      testMode: testMode,
      shopId: shopId,
    });

    // Make actual API call to Izipay
    const fetch = require("node-fetch");
    const izipayResponse = await fetch(
      `${apiUrl}/api-payment/V4/Charge/CreatePayment`,
      {
        method: "POST",
        headers: {
          Authorization: `Basic ${authBase64}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(paymentData),
      }
    );

    const izipayResult = await izipayResponse.json();

    // Check response status
    if (!izipayResponse.ok || izipayResult.status !== "SUCCESS") {
      console.error("Izipay API error:", izipayResult);
      return {
        statusCode: 502,
        headers,
        body: JSON.stringify({
          status: "error",
          message: "Payment gateway error",
          error: izipayResult.message || "Unknown error",
          details: izipayResult,
        }),
      };
    }

    // Extract formToken from response
    const formToken = izipayResult.answer?.formToken;

    if (!formToken) {
      console.error("No formToken in Izipay response:", izipayResult);
      return {
        statusCode: 502,
        headers,
        body: JSON.stringify({
          status: "error",
          message: "Invalid response from payment gateway",
          details: "No formToken received",
        }),
      };
    }

    // Success! Return formToken and configuration
    console.log("Payment token created successfully:", orderId);

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        status: "success",
        data: {
          form_token: formToken,
          public_key: publicKey,
          order_id: orderId,
          amount: selectedPlan.amount,
          currency: "PEN",
          customer_email: user_email,
          plan_id: plan_id,
          test_mode: testMode,
          shop_id: shopId,
          js_url:
            "https://static.micuentaweb.pe/static/js/krypton-client/V4.0/stable/kr-payment-form.min.js",
        },
        timestamp: new Date().toISOString(),
      }),
    };
  } catch (error) {
    console.error("Create payment error:", error);

    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({
        status: "error",
        message: "Internal server error",
        error: error.message,
        timestamp: new Date().toISOString(),
      }),
    };
  }
};
