import os
import sys
# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.identification_engine import IdentificationEngine

def test_fc_logic():
    engine = IdentificationEngine()
    
    # Vital 3 Brick 200ml -> FC Net ~0.217 (Single)
    # Vital 3 Brick x 24 -> FC Net ~5.208
    vital_3_pack = {
        "product_name": "VITAL 3 BRICKS X 24 X 200 ML",
        "brand": "VITAL",
        "fc_net": 5.208,
        "fc_dry": 1.661,
        "substance": "Liquido"
    }
    
    # Mocking a master product for Fortini Powder
    # Fortini 400g -> FC Net 0.4
    fortini_powder = {
        "product_name": "FORTINI 400 G",
        "brand": "FORTINI",
        "fc_net": 0.4,
        "fc_dry": 0.4,
        "substance": "Polvo"
    }
    
    print("--- Testing Vital 3 Pack (Correct) ---")
    listing_vital = {"title": "Leche Vital 3 24 Bricks X 200 Ml", "attributes": {"brand": "Vital", "title": "Leche Vital 3 24 Bricks X 200 Ml"}}
    score, matches = engine.calculate_attribute_score(listing_vital["attributes"], vital_3_pack)
    print(f"Score: {score} (High score expected as 24*200ml = 4.8L -> ~5.2kg with FC Net weight)")
    
    print("\n--- Testing Vital 3 Pack (Wrong Quantity) ---")
    # If it says 12 bricks instead of 24
    listing_vital_bad = {"title": "Leche Vital 3 12 Bricks X 200 Ml", "attributes": {"brand": "Vital", "title": "Leche Vital 3 12 Bricks X 200 Ml"}}
    score, matches = engine.calculate_attribute_score(listing_vital_bad["attributes"], vital_3_pack)
    print(f"Score: {score} (Penalty expected due to volume mismatch)")
    
    print("\n--- Testing Powder Match (Correct) ---")
    listing_powder = {"title": "Fortini Nutricia 400g", "attributes": {"brand": "Fortini", "title": "Fortini Nutricia 400g"}}
    score, matches = engine.calculate_attribute_score(listing_powder["attributes"], fortini_powder)
    print(f"Score: {score} (High score expected)")

if __name__ == "__main__":
    test_fc_logic()
