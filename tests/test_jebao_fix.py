import asyncio
from logic.identification_engine import IdentificationEngine

async def test_jebao_rejection():
    engine = IdentificationEngine()
    
    # Mock listing for Jebao Dmp-40 (as seen in user screenshot)
    jebao_listing = {
        "title": "Jebao Dmp-40",
        "price": 550000,
        "attributes": {
            "brand": None, # "Not detected" in screenshot
        }
    }
    
    print(f"Testing identification for: {jebao_listing['title']}")
    # This listing has NO common words with "Nutrilon" or any other Nutricia brand
    audit = engine.identify_product(jebao_listing)
    
    if audit["master_id"] is None:
        print("✅ SUCCESS: Product rejected as expected (Master ID is None).")
    else:
        print(f"❌ FAILURE: Product was matched to Master ID {audit['master_id']} ('{audit.get('master_name')}')")
        print(f"Audit Score: {audit['fraud_score']}")
        print(f"Details: {audit['details']}")

if __name__ == "__main__":
    asyncio.run(test_jebao_rejection())
