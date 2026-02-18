import asyncio
from logic.identification_engine import IdentificationEngine

async def test_hongo_rejection():
    engine = IdentificationEngine()
    
    # Mock listing for Hongo Cola de Pavo (as seen in user screenshot)
    hongo_listing = {
        "title": "Hongo Cola De Pavo Molido X30 Gr Sabor Sin Sabor",
        "price": 25000,
        "attributes": {
            "brand": None,
        }
    }
    
    print(f"Testing identification for: {hongo_listing['title']}")
    # 1. Test Rejection (it should return match_level 0 and master_id None)
    audit = engine.identify_product(hongo_listing)
    
    if audit["master_id"] is None:
        print("✅ SUCCESS: Product rejected (No Nutricia match).")
        # 2. Check risk scoring (it should be 0 - Bajo, not 100 - Alto)
        if audit["fraud_score"] == 0 and audit["risk_level"] == "Bajo":
            print("✅ SUCCESS: Risk score is 0 (Bajo) for unidentified product.")
        else:
            print(f"❌ FAILURE: Risk score is {audit['fraud_score']} ({audit['risk_level']}), expected 0 (Bajo).")
    else:
        print(f"❌ FAILURE: Product was incorrectly matched to Master ID {audit['master_id']} ('{audit.get('master_name')}')")

if __name__ == "__main__":
    asyncio.run(test_hongo_rejection())
