import re
from thefuzz import fuzz
from logic.supabase_handler import SupabaseHandler

class IdentificationEngine:
    def __init__(self):
        self.db = SupabaseHandler()
        # Cache master products for performance
        self.master_products = self.db.get_master_products()
        print(f"Identification Engine initialized with {len(self.master_products)} master products.")

    def normalize_text(self, text):
        """
        Normalizes text for fuzzy matching.
        """
        if not text: return ""
        text = text.lower()
        # Remove accents
        text = re.sub(r'[áàäâ]', 'a', text)
        text = re.sub(r'[éèëê]', 'e', text)
        text = re.sub(r'[íìïî]', 'i', text)
        text = re.sub(r'[óòöô]', 'o', text)
        text = re.sub(r'[úùüû]', 'u', text)
        # Remove symbols and common noise
        text = re.sub(r'[^a-z0-9\s]', '', text)
        text = re.sub(r'\b(x|ml|gr|g|unidades|pack)\b', '', text)
        return " ".join(text.split())

    def identify_product(self, listing):
        """
        Executes 3-level matching logic.
        :param listing: Dictionary from MeliListing
        :return: (master_product_id, match_level, fraud_score)
        """
        listing_title_norm = self.normalize_text(listing.get("title", ""))
        listing_ean = listing.get("ean_published")
        
        # Level 1: Match exact by EAN (Strong)
        if listing_ean:
            for mp in self.master_products:
                if mp.get("ean") == listing_ean:
                    return mp["id"], 1, 0 # Exact match, 0 fraud base

        # Level 2: Fuzzy Match by Title + Brand
        best_match = None
        max_score = 0
        
        for mp in self.master_products:
            mp_name_norm = self.normalize_text(mp.get("product_name", ""))
            score = fuzz.token_set_ratio(listing_title_norm, mp_name_norm)
            
            if score > max_score:
                max_score = score
                best_match = mp

        # Threshold for Level 2
        if max_score > 85:
            # We identified it fuzzy
            fraud_score = self.calculate_fraud_score(listing, best_match, 2)
            return best_match["id"], 2, fraud_score

        # Level 3: Suspicious Brand Detection (Similarity without identity)
        # If score is between 70-85, it might be a suspicious/apocryphal match
        if max_score > 70:
            fraud_score = self.calculate_fraud_score(listing, best_match, 3)
            return best_match["id"], 3, fraud_score

        # No match found
        return None, 0, self.calculate_fraud_score(listing, None, 0)

    def calculate_fraud_score(self, listing, master_product, match_level):
        """
        Calculates a score from 0-100 indicating likelihood of counterfeit/violation.
        """
        score = 0
        
        # 1. EAN Check (+40 if missing/not matching while in Level 2/3)
        if not listing.get("ean_published"):
            score += 40
            
        # 2. Brand Alteration Check (+20)
        # If brand as published looks like an intentionally misspelled version
        if master_product and listing.get("brand_detected"):
            brand_sim = fuzz.ratio(listing["brand_detected"].lower(), master_product["brand"].lower())
            if 80 < brand_sim < 100:
                score += 20

        # 3. Price Anomaly (+20)
        if master_product and master_product.get("list_price"):
            actual_price = listing.get("price", 0)
            expected_min = master_product["list_price"]
            if actual_price < expected_min * 0.8:
                score += 20

        # 4. Level penalties
        if match_level == 3: score += 10 # Suspicious match bonus

        return min(score, 100)

    def get_risk_level(self, score):
        if score >= 60: return "Alto"
        if score >= 30: return "Medio"
        return "Bajo"
