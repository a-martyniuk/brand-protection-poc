import json
from collections import Counter

def analyze_noise():
    try:
        with open('user_data/raw_listings.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("File not found.")
        return

    print(f"Total listings: {len(data)}")
    
    # Check specific IDs from screenshots
    screenshot_ids = [
        'MLA257503922', 'MLA1893154640', 'MLA2841656254', 'MLA2044830494', 'MLA63636507',
        'MLA1604839601', 'MLA2681062956', 'MLA2381895496', 'MLA2059474428', 'MLA2046435239', 'MLA2062101680',
        'MLA2613602264', 'MLA1507087499', 'MLA1678327157', 'MLA2047820329', 'MLA2091016934', 'MLA1660238095', 'MLA2028896502'
    ]
    print("\n--- SPECIFIC ID CATEGORIES ---")
    for r in data:
        if r.get('meli_id') in screenshot_ids:
            print(f"ID: {r.get('meli_id')} | Category: {r.get('category')} | Title: {r.get('title')}")
    cats = [r.get('category') for r in data]
    cat_counts = Counter(cats).most_common(50)
    
    # Analyze examples for the most common "Identificando..." candidates
    # We'll look for anything that doesn't say "Leche" or "Suplemento" or "Nutricion"
    
    print("\nMost Common Categories:")
    for cat, count in cat_counts:
        print(f"- {cat}: {count}")

    # Sample items from suspicious categories
    suspicious_cats = [
        "MCT Oil", "Vital", "Advanta", "Anamix", "Duocal", "Monogen", "Liquigen", 
        "LS BABY", "Fortifit", "GMPro", "Maxamum", "Lophlex", "Polimerosa"
    ]
    
    print("\n--- SAMPLE ITEMS FROM SUSPICIOUS CATEGORIES ---")
    for s_cat in suspicious_cats:
        items = [r for r in data if r.get('category') == s_cat]
        print(f"\n[Category: {s_cat}] - Total: {len(items)}")
        for item in items[:10]:
            print(f"  • {item['title']} - ${item['price']}")

if __name__ == "__main__":
    analyze_noise()
