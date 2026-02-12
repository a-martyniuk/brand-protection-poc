import pandas as pd

# Load master products
df = pd.read_excel('BPP master data skus.xlsx')

print("=" * 60)
print("MASTER PRODUCTS ANALYSIS")
print("=" * 60)

print(f"\nTotal products: {len(df)}")

print("\n" + "=" * 60)
print("BRANDS (Marca)")
print("=" * 60)
print(df['Marca'].value_counts())

print("\n" + "=" * 60)
print("STAGES (Etapa)")
print("=" * 60)
print(df['Etapa'].value_counts())

print("\n" + "=" * 60)
print("BUSINESS UNITS (BU)")
print("=" * 60)
print(df['BU'].value_counts())

print("\n" + "=" * 60)
print("SAMPLE PRODUCTS BY BRAND")
print("=" * 60)
for brand in df['Marca'].unique()[:10]:
    print(f"\n{brand}:")
    samples = df[df['Marca'] == brand][['Unificador', 'Etapa']].head(3)
    for idx, row in samples.iterrows():
        print(f"  - {row['Unificador']} ({row['Etapa']})")

print("\n" + "=" * 60)
print("KEYWORDS TO ANALYZE")
print("=" * 60)

# Check if any legitimate products contain potential filter keywords
keywords_to_check = [
    'suplemento', 'vitamina', 'alimento', 'perfume', 
    'colonia', 'mascota', 'perro', 'gato'
]

for keyword in keywords_to_check:
    matches = df[df['Unificador'].str.contains(keyword, case=False, na=False)]
    if len(matches) > 0:
        print(f"\n⚠️  '{keyword}' found in {len(matches)} products:")
        for idx, row in matches[['Marca', 'Unificador']].head(5).iterrows():
            print(f"   - {row['Marca']}: {row['Unificador']}")
    else:
        print(f"\n✓ '{keyword}' - SAFE TO FILTER (not in master)")
