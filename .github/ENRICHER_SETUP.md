# GitHub Actions Setup for Product Enricher

## Overview

El enricher puede correr de 3 formas:
1. **Localmente** (manual, para testing)
2. **GitHub Actions manual** (on-demand)
3. **GitHub Actions programado** (cron diario)

## Configuración de GitHub Actions

### 1. Agregar Secrets

Ve a tu repositorio → Settings → Secrets and variables → Actions

Agrega estos secrets:
- `SUPABASE_URL`: Tu URL de Supabase
- `SUPABASE_KEY`: Tu anon key de Supabase

### 2. Workflow Configurado

El archivo `.github/workflows/enricher.yml` ya está configurado con:

**Triggers:**
- ⏰ **Cron**: Corre diariamente a las 2 AM UTC
- 🎯 **Manual**: Botón "Run workflow" en GitHub Actions

**Parámetros configurables (manual):**
- `limit`: Número de productos (vacío = todos)
- `batch_size`: Productos por batch (default: 15)
- `delay`: Segundos entre requests (default: 3)

**Features:**
- ✅ Timeout de 2 horas
- ✅ Upload de `enricher_status.json` como artifact
- ✅ Notificación automática si falla (crea issue)

### 3. Ejecución Manual

1. Ve a tu repo en GitHub
2. Click en "Actions"
3. Selecciona "Product Enricher"
4. Click "Run workflow"
5. Configura parámetros (opcional)
6. Click "Run workflow"

### 4. Ver Resultados

**Durante ejecución:**
- Ve a Actions → Product Enricher → [run actual]
- Expande "Run enricher" para ver logs en tiempo real

**Después de ejecución:**
- Download artifact "enricher-status" para ver el JSON completo
- Revisa logs para ver qué productos se enriquecieron

## Ejecución Local (Testing)

Para testing local antes de usar GitHub Actions:

```bash
# 1. Cargar variables de entorno
# Windows PowerShell:
$env:SUPABASE_URL="tu_url"
$env:SUPABASE_KEY="tu_key"

# Linux/Mac:
export SUPABASE_URL="tu_url"
export SUPABASE_KEY="tu_key"

# 2. Correr enricher
python enrichers/product_enricher.py 5  # Test con 5 productos

# 3. Ver status en tiempo real (otra terminal)
python enrichers/check_status.py
```

## Ventajas de GitHub Actions

### vs Ejecución Local

| Aspecto | Local | GitHub Actions |
|---------|-------|----------------|
| **Disponibilidad** | Requiere PC encendida | Siempre disponible |
| **Interrupciones** | Vulnerable a cortes | Robusto |
| **Scheduling** | Manual o Task Scheduler | Cron nativo |
| **Logs** | Solo consola | Persistentes en GitHub |
| **Notificaciones** | Ninguna | Auto-crea issues si falla |
| **Recursos** | Tu máquina | Runners de GitHub |

### Monitoreo

**Archivo de status:**
- Se genera `enricher_status.json` en cada run
- Se sube como artifact (disponible 7 días)
- Contiene historial completo de productos procesados

**Notificaciones:**
- Si el workflow falla, auto-crea un issue en GitHub
- Incluye link directo al run fallido
- Puedes configurar notificaciones de GitHub para recibir emails

## Programación del Cron

El workflow está configurado para correr **diariamente a las 2 AM UTC**.

Para cambiar el horario, edita `.github/workflows/enricher.yml`:

```yaml
schedule:
  - cron: '0 2 * * *'  # Diario a las 2 AM UTC
  # - cron: '0 */6 * * *'  # Cada 6 horas
  # - cron: '0 0 * * 0'  # Semanal (domingos)
```

**Sintaxis cron:**
```
┌───────────── minuto (0 - 59)
│ ┌───────────── hora (0 - 23)
│ │ ┌───────────── día del mes (1 - 31)
│ │ │ ┌───────────── mes (1 - 12)
│ │ │ │ ┌───────────── día de la semana (0 - 6, domingo = 0)
│ │ │ │ │
* * * * *
```

## Troubleshooting

### Workflow falla con "Module not found"

**Causa**: Falta alguna dependencia en `requirements.txt`

**Solución**: Asegúrate que `requirements.txt` incluya:
```
playwright
python-dotenv
supabase
```

### Timeout después de 2 horas

**Causa**: Demasiados productos para procesar

**Soluciones**:
1. Aumentar `timeout-minutes` en el workflow
2. Reducir batch size (más lento pero más seguro)
3. Correr en múltiples runs con límites

### No se crean issues al fallar

**Causa**: Falta permiso de escritura

**Solución**: En `.github/workflows/enricher.yml`, agregar:
```yaml
permissions:
  issues: write
```

## Costos

GitHub Actions es **gratis** para repos públicos.

Para repos privados:
- 2,000 minutos/mes gratis
- Este workflow usa ~10-20 min/día
- Total: ~300-600 min/mes (dentro del límite gratuito)

## Recomendación

**Para producción**: Usa GitHub Actions con cron diario
- Más confiable
- No requiere infraestructura
- Logs persistentes
- Notificaciones automáticas

**Para desarrollo**: Usa ejecución local
- Testing rápido
- Debugging más fácil
- Control total
