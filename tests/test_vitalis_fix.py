import asyncio
from logic.identification_engine import IdentificationEngine

async def test_vitalis_rejection():
    engine = IdentificationEngine()
    
    # Mock listing for Vitalis Acetylcysteine (as seen in user screenshot)
    vitalis_listing = {
        "title": "Promo N Acetil Cisteina 250gr Vitalis + 250g Envase Recarga Característico",
        "price": 50000,
        "attributes": {
            "brand": None, # Missing in screenshot 
            "net_content": "250g"
        }
    }
    
    print(f"Testing identification for: {vitalis_listing['title']}")
    audit = engine.identify_product(vitalis_listing)
    
    if audit["master_id"] is None:
        print("✅ SUCCESS: Product rejected as expected (Master ID is None).")
    else:
        print(f"❌ FAILURE: Product was matched to Master ID {audit['master_id']} ('{audit.get('master_name')}')")
        print(f"Audit Score: {audit['fraud_score']}")
        print(f"Details: {audit['details']}")

if __name__ == "__main__":
    asyncio.run(test_vitalis_rejection())
