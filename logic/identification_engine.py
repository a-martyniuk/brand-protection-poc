import re
from thefuzz import fuzz
from logic.supabase_handler import SupabaseHandler

class IdentificationEngine:
    def __init__(self):
        self.db = SupabaseHandler()
        # Cache master products for performance
        self.master_products = self.db.get_master_products()
        print(f"Identification Engine initialized with {len(self.master_products)} master products.")

    def extract_measures(self, text, substance_hint=None):
        """
        Extracts numbers associated with measures (ml, gr, unidades, xN).
        Returns a dict with 'unit_val', 'unit_type', and 'qty'.
        """
        if not text: return {"total_kg": 0}
        text = text.lower()
        substance_hint = (substance_hint or "").lower()
        
        # 1. Detect Pack Patterns like "24 bricks x 200ml" or "pack x 4 800g"
        qty = 1
        unit_val = 0
        unit_type = None
        
        # Try to find quantity: [number] [space] [bricks|unidades|pack|u|x]
        qty_match = re.search(r'(\d+)\s?(bricks|unidades|units|u|bricks|pack|un|x)', text)
        if qty_match:
            qty = int(qty_match.group(1))
            
        # Try to find volume: [number] [ml|g|kg|gr]
        vol_match = re.search(r'(\d+)\s?(ml|gr|g|kg)', text)
        if vol_match:
            unit_val = float(vol_match.group(1))
            unit_type = vol_match.group(2)
            if unit_type == 'kg':
                unit_val *= 1000
                unit_type = 'g'
            elif unit_type == 'gr':
                unit_type = 'g'

        # Calculate estimated KG
        total_kg = 0.0
        if unit_val > 0:
            if unit_type == 'g':
                total_kg = (unit_val * qty) / 1000
            elif unit_type == 'ml':
                # Liquid Density Factor (User insight: 200ml -> 0.217kg)
                # We apply it if the substance is liquid or inferred to be liquid
                multiplier = 1.085 if "liquid" in substance_hint or "liquido" in substance_hint else 1.0
                total_kg = ((unit_val * qty) / 1000) * multiplier
                
        return {"total_kg": total_kg, "qty": qty, "unit_val": unit_val, "unit_type": unit_type}

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

    def validate_volumetric_match(self, listing_attrs, master_product):
        """
        Uses FC (Net) and units per pack to validate if the listing volume matches the master SKU.
        Prioritizes enriched structured attributes over regex text extraction.
        """
        m_net = float(master_product.get("fc_net") or 0)
        m_substance = (master_product.get("substance") or "").lower()
        m_units = int(master_product.get("units_per_pack") or 1)
        
        if m_net == 0: return True
        
        # 1. Try to use Enriched Structured Attributes first
        l_net_str = listing_attrs.get("net_content") or listing_attrs.get("weight") or listing_attrs.get("peso neto")
        l_units_str = listing_attrs.get("units_per_pack") or listing_attrs.get("unidades por pack") or listing_attrs.get("cantidad de unidades")
        
        l_total_kg = 0.0
        
        if l_net_str:
            # Simple extraction from structured "800g" or "1kg"
            val_match = re.search(r'(\d+[.,]?\d*)\s?(ml|gr|g|kg)', str(l_net_str).lower())
            if val_match:
                val = float(val_match.group(1).replace(',', '.'))
                unit = val_match.group(2)
                
                l_qty = 1
                if l_units_str:
                    qty_match = re.search(r'(\d+)', str(l_units_str))
                    if qty_match: l_qty = int(qty_match.group(1))
                
                # Convert to KG
                if unit in ['g', 'gr']:
                    l_total_kg = (val * l_qty) / 1000
                elif unit == 'kg':
                    l_total_kg = val * l_qty
                elif unit == 'ml':
                    multiplier = 1.085 if "liquid" in m_substance or "liquido" in m_substance else 1.0
                    l_total_kg = ((val * l_qty) / 1000) * multiplier

        # 2. Fallback to Regex on Title if structured data failed
        if l_total_kg == 0:
            full_text = (listing_attrs.get("title", "") + " " + (listing_attrs.get("weight") or "")).lower()
            measures = self.extract_measures(full_text, substance_hint=m_substance)
            l_total_kg = measures.get("total_kg", 0)
        
        if l_total_kg == 0: return True # Could not determine listing volume
        
        diff = abs(l_total_kg - m_net)
        return diff < (m_net * 0.10) # Reduced tolerance to 10% for enriched data clarity

    def calculate_attribute_score(self, listing_attrs, master_product):
        """
        Calculates a compatibility score based on structured attributes + FC Validation.
        """
        score = 100
        matches = 0
        
        # 1. Brand Match (Critical)
        l_brand = (listing_attrs.get("brand") or listing_attrs.get("marca") or "").lower()
        m_brand = (master_product.get("brand") or "").lower()
        if l_brand and m_brand:
            if l_brand not in m_brand and m_brand not in l_brand:
                score -= 40 
            else:
                matches += 1

        # 2. Volumetric/FC Validation (Updated with structured data)
        listing_attrs["title"] = listing_attrs.get("title", "") # Ensure title is available
        if not self.validate_volumetric_match(listing_attrs, master_product):
            score -= 60 # Heavy penalty for format fraud
        else:
            matches += 1

        # 3. Stage Match
        m_stage = str(master_product.get("stage") or "").lower()
        if m_stage and m_stage != "nan" and m_stage != "none":
            l_text = (listing_attrs.get("title", "") + " " + str(listing_attrs.get("stage", ""))).lower()
            if m_stage in l_text:
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
        listing_attrs["title"] = listing.get("title", "") 
        
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

            if max_total_score > 80: # Slightly relaxed threshold due to strict volumetric check
                match_level = 2
            elif max_total_score > 60: 
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
        [VERSION: ZeroTolerance_v3]
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

        # 1. Attribute-Based Confidence Details
        listing_attrs = listing.get("attributes", {})
        listing_attrs["title"] = listing.get("title", "")
        attr_score, attr_matches = self.calculate_attribute_score(listing_attrs, master_product)
        details["attribute_breakdown"] = {
            "score": attr_score,
            "matches_count": attr_matches,
            "brand": listing_attrs.get("brand") or listing_attrs.get("marca"),
            "net_content": listing_attrs.get("net_content") or listing_attrs.get("weight")
        }

        # Rule A: EAN Presence
        if not listing.get("ean_published") and match_level > 1:
            score += 20
            details["missing_ean"] = True

        # Rule B: Brand Integrity
        found_brand = listing.get("brand_detected") or listing_attrs.get("brand") or listing_attrs.get("marca")
        if found_brand:
            brand_sim = fuzz.ratio(str(found_brand).lower(), master_product["brand"].lower())
            if brand_sim < 85:
                is_brand_correct = False
                score += 30
                details["brand_mismatch"] = {"expected": master_product["brand"], "found": found_brand}

        # Rule C: Price Policy (ZERO TOLERANCE)
        # Using list_price from master_products as the absolute minimum
        if master_product.get("list_price"):
            actual_price = float(listing.get("price", 0))
            min_price = float(master_product["list_price"])
            
            if actual_price < min_price:
                is_price_ok = False
                score += 50 # Significant score increase for price breaking
                details["low_price"] = {
                    "min_allowed": min_price, 
                    "actual_price": actual_price,
                    "diff": round(min_price - actual_price, 2)
                }

        # Rule D: Volumetric Validation (Enhanced Format Fraud Detection)
        if not self.validate_volumetric_match(listing_attrs, master_product):
            m_net = float(master_product.get("fc_net") or 0)
            score += 60 # Critical penalty for format fraud
            details["volumetric_mismatch"] = {
                "expected_kg": m_net,
                "detected_in_listing": listing_attrs.get("net_content") or "unmatched"
            }

        # Rule E: Restricted SKU
        if not master_product.get("is_publishable", True):
            is_publishable_ok = False
            score += 80 # Highly suspicious
            details["restricted_sku_violation"] = True

        # Ensure score stays in range
        final_score = min(score, 100)
        
        return {
            "master_id": master_product["id"],
            "match_level": match_level,
            "fraud_score": final_score,
            "details": details,
            "is_price_ok": is_price_ok,
            "is_brand_correct": is_brand_correct,
            "is_publishable_ok": is_publishable_ok,
            "risk_level": self.get_risk_level(final_score)
        }

    def get_risk_level(self, score):
        if score >= 60: return "Alto"
        if score >= 30: return "Medio"
        return "Bajo"
