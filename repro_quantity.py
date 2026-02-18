import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from logic.identification_engine import IdentificationEngine

def test_reproduction():
    engine = IdentificationEngine()
    
    # Case 1: Fortisip Pack X 4
    listing1 = {
        "title": "Fortisip Compact X 125 Ml Nutricion Pack X 4 U Frutos Rojos. Frutos Rojos",
        "price": 15000,
        "attributes": {
            "title": "Fortisip Compact X 125 Ml Nutricion Pack X 4 U Frutos Rojos. Frutos Rojos",
            "weight": "125 ml" 
        }
    }
    
    # Case 2: Combo X2
    listing2 = {
        "title": "Combo X2 Nutrilon Profutura 4 De 800g Sin Sabor",
        "price": 82762,
        "attributes": {
            "title": "Combo X2 Nutrilon Profutura 4 De 800g Sin Sabor",
            "weight": "800g" 
        }
    }
    
    master_product = {
        "id": "test-id",
        "product_name": "Nutrilon Profutura 4 800g",
        "brand": "Nutrilon",
        "fc_net": 0.8,
        "units_per_pack": 1,
        "substance": "polvo",
        "list_price": 35000
    }

    print("\n--- CASE 1: Fortisip Pack X 4 ---")
    measures1 = engine.extract_measures(listing1["title"], substance_hint="liquido")
    print(f"Measures: {measures1}")
    audit1 = engine.generate_audit_report(listing1, master_product, match_level=1)
    print(f"Audit Qty: {audit1['violation_details'].get('detected_qty')}")

    print("\n--- CASE 2: Combo X2 ---")
    measures2 = engine.extract_measures(listing2["title"], substance_hint="polvo")
    print(f"Measures: {measures2}")
    audit2 = engine.generate_audit_report(listing2, master_product, match_level=1)
    print(f"Audit Qty: {audit2['violation_details'].get('detected_qty')}")
    print(f"Audit Vol: {audit2['violation_details'].get('detected_volume')}")

    # Case 3: Combo X2 with total weight in attributes
    listing3 = {
        "title": "Combo X2 Nutrilon Profutura 4 De 800g Sin Sabor",
        "price": 82762,
        "attributes": {
            "title": "Combo X2 Nutrilon Profutura 4 De 800g Sin Sabor",
            "weight": "1.6kg" 
        }
    }

    print("\n--- CASE 3: Combo X2 (Total Weight Attribute) ---")
    measures3 = engine.extract_measures(listing3["title"], substance_hint="polvo")
    print(f"Measures: {measures3}")
    audit3 = engine.generate_audit_report(listing3, master_product, match_level=1)
    print(f"Audit Qty: {audit3['violation_details'].get('detected_qty')}")
    print(f"Audit Vol: {audit3['violation_details'].get('detected_volume')}")

if __name__ == "__main__":
    test_reproduction()
