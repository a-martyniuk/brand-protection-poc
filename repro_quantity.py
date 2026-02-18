import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from logic.identification_engine import IdentificationEngine

def test_reproduction():
    engine = IdentificationEngine()
    
    # Mock listing from the user's report
    listing = {
        "title": "Fortisip Compact X 125 Ml Nutricion Pack X 4 U Frutos Rojos. Frutos Rojos",
        "price": 15000,
        "attributes": {
            "title": "Fortisip Compact X 125 Ml Nutricion Pack X 4 U Frutos Rojos. Frutos Rojos",
            "weight": "125 ml" 
        }
    }
    
    # Mock master product (assuming it's a 125ml unit)
    master_product = {
        "id": "test-id",
        "product_name": "Fortisip Compact 125ml",
        "brand": "Fortisip",
        "fc_net": 0.145, # 125ml * 1.085 approx
        "units_per_pack": 1,
        "substance": "liquido",
        "list_price": 5000
    }
    
    print("Testing measures extraction...")
    measures = engine.extract_measures(listing["title"], substance_hint="liquido")
    print(f"Measures: {measures}")
    
    print("\nTesting volumetric validation...")
    vol_match, detected_kg = engine.validate_volumetric_match(listing["attributes"], master_product)
    print(f"Match: {vol_match}, Detected KG: {detected_kg}")
    
    if measures["qty"] != 4:
        print("FAIL: Expected quantity 4 from title")
    else:
        print("SUCCESS: Quantity 4 detected in measures")
        
    if abs(detected_kg - (0.145 * 4)) > 0.1:
        print(f"FAIL: Expected ~{0.145 * 4}kg, got {detected_kg}")
    else:
        print("SUCCESS: Total volume calculated correctly for pack of 4")

if __name__ == "__main__":
    test_reproduction()
