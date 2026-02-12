# Instrucciones para iniciar la PoC

## 1. Configurar Supabase
Crea un archivo llamado `.env` en la raíz del proyecto (`d:/Projects/brand-protection-poc/`) con el siguiente contenido:

```env
SUPABASE_URL=TU_URL_DE_SUPABASE
SUPABASE_KEY=TU_API_KEY_ANON

# Credenciales de MercadoLibre
MELI_APP_ID=TU_APP_ID
MELI_CLIENT_SECRET=TU_CLIENT_SECRET
MELI_REDIRECT_URI=TU_REDIRECT_URI
MELI_ACCESS_TOKEN=TU_ACCESS_TOKEN
MELI_REFRESH_TOKEN=TU_REFRESH_TOKEN
```

### Configuración inicial de MercadoLibre
Si aún no tienes los tokens de acceso, puedes generarlos ejecutando el script auxiliar:

```bash
python scripts/get_meli_token.py
```
Sigue las instrucciones en pantalla para obtener tus tokens y agrégalos al archivo `.env`.

## 2. Instalar dependencias (Backend)
En tu terminal, dentro de la carpeta raíz:
```bash
pip install -r requirements.txt
playwright install chromium
```

## 3. Ejecutar el Scraper (API Vía Principal)
```bash
python main.py
```

## 4. Visualizar el Dashboard (En Vercel o Local)
Para correrlo localmente:
```bash
cd frontend
npm install
npm run dev
```

El dashboard se abrirá en `http://localhost:3000`.
