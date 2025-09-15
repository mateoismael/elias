"""
Test de pago en producción - Netlify Function
"""
import requests
import json

def test_payment_creation():
    """Test crear token de pago en producción"""
    print("🚀 TESTEANDO PAGO EN PRODUCCIÓN")
    print("=" * 50)
    
    # URL de la función en Netlify
    url = "https://pseudosapiens.com/.netlify/functions/create_payment"
    
    # Datos de prueba
    test_data = {
        "user_email": "test@pseudosapiens.com",
        "plan_id": 1  # Plan básico S/5.00
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    print(f"📧 Email: {test_data['user_email']}")
    print(f"📦 Plan: {test_data['plan_id']} (S/5.00)")
    print(f"🔗 URL: {url}")
    
    try:
        print("\n⏳ Enviando petición...")
        response = requests.post(url, json=test_data, headers=headers, timeout=30)
        
        print(f"📡 Status Code: {response.status_code}")
        print(f"📄 Response:")
        
        if response.text:
            try:
                result = response.json()
                print(json.dumps(result, indent=2))
                
                # Si tenemos token, mostrar link de pago
                if result.get('form_token'):
                    print(f"\n✅ ¡TOKEN GENERADO!")
                    print(f"🎫 Token: {result['form_token'][:50]}...")
                    print(f"💰 Monto: S/{result.get('amount', 0)/100}")
                    
                    # URL del formulario de pago
                    payment_url = f"https://static.micuentaweb.pe/static/js/krypton-client/V4.0/stable/kr-payment-form.min.js"
                    print(f"🔗 JS SDK: {payment_url}")
                    
                    return result
                else:
                    print(f"\n❌ No se generó token")
                    if 'error' in result:
                        print(f"Error: {result['error']}")
                    
            except json.JSONDecodeError:
                print(response.text)
        else:
            print("(Sin contenido)")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        
    return None

if __name__ == "__main__":
    test_payment_creation()