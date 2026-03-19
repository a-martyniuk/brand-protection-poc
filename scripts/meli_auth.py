import os
import requests
import urllib.parse
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    app_id = os.getenv("MELI_APP_ID")
    client_secret = os.getenv("MELI_CLIENT_SECRET")
    redirect_uri = os.getenv("MELI_REDIRECT_URI", "http://localhost")
    
    if not app_id or not client_secret:
        print("❌ ERROR: Faltan MELI_APP_ID o MELI_CLIENT_SECRET en tu archivo .env.")
        print("Por favor, asegúrate de ingresarlos desde tu panel de desarrollador de MercadoLibre y vuelve a correr este script.")
        return
        
    auth_url = f"https://auth.mercadolibre.com.ar/authorization?response_type=code&client_id={app_id}&redirect_uri={urllib.parse.quote(redirect_uri)}"
    
    print("\n" + "="*80)
    print("🔒 CONFIGURACIÓN DE TOKEN DE MERCADO LIBRE")
    print("="*80)
    print("\n1️⃣ Abre el siguiente enlace en tu navegador web:")
    print(f"\n   👉 {auth_url}\n")
    print("2️⃣ Inicia sesión con la cuenta de MercadoLibre con la que creaste la aplicación si te lo pide.")
    print("3️⃣ Cuando autorices, la página te llevará a un enlace roto o localhost (es normal).")
    print("   Observa la barra de direcciones, debería decir algo como:")
    print("   http://localhost/?code=TG-xxxxxxxxxxxx-yyyyyy\n")
    
    code = input("4️⃣ Pega aquí la parte del 'code' que aparece en la URL (incluye el TG-...): ").strip()
    
    if "code=" in code:
        # por si pega toda la URL completa
        code = code.split("code=")[1].split("&")[0]
        
    if not code:
        print("No se ingresó código. Cancelando...")
        return
        
    print("\nCanjeando código por Access Token...")
    
    payload = {
        "grant_type": "authorization_code",
        "client_id": app_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    response = requests.post("https://api.mercadolibre.com/oauth/token", data=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        
        # Cargar lo que hay en el .env actualmente y sobrescribir los tokens
        env_lines = []
        try:
            with open(".env", "r", encoding="utf-8") as f:
                env_lines = f.readlines()
        except FileNotFoundError:
            pass
            
        new_env_lines = []
        found_access = False
        found_refresh = False
        
        for line in env_lines:
            if line.startswith("MELI_ACCESS_TOKEN="):
                new_env_lines.append(f"MELI_ACCESS_TOKEN={access_token}\n")
                found_access = True
            elif line.startswith("MELI_REFRESH_TOKEN="):
                new_env_lines.append(f"MELI_REFRESH_TOKEN={refresh_token}\n")
                found_refresh = True
            else:
                new_env_lines.append(line)
                
        if not found_access:
            new_env_lines.append(f"MELI_ACCESS_TOKEN={access_token}\n")
        if not found_refresh:
            new_env_lines.append(f"MELI_REFRESH_TOKEN={refresh_token}\n")
            
        with open(".env", "w", encoding="utf-8") as f:
            f.writelines(new_env_lines)
            
        print("✅ ÉXITO: Los tokens fueron guardados en el archivo .env correctamente.")
        print("Ahora la extracción de stock debería funcionar sin problemas.")
        
    else:
        print(f"❌ ERROR: Falló el canje de tokens (HTTP {response.status_code})")
        print(response.text)
        print("Es probable que el código haya expirado o ya se haya usado. Intenta generar un enlace nuevo.")

if __name__ == "__main__":
    main()
