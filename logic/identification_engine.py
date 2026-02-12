import re
from thefuzz import fuzz
from logic.supabase_handler import SupabaseHandler

class IdentificationEngine:
    def __init__(self):
        self.db = SupabaseHandler()
        # Cache master products for performance
        self.master_products = self.db.get_master_products()
        print(f"Identification Engine initialized with {len(self.master_products)} master products.")

    def extract_measures(self, text):
        """
        Extracts numbers associated with measures (ml, gr, unidades, xN).
        Used to detect quantity mismatches.
        """
        if not text: return set()
        text = text.lower()
        measures = set()
        
        # 1. Matches patterns like "x 4", "x4" (pack size)
        pack_matches = re.findall(r'x\s?(\d+)', text)
        for m in pack_matches:
            measures.add(f"qty_{m}")
            
        # 2. Matches patterns like "800gr", "800 g", "200 ml"
        weight_matches = re.findall(r'(\d+)\s?(ml|gr|g|kg|units|unidades)', text)
        for val, unit in weight_matches:
            # Normalize units
            u = "g" if unit in ["gr", "g", "kg"] else "ml" 
            measures.add(f"{val}{u}")
            measures.add(val) # Also add the raw number for unit-less matching

        # 3. Handle cases like "Tarro 500" or "+ 300" (no units but numeric)
        # We look for a number at the end or preceded by common separators
        standalone_nums = re.findall(r'(\d+)$|\D(\d+)\D', text)
        for group in standalone_nums:
            for num in group:
                if num and len(num) > 1: # Avoid single digit noise unless it's pack qty
                    measures.add(num)
            
        return measures

    def normalize_text(self, text):
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
        return " ".join(text.split())

    def calculate_attribute_score(self, listing_attrs, master_product):
        """
        Calculates a compatibility score based on structured attributes.
        """
        score = 100
        matches = 0
        
        # 1. Brand Match (Critical)
        l_brand = listing_attrs.get("brand", "").lower()
        m_brand = (master_product.get("brand") or "").lower()
        if l_brand and m_brand:
            if l_brand not in m_brand and m_brand not in l_brand:
                score -= 40 # Heavy penalty for brand mismatch
            else:
                matches += 1

        # 2. Stage Match (for formulas)
        m_stage = str(master_product.get("stage") or "").lower()
        if m_stage and m_stage != "nan":
            # Search for stage in title or attributes
            l_text = (listing_attrs.get("title", "") + " " + listing_attrs.get("weight", "")).lower()
            if m_stage in l_text:
                matches += 1
            else:
                score -= 30

        # 3. Weight/Volume Match
        m_weight = str(master_product.get("fc_net") or "").split('.')[0]
        if m_weight and m_weight != "None":
            l_text = (listing_attrs.get("title", "") + " " + listing_attrs.get("weight", "")).lower()
            if m_weight in l_text:
                matches += 1
            else:
                score -= 30

        return max(0, score), matches

    def identify_product(self, listing):
        """
        Executes weighted matching logic and returns a comprehensive audit report.
        """
        listing_title_norm = self.normalize_text(listing.get("title", ""))
        listing_ean = listing.get("ean_published")
        listing_attrs = listing.get("attributes", {})
        listing_attrs["title"] = listing.get("title", "") # for helper
        
        best_match = None
        match_level = 0
        max_total_score = 0
        
        # 1. Level 1: Match exact by EAN (Strong) - Priority
        if listing_ean:
            for mp in self.master_products:
                if mp.get("ean") == listing_ean:
                    best_match = mp
                    match_level = 1
                    break

        if not best_match:
            # 2. Level 2: Weighted Attribute + Title Match
            for mp in self.master_products:
                # Title Similarity (40%)
                mp_name_norm = self.normalize_text(mp.get("product_name", ""))
                title_sim = fuzz.token_set_ratio(listing_title_norm, mp_name_norm)
                
                # Attribute Similarity (60%)
                attr_score, attr_matches = self.calculate_attribute_score(listing_attrs, mp)
                
                # Combined Score
                total_score = (title_sim * 0.4) + (attr_score * 0.6)
                
                if total_score > max_total_score:
                    max_total_score = total_score
                    best_match = mp

            if max_total_score > 85:
                match_level = 2
            elif max_total_score > 65: # Lowered threshold because attributes add precision
                match_level = 3
            else:
                match_level = 0
                best_match = None if max_total_score < 40 else best_match

        # 3. Generate Full Audit
        audit = self.generate_audit_report(listing, best_match, match_level)
        return audit

    def generate_audit_report(self, listing, master_product, match_level):
        """
        Runs all compliance rules and returns result + score.
        """
        details = {}
        score = 0
        is_price_ok = True
        is_brand_correct = True
        is_publishable_ok = True
        
        if not master_product:
            return {
                "master_id": None,
                "match_level": 0,
                "fraud_score": 100 if match_level == 0 else 50,
                "details": {"unidentified": True},
                "is_price_ok": False,
                "is_brand_correct": False,
                "is_publishable_ok": True
            }

        # Attribute-Based Confidence Details
        listing_attrs = listing.get("attributes", {})
        listing_attrs["title"] = listing.get("title", "")
        attr_score, attr_matches = self.calculate_attribute_score(listing_attrs, master_product)
        details["attribute_breakdown"] = {
            "score": attr_score,
            "matches_count": attr_matches,
            "brand": listing_attrs.get("brand"),
            "weight": listing_attrs.get("weight")
        }

        # Rule A: EAN Presence
        if not listing.get("ean_published") and match_level > 1:
            score += 30
            details["missing_ean"] = True

        # Rule B: Brand Integrity
        if listing.get("brand_detected"):
            brand_sim = fuzz.ratio(listing["brand_detected"].lower(), master_product["brand"].lower())
            if brand_sim < 90:
                is_brand_correct = False
                score += 20
                details["brand_mismatch"] = {"expected": master_product["brand"], "found": listing["brand_detected"]}

        # Rule C: Price & Discount Policy
        if master_product.get("list_price"):
            actual_price = listing.get("price", 0)
            expected_min = master_product["list_price"]
            
            if actual_price < expected_min:
                is_price_ok = False
                details["low_price"] = {"min": expected_min, "actual": actual_price}
                
                # STRICT POLICY: If product is flagged as "No Discount Allowed"
                if not master_product.get("discount_allowed", True):
                    score += 60 # Critical: This product should NEVER have a discount
                    details["unauthorized_discount"] = True
                else:
                    if actual_price < expected_min * 0.9:
                        score += 20

        # Rule D: Measure & Quantity Mismatch (Combos)
        master_measures = self.extract_measures(master_product.get("product_name", ""))
        listing_measures = self.extract_measures(listing.get("title", ""))
        
        # Cross-reference with numeric units_per_pack from DB
        db_units = master_product.get("units_per_pack", 1)
        if db_units > 1:
            master_measures.add(f"qty_{db_units}")

        if master_measures and listing_measures:
            mismatches = master_measures - listing_measures
            if mismatches:
                # Detect critical quantity/combo mismatch
                qty_mismatch = any(m.startswith("qty_") for m in mismatches)
                if qty_mismatch:
                    score += 50
                    details["combo_mismatch"] = True
                else:
                    score += 30
                details["measure_mismatch"] = list(mismatches)

        # Rule E: Restricted SKU
        if not master_product.get("is_publishable", True):
            is_publishable_ok = False
            score += 50
            details["restricted_sku"] = True

        # Penalties by level
        if match_level == 3: score += 10
        
        return {
            "master_id": master_product["id"],
            "match_level": match_level,
            "fraud_score": min(score, 100),
            "details": details,
            "is_price_ok": is_price_ok,
            "is_brand_correct": is_brand_correct,
            "is_publishable_ok": is_publishable_ok,
            "master_context": master_product # Return for debugging
        }

    def get_risk_level(self, score):
        if score >= 60: return "Alto"
        if score >= 30: return "Medio"
        return "Bajo"
