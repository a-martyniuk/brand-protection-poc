import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from logic.supabase_handler import SupabaseHandler
from logic.identification_engine import IdentificationEngine

def analyze_unidentified_noise():
    print("🔍 Fetching 'Brand Not Detected' (Unidentified) listings...")
    db = SupabaseHandler()
    engine = IdentificationEngine()
    
    # Fetch current results from the audit table if possible, or re-run engine
    # Let's fetch the listings and their audit results if they exist
    listings = db.supabase.table("meli_listings").select("*").execute().data
    
    # We need master products
    master_products = db.supabase.table("master_products").select("*").execute().data
    
    unidentified = []
    
    for l in listings:
        title = l.get("title", "")
        
        # Check if it has ANY match with ANY master product
        best_score = 0
        for mp in master_products:
            score, _, _ = engine.calculate_attribute_score(l, mp)
            if score > best_score:
                best_score = score
        
        if best_score == 0:
            unidentified.append(title)
            
    print(f"\nFound {len(unidentified)} unidentified listings (Score 0):")
    for title in sorted(set(unidentified)):
        print(f"- {title}")

if __name__ == "__main__":
    analyze_unidentified_noise()
