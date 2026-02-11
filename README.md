# Instrucciones para iniciar la PoC

## 1. Configurar Supabase
Crea un archivo llamado `.env` en la raíz del proyecto (`d:/Projects/brand-protection-poc/`) con el siguiente contenido:

```env
SUPABASE_URL=TU_URL_DE_SUPABASE
SUPABASE_KEY=TU_API_KEY_ANON
```

## 2. Instalar dependencias (Backend)
En tu terminal, dentro de la carpeta raíz:
```bash
pip install -r requirements.txt
playwright install chromium
```

## 3. Ejecutar el Scraper
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
