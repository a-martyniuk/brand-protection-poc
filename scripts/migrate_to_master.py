from logic.supabase_handler import SupabaseHandler

def migrate_to_golden_source():
    db = SupabaseHandler()
    
    # 1. Fetch from old table
    print("Fetching data from legacy 'official_products'...")
    try:
        old_data = db.supabase.table("official_products").select("*").execute().data
    except Exception as e:
        print(f"Error fetching old data: {e}")
        return

    if not old_data:
        print("No legacy data found.")
        return

    print(f"Found {len(old_data)} products. Preparing for migration...")

    # 2. Map to new schema
    new_data = []
    seen_eans = set()
    for item in old_data:
        ean = item.get("ean")
        if not ean or ean in seen_eans:
            continue
            
        seen_eans.add(ean)
        new_data.append({
            "sap_code": str(item.get("sap_code")),
            "ean": ean,
            "brand": item.get("brand"),
            "product_name": item.get("product_name"),
            "format": item.get("format"),
            "fc_net": float(item.get("fc_net")) if item.get("fc_net") else None,
            "is_publishable": item.get("is_publishable", True),
            "list_price": float(item.get("list_price")) if item.get("list_price") else None,
            "status": item.get("status"),
            "units_per_pack": item.get("units_per_pack")
        })

    # 3. Upsert to new table
    if new_data:
        print(f"Migrating {len(new_data)} unique products to 'master_products'...")
        result = db.upsert_master_products(new_data)
        if result:
            print("Migration successful.")
        else:
            print("Migration failed during upsert.")
    else:
        print("No valid unique products to migrate.")

if __name__ == "__main__":
    migrate_to_golden_source()
