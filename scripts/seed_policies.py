from logic.supabase_handler import SupabaseHandler

def seed_policies():
    db = SupabaseHandler()
    
    policies = [
        {
            "product_name": "Nutrilon Profutura 4",
            "min_price": 18000.00,
            "keywords_blacklist": ["vencida", "oferta prohibida", "promo"]
        },
        {
            "product_name": "Vital 3",
            "min_price": 9500.00,
            "keywords_blacklist": ["vencida"]
        },
        {
            "product_name": "Nutrilon 1",
            "min_price": 12000.00,
            "keywords_blacklist": ["regalo", "promocion"] # Often restricted for stage 1 formula
        }
    ]
    
    print("Seeding policies into Supabase...")
    for policy in policies:
        try:
            # We use insert because we don't have meli_id for policies, just names
            response = db.supabase.table("policies").insert(policy).execute()
            print(f"Added policy for: {policy['product_name']}")
        except Exception as e:
            print(f"Error seeding policy {policy['product_name']}: {e}")

if __name__ == "__main__":
    seed_policies()
