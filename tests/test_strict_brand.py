import asyncio
from logic.identification_engine import IdentificationEngine

async def test_strict_brand_match():
    engine = IdentificationEngine()
    
    # Mock listing that has NO brand in title, but maybe generic terms
    generic_listing = {
        "title": "Leche De Bebe Etapa 1 X 800g",
        "price": 25000,
        "attributes": {
            "brand": None,
            "net_content": "800g"
        }
    }
    
    # Mock listing that HAS brand
    legit_listing = {
        "title": "Nutrilon Profutura 1 800 Gr",
        "price": 95000,
        "attributes": {
            "brand": "Nutrilon",
            "net_content": "800g"
        }
    }
    
    print(f"Testing generic listing: {generic_listing['title']}")
    audit_generic = engine.identify_product(generic_listing)
    if audit_generic["master_id"] is None:
        print("✅ SUCCESS: Generic listing rejected for lack of brand keyword.")
    else:
        print(f"❌ FAILURE: Generic listing matched to {audit_generic.get('master_name')}")

    print(f"Testing legit listing: {legit_listing['title']}")
    audit_legit = engine.identify_product(legit_listing)
    if audit_legit["master_id"] is not None:
        print(f"✅ SUCCESS: Legit listing matched to {audit_legit.get('master_name')}. Score: {audit_legit['fraud_score']}")
    else:
        print(f"❌ FAILURE: Legit listing was rejected. Match Level: {audit_legit['match_level']}")
        # Try to find what was the max score internally
        listing_title_norm = engine.normalize_text(legit_listing.get("title", ""))
        max_s = 0
        for mp in engine.master_products:
            mp_name_norm = engine.normalize_text(mp.get("product_name", ""))
            ts = fuzz.token_set_ratio(listing_title_norm, mp_name_norm)
            attr_s, _ = engine.calculate_attribute_score(legit_listing["attributes"], mp)
            s = (ts * 0.4) + (attr_s * 0.6)
            if s > max_s: max_s = s
        print(f"Max internal score found: {max_s}")

if __name__ == "__main__":
    asyncio.run(test_strict_brand_match())
