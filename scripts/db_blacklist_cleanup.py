import sys
import os
from datetime import datetime

# Add the project root to the path so we can import logic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.supabase_handler import SupabaseHandler

def db_cleanup():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting Database Blacklist Cleanup...")
    db = SupabaseHandler()
    
    # 1. Definir las palabras clave (igual que en IdentificationEngine)
    exclusion_keywords = [
        # Pet & Animal
        "perro", "gato", "mascotas", "vitalcan", "sieger", "dog chow", "cat chow",
        # Pharmaceuticals
        "vitalis", "acetilcisteina", "cisteina", "farmacia", "medicamento", "laboratorio vitalis",
        # Biological/Tech Mimics
        "hongo", "seta", "reishi", "melena de leon", "suplemento dietario",
        "jebao", "acuario", "pecera", "skimmer", "dosificadora", "iluminacion led",
        # Mobile & Tech Noise
        "funda", "vidrio templado", "celular", "case", "protector de pantalla",
        # Personal Care & Beauty
        "shampoo", "acondicionador", "crema", "perfume", "fragancia", "peine", "shampoo vital",
        # Baby Gear & Toys
        "cochecito", "cuna", "butaca", "bouncer", "mecedora", "juguete", "lego", "playmobil", "muñeca",
        # Automotive & Industrial
        "motor", "auto", "camion", "moto ", "lubricante", "filtro aceite", "shell helix", "castrol", "motul", "motorcraft"
    ]
    
    nutricia_brands = [
        "nutrilon", "vital", "neocate", "fortisip", "fortini", "nutrison", "peptisorb", "diasip", "loprofin",
        "infatrini", "ketocal", "souvenaid", "cubitan", "mct oil", "monogen", "liquigen", "secalbum", 
        "espesan", "gmpro", "galactomin", "ketoblend", "maxamum", "lophlex", "ls baby", "fortifit", 
        "duocal", "polimerosa", "advanta", "pku", "flocare", "anamix", "l'serina", "serina"
    ]

    try:
        # Fetch all listings
        print("Fetching all listings to identify candidates for deletion...")
        response = db.supabase.table("meli_listings").select("id, title, attributes").execute()
        listings = response.data
        
        to_delete_ids = []
        for l in listings:
            title_lower = l['title'].lower()
            desc_lower = str(l.get('attributes', {}).get('description', '')).lower()
            t_d = title_lower + " " + desc_lower
            
            # Rule 1: Master Exclusion Blacklist
            if any(kw in title_lower for kw in exclusion_keywords):
                to_delete_ids.append(l['id'])
                continue
            
            # Rule 2: MANDATORY Brand Presence (Strict New Policy)
            if not any(b in t_d for b in nutricia_brands):
                to_delete_ids.append(l['id'])
        
        if not to_delete_ids:
            print("No listings found matching the blacklist. Database is already clean.")
            return

        print(f"Found {len(to_delete_ids)} listings to delete.")
        
        # We need to delete compliance_audit records first due to FK
        print("Deleting associated compliance audit logs...")
        db.supabase.table("compliance_audit").delete().in_("listing_id", to_delete_ids).execute()
        
        print(f"Deleting listings from 'meli_listings'...")
        # Supabase delete with .in_()
        # Note: Depending on the size, we might need to batch this, but for < 1500 it should be fine
        db.supabase.table("meli_listings").delete().in_("id", to_delete_ids).execute()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Cleanup complete. {len(to_delete_ids)} noise records removed.")

    except Exception as e:
        print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    db_cleanup()
