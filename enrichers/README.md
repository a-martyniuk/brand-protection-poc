# Product Enricher - Usage Guide

## Overview

The Product Enricher is a background script that scrapes product detail pages to extract EAN codes and detailed specifications. It runs in batches with rate limiting to avoid being blocked by MercadoLibre.

## Quick Start

### Basic Usage

```bash
# Enrich all products missing EAN or brand
python enrichers/product_enricher.py

# Enrich only first 20 products (for testing)
python enrichers/product_enricher.py 20

# Custom batch size and delay
python enrichers/product_enricher.py 50 10 5
# Args: limit=50, batch_size=10, delay=5s
```

## How It Works

1. **Queries database** for products missing `ean_published` or `brand_detected`
2. **Processes in batches** (default: 15 products per batch)
3. **Scrapes detail page** for each product to extract:
   - EAN/GTIN code
   - Brand name
   - Weight/volume
   - Format
4. **Updates database** with enriched data
5. **Rate limits** requests (default: 3s between products, 6s between batches)

## Performance

- **Speed**: ~5-8 seconds per product
- **Batch of 50 products**: ~5-7 minutes
- **Full enrichment (80 products)**: ~10-12 minutes

## Command Line Arguments

```bash
python enrichers/product_enricher.py [limit] [batch_size] [delay]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `limit` | None (all) | Max products to enrich |
| `batch_size` | 15 | Products per batch before long sleep |
| `delay` | 3 | Seconds between requests |

## Examples

```bash
# Test with 10 products
python enrichers/product_enricher.py 10

# Aggressive (faster, higher risk of blocking)
python enrichers/product_enricher.py 100 20 2

# Conservative (slower, safer)
python enrichers/product_enricher.py 100 10 5
```

## Scheduling (Optional)

### Windows Task Scheduler

Run enricher daily at 2 AM:

```powershell
schtasks /create /tn "Product Enricher" /tr "python D:\Projects\brand-protection-poc\enrichers\product_enricher.py" /sc daily /st 02:00
```

### Linux Cron

```bash
# Add to crontab
0 2 * * * cd /path/to/project && python enrichers/product_enricher.py
```

## Monitoring

The enricher provides detailed console output:

```
🔍 Found 45 products to enrich
[1/45] Enriching MLA17322342 - Leche En Polvo Vital 1...
  ✓ Updated with EAN: 7795323001966
[2/45] Enriching MLA9209971 - Nutrilon Profutura 1...
  ✓ Updated with EAN: 7613036716857
...
📦 Batch complete. Sleeping 6s...
...
============================================================
✓ Enrichment complete:
  - Enriched: 42/45
  - Failed: 3/45
============================================================
```

## Database Updates

The enricher updates the `meli_listings` table:

- `ean_published`: EAN code from product page
- `brand_detected`: Brand name from specifications
- `attributes`: Additional specs (weight, format)
- `enriched_at`: Timestamp of enrichment

## Troubleshooting

### No products to enrich

```
🔍 Found 0 products to enrich
✓ No products need enrichment
```

**Solution**: All products already have EAN and brand. Run main scraper first.

### High failure rate

```
✓ Enrichment complete:
  - Enriched: 10/50
  - Failed: 40/50
```

**Possible causes**:
- MercadoLibre blocking requests (reduce batch size, increase delay)
- Network issues
- Product pages changed structure

**Solution**: Run with more conservative settings:
```bash
python enrichers/product_enricher.py 50 5 10
```

### Interrupted enrichment

The enricher is **resumable**. Just run it again - it will only process products still missing data.

## Integration with Main Pipeline

### Recommended Workflow

```bash
# 1. Run main scraper (fast - 2 min)
python main.py

# 2. Run enricher in background (slow - 5-10 min)
python enrichers/product_enricher.py

# 3. Dashboard will show enriched data automatically
```

### Automated Pipeline

```bash
# Run both sequentially
python main.py && python enrichers/product_enricher.py
```

## Notes

- **Resumable**: Can be interrupted and restarted safely
- **Idempotent**: Running multiple times won't duplicate data
- **Selective**: Only enriches products missing data
- **Safe**: Conservative rate limiting by default
