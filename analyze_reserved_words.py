import pandas as pd

# Load master products
df = pd.read_excel('BPP master data skus.xlsx')

print("=" * 80)
print("ANÁLISIS DE CAMPOS CON POSIBLES PALABRAS RESERVADAS")
print("=" * 80)

# Campos a analizar según el usuario
campos = ['Etapa', 'Marca', 'TA', 'Unificador', 'Sustancia', 'Formato']

for campo in campos:
    print(f"\n{'=' * 80}")
    print(f"CAMPO: {campo}")
    print("=" * 80)
    
    if campo in df.columns:
        valores_unicos = df[campo].dropna().unique()
        print(f"Total valores únicos: {len(valores_unicos)}\n")
        
        # Mostrar todos los valores únicos
        for i, valor in enumerate(sorted(valores_unicos), 1):
            print(f"{i:3d}. {valor}")
    else:
        print(f"⚠️  Campo '{campo}' no encontrado en el maestro")

print("\n" + "=" * 80)
print("PALABRAS POTENCIALMENTE PROBLEMÁTICAS EN PRODUCTOS LEGÍTIMOS")
print("=" * 80)

# Buscar palabras que podrían confundirse con productos no deseados
palabras_analizar = {
    'suplemento': [],
    'nutricional': [],
    'adulto': [],
    'infantil': [],
    'polvo': [],
    'liquido': [],
    'aceite': []
}

for palabra in palabras_analizar.keys():
    # Buscar en todos los campos relevantes
    for campo in ['Etapa', 'Marca', 'TA', 'Unificador', 'Sustancia']:
        if campo in df.columns:
            matches = df[df[campo].astype(str).str.contains(palabra, case=False, na=False)]
            if len(matches) > 0:
                for idx, row in matches.iterrows():
                    palabras_analizar[palabra].append({
                        'campo': campo,
                        'valor': row[campo],
                        'marca': row['Marca'],
                        'producto': row['Unificador']
                    })

print("\nProductos legítimos que contienen palabras potencialmente problemáticas:\n")
for palabra, ocurrencias in palabras_analizar.items():
    if ocurrencias:
        print(f"\n📌 '{palabra.upper()}' - {len(ocurrencias)} ocurrencias:")
        seen = set()
        for occ in ocurrencias:
            key = f"{occ['marca']}|{occ['producto']}"
            if key not in seen:
                print(f"   • {occ['marca']}: {occ['producto']}")
                print(f"     └─ Campo '{occ['campo']}': {occ['valor']}")
                seen.add(key)

print("\n" + "=" * 80)
print("CONCLUSIÓN")
print("=" * 80)
print("""
✓ NO se debe implementar filtrado por palabras clave
✓ La estrategia correcta es:
  1. Buscar solo por marcas del maestro (Nutrilon, Vital, Diasip, etc.)
  2. Dejar que el motor de identificación haga fuzzy matching
  3. Usar el enricher para obtener EAN y hacer match exacto
""")
