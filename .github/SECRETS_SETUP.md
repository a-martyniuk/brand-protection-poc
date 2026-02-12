# GitHub Secrets Configuration Guide

## Valores que necesitas configurar en GitHub

Para que el enricher funcione en GitHub Actions, necesitas agregar estos secrets:

### 1. SUPABASE_URL
**Dónde encontrarlo:**
1. Ve a tu proyecto en [Supabase Dashboard](https://app.supabase.com)
2. Click en "Settings" (⚙️) en el sidebar izquierdo
3. Click en "API"
4. Copia el valor de **"Project URL"**

**Formato:** `https://xxxxxxxxxxxxx.supabase.co`

### 2. SUPABASE_KEY
**Dónde encontrarlo:**
1. En la misma página de Settings → API
2. Busca la sección **"Project API keys"**
3. Copia el valor de **"anon public"** key

**Formato:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (un JWT largo)

---

## Cómo agregar los secrets en GitHub

### Paso 1: Ve a tu repositorio en GitHub
```
https://github.com/a-martyniuk/brand-protection-poc
```

### Paso 2: Navega a Settings
1. Click en **"Settings"** (tab superior derecho)
2. En el sidebar izquierdo, busca **"Secrets and variables"**
3. Click en **"Actions"**

### Paso 3: Agregar cada secret
1. Click en **"New repository secret"**
2. **Name**: `SUPABASE_URL`
3. **Secret**: Pega tu URL de Supabase
4. Click **"Add secret"**

Repite para `SUPABASE_KEY`.

---

## Verificar que funcionó

Después de agregar los secrets:

1. Ve a **Actions** tab en GitHub
2. Click en **"Product Enricher"** workflow
3. Click en **"Run workflow"** (botón verde)
4. Configura:
   - **limit**: `5` (para testing)
   - **batch_size**: `5`
   - **delay**: `3`
5. Click **"Run workflow"**

El workflow debería:
- ✅ Conectarse a Supabase
- ✅ Encontrar productos para enriquecer
- ✅ Procesar 5 productos
- ✅ Subir `enricher_status.json` como artifact

---

## Actualizar tu .env local

Para correr el enricher localmente, crea/actualiza tu `.env`:

```bash
# MercadoLibre (ya existentes)
MELI_APP_ID=tu_app_id
MELI_CLIENT_SECRET=tu_secret
MELI_ACCESS_TOKEN=tu_token

# Supabase (agregar estos)
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**⚠️ IMPORTANTE**: Asegúrate que `.env` esté en `.gitignore` (ya debería estarlo).

---

## Troubleshooting

### "SUPABASE_URL and SUPABASE_KEY must be set"

**Causa**: Los secrets no están configurados o tienen nombres incorrectos.

**Solución**: 
- Verifica que los nombres sean exactamente `SUPABASE_URL` y `SUPABASE_KEY`
- No uses espacios ni caracteres especiales en los nombres
- Los valores deben estar pegados sin espacios extra

### "Failed to connect to Supabase"

**Causa**: URL o key incorrectos.

**Solución**:
- Verifica que copiaste la URL completa (con `https://`)
- Verifica que copiaste el **anon public** key, no el service role key
- Prueba los valores localmente primero

### Workflow no aparece en Actions

**Causa**: El archivo `.github/workflows/enricher.yml` no está en la rama main.

**Solución**:
```bash
git add .github/workflows/enricher.yml
git commit -m "Add enricher workflow"
git push origin main
```

---

## Seguridad

✅ **Secrets en GitHub están encriptados** - nadie puede verlos después de agregarlos
✅ **No aparecen en logs** - GitHub los oculta automáticamente
✅ **Solo accesibles por workflows** - no se exponen públicamente

❌ **NUNCA** hagas commit de `.env` con valores reales
❌ **NUNCA** uses el service role key en GitHub Actions (solo anon public)
