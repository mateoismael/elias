#!/usr/bin/env python3
"""
Script simple para mostrar configuracion DNS necesaria
Sin emojis para evitar problemas de encoding
"""

def main():
    domain = "pseudosapiens.com"
    
    print("PSEUDOSAPIENS - CONFIGURACION DNS CRITICA")
    print("=" * 50)
    print("SIN ESTO, TUS EMAILS VAN DIRECTO A PROMOCIONES")
    print("=" * 50)
    
    print(f"\nCONFIGURACION DNS PARA {domain.upper()}")
    print("=" * 40)
    
    print("\n1. SPF RECORD (CRITICO)")
    print("   Tipo: TXT")
    print("   Nombre: @")
    print("   Valor: v=spf1 include:spf.resend.com ~all")
    print("   Descripcion: Autoriza a Resend a enviar emails")
    
    print("\n2. DKIM RECORD (CRITICO)")
    print("   Tipo: TXT")
    print("   Nombre: resend._domainkey")
    print("   Valor: OBTENER_DE_RESEND_DASHBOARD")
    print("   Descripcion: Key DKIM de Resend")
    print("   Instrucciones:")
    print("      1. Ve a dashboard.resend.com")
    print("      2. Domain Settings")
    print("      3. Copia el valor TXT")
    
    print("\n3. DMARC RECORD (CRITICO)")
    print("   Tipo: TXT")
    print("   Nombre: _dmarc")
    print("   Valor: v=DMARC1; p=none; rua=mailto:dmarc@pseudosapiens.com")
    print("   Descripcion: Politica DMARC requerida por Gmail 2025")
    
    print("\nPASOS A SEGUIR:")
    print("1. Ve al panel de DNS de tu proveedor")
    print("2. Agrega TODOS los registros TXT mostrados arriba")
    print("3. Espera 24 horas para propagacion")
    print("4. Solo DESPUES envia emails masivos")
    
    print("\nRESULTADO ESPERADO:")
    print("Con DNS configurado: 80-90% emails llegan al inbox")
    print("Sin DNS configurado: 90% van a promociones/spam")
    
    print("\nVERIFICAR MANUALMENTE:")
    print("nslookup -type=TXT pseudosapiens.com")
    print("nslookup -type=TXT resend._domainkey.pseudosapiens.com")
    print("nslookup -type=TXT _dmarc.pseudosapiens.com")

if __name__ == "__main__":
    main()