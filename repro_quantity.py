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
    
    print("\nTesting full audit (including unit pricing)...")
    audit = engine.generate_audit_report(listing, master_product, match_level=1)
    
    details = audit["violation_details"]
    if "non_standard_qty" in details:
        calc_unit_price = details["non_standard_qty"]["unit_price_calculated"]
        print(f"SUCCESS: Non-standard quantity detected. Unit price: {calc_unit_price}")
        if calc_unit_price == 15000 / 4:
            print("SUCCESS: Unit price calculated correctly (15000 / 4 = 3750)")
        else:
            print(f"FAIL: Expected unit price 3750, got {calc_unit_price}")
    else:
        print("FAIL: Non-standard quantity NOT detected in audit details")

    if audit["fraud_score"] >= 100 and "low_price" in details:
        print(f"SUCCESS: Low price detected based on unit price. Violation diff: {details['low_price']['diff']}")
    else:
        print(f"FAIL: Expected low price violation (3750 < 5000), but audit score is {audit['fraud_score']}")

if __name__ == "__main__":
    test_reproduction()
