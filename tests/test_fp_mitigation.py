import asyncio
from logic.identification_engine import IdentificationEngine

async def test_false_positive():
    engine = IdentificationEngine()
    
    # Mock listing for Vitalcan
    vitalcan_listing = {
        "title": "Vitalcan Alimento Seco Perro Adulto Cordero Premium Bolsa 22kg",
        "price": 52990,
        "attributes": {
            "brand": "Vitalcan",
            "marca": "Vitalcan",
            "net_content": "22kg"
        }
    }
    
    print(f"Testing identification for: {vitalcan_listing['title']}")
    audit = engine.identify_product(vitalcan_listing)
    
    if audit["master_id"] is None:
        print("✅ SUCCESS: Product rejected as expected.")
    else:
        print(f"❌ FAILURE: Product matched to Master ID {audit['master_id']} ('{audit.get('master_name')}') with score {audit['fraud_score']}")
        print(f"Audit Details: {audit['details']}")

if __name__ == "__main__":
    asyncio.run(test_false_positive())
