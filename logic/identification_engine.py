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
        
        # 1. Detect Quantity/Pack Patterns
        qty = 1
        # Match patterns like: Pack X 4, Pack de 6, 12 unidades, 24u, x24, x 4
        # We avoid matching the volume (e.g., 800g) as quantity by using word boundaries or specific markers
        qty_patterns = [
            r'pack\s*x?\s*(\d+)',           # Pack X 4, Pack 4
            r'pack\s+de\s+(\d+)',          # Pack de 6
            r'(\d+)\s*(?:unidades|units|u|un)\b', # 12 unidades, 24u
            r'\bx\s?(\d+)\b'               # x 4, x24 (but not 800x600)
        ]
        
        for p in qty_patterns:
            qty_match = re.search(p, text)
            if qty_match:
                # Extra check: ensure we didn't just grab part of a volume (e.g., 800g)
                candidate = int(qty_match.group(1))
                if candidate > 0 and candidate < 200: # Sanity check for quantity
                    # Ensure it's not immediately followed by a unit of measure
                    if not re.search(f'{candidate}\\s?(ml|gr|g|kg|l)', text):
                        qty = candidate
                        break
            
        # 2. Find Volume/Weight: [number] [ml|g|kg|gr]
        unit_val = 0
        unit_type = None
        vol_match = re.search(r'(\d+[.,]?\d*)\s?(ml|gr|g|kg|l)\b', text)
        if vol_match:
            unit_val = float(vol_match.group(1).replace(',', '.'))
            unit_type = vol_match.group(2)
            if unit_type == 'kg' or unit_type == 'l':
                unit_val *= 1000
                unit_type = 'g' if unit_type == 'kg' else 'ml'
            elif unit_type == 'gr':
                unit_type = 'g'

        # Calculate estimated KG
        total_kg = 0.0
        if unit_val > 0:
            if unit_type == 'g':
                total_kg = (unit_val * qty) / 1000
            elif unit_type == 'ml':
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
        Prioritizes enriched structured attributes but cross-references title for multipliers.
        """
        m_net = float(master_product.get("fc_net") or 0)
        m_substance = (master_product.get("substance") or "").lower()
        
        if m_net == 0: return True, 0
        
        # 1. Try to use Enriched Structured Attributes for Volume
        l_net_str = listing_attrs.get("net_content") or listing_attrs.get("weight") or listing_attrs.get("peso neto")
        l_units_str = listing_attrs.get("units_per_pack") or listing_attrs.get("unidades por pack") or listing_attrs.get("cantidad de unidades")
        
        l_total_kg = 0.0
        l_qty = 1
        
        # Get structured quantity if available
        if l_units_str:
            qty_match = re.search(r'(\d+)', str(l_units_str))
            if qty_match: l_qty = int(qty_match.group(1))
        
        # If quantity is still 1, scan the title for potential "Pack X N" patterns
        title = (listing_attrs.get("title") or "").lower()
        if l_qty == 1 and title:
            measures_title = self.extract_measures(title, substance_hint=m_substance)
            # If extract_measures found a qty > 1, use it
            if measures_title.get("qty", 1) > 1:
                l_qty = measures_title["qty"]
        
        if l_net_str:
            # Simple extraction from structured "800g" or "1kg"
            val_match = re.search(r'(\d+[.,]?\d*)\s?(ml|gr|g|kg|l)', str(l_net_str).lower())
            if val_match:
                val = float(val_match.group(1).replace(',', '.'))
                unit = val_match.group(2)
                
                # Convert to KG using combined quantity
                if unit in ['g', 'gr']:
                    l_total_kg = (val * l_qty) / 1000
                elif unit in ['kg', 'l']:
                    l_total_kg = val * l_qty
                elif unit == 'ml':
                    multiplier = 1.085 if "liquid" in m_substance or "liquido" in m_substance else 1.0
                    l_total_kg = ((val * l_qty) / 1000) * multiplier

        # 2. Final Fallback: Fully Regex Title if still undetermined
        if l_total_kg == 0:
            measures = self.extract_measures(title, substance_hint=m_substance)
            l_total_kg = measures.get("total_kg", 0)
        
        if l_total_kg == 0: return True, 0, l_qty 
        
        diff = abs(l_total_kg - m_net)
        return (diff < (m_net * 0.15)), l_total_kg, l_qty

    def calculate_attribute_score(self, listing_attrs, master_product):
        """
        Calculates a compatibility score based on structured attributes + FC Validation.
        Also implements strict rejection for known false positives (e.g., pet food).
        """
        score = 100
        matches = 0
        
        # 0. Anti-False Positive Keywords (Hard Rejection)
        title_lower = listing_attrs.get("title", "").lower()
        exclusion_keywords = [
            # Pet & Animal (Vitalcan, etc.)
            "perro", "gato", "mascotas", "vitalcan", "sieger", "dog chow", "cat chow",
            # Pharmaceuticals (Vitalis, etc.)
            "vitalis", "acetilcisteina", "cisteina", "farmacia", "medicamento", "laboratorio vitalis",
            # Biological/Tech Mimics (Hongo, Jebao)
            "hongo", "seta", "reishi", "melena de leon", "suplemento dietario",
            "jebao", "acuario", "pecera", "skimmer", "dosificadora", "iluminacion led",
            # Mobile & Tech Noise (Common overlaps)
            "funda", "vidrio templado", "celular", "case", "protector de pantalla",
            # Personal Care & Beauty
            "shampoo", "acondicionador", "crema", "perfume", "fragancia", "peine", "shampoo vital",
            # Baby Gear & Toys (Non-Nutricia)
            "cochecito", "cuna", "butaca", "bouncer", "mecedora", "juguete", "lego", "playmobil", "muñeca",
            # Automotive & Industrial (Conflicts with MCT Oil / Aceite de Lorenzo)
            "motor", "auto", "camion", "moto ", "lubricante", "filtro aceite", "shell helix", "castrol", "motul", "motorcraft"
        ]
        if any(kw in title_lower for kw in exclusion_keywords):
            return 0, 0, None # Hard rejection for pet or unrelated pharma products

        # 1. Brand Match (Critical)
        l_brand = (listing_attrs.get("brand") or listing_attrs.get("marca") or "").lower()
        m_brand = (master_product.get("brand") or "").lower()
        
        # If scraper didn't detect brand, try to find it in title
        nutricia_brands = [
            "nutrilon", "vital", "neocate", "fortisip", "fortini", "nutrison", "peptisorb", "diasip", "loprofin",
            "infatrini", "ketocal", "souvenaid", "cubitan", "mct oil", "monogen", "liquigen", "secalbum", 
            "espesan", "gmpro", "galactomin", "ketoblend", "maxamum", "lophlex", "ls baby", "fortifit", 
            "duocal", "polimerosa", "advanta", "pku", "flocare", "anamix", "l'serina", "serina", "profutura"
        ]
        if not l_brand:
            for b in nutricia_brands:
                if b in title_lower:
                    l_brand = b
                    break
        
        if l_brand and m_brand:
            # If brands are explicitly different and non-overlapping, it's a mismatch
            if l_brand != m_brand and l_brand not in m_brand and m_brand not in l_brand:
                # REJECT known external brands that mimic Nutricia names
                external_mimics = ["vitalcan", "vitalis", "vitalife"]
                if any(mimic in title_lower for mimic in external_mimics):
                    return 0, 0, l_brand # Hard rejection
                score -= 60 
            else:
                matches += 1
        
        # NEW CRITICAL RULE: Mandatory Brand Presence
        # If the master brand keyword is not in the title, reject the match
        # This prevents generic "infant" or "protein" products from other brands from matching
        if m_brand not in title_lower and m_brand not in l_brand:
            return 0, 0, l_brand # Hard rejection for lack of brand intent

        # 2. Volumetric/FC Validation (Updated with structured data)
        vol_match, detected_kg, detected_qty = self.validate_volumetric_match(listing_attrs, master_product)
        if not vol_match:
            score -= 60 # Heavy penalty for format fraud
        else:
            matches += 1

        # 3. Stage Match
        m_stage = str(master_product.get("stage") or "").lower()
        if m_stage and m_stage != "nan" and m_stage != "none":
            l_text = (title_lower + " " + str(listing_attrs.get("stage", ""))).lower()
            if m_stage in l_text:
                matches += 1
            else:
                score -= 30

        return max(0, score), matches, l_brand

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

        # 2. Level 2: Weighted Attribute + Title Match
        # Pre-detect brand to use in strict floors
        l_brand = (listing_attrs.get("brand") or listing_attrs.get("marca") or "").lower()
        if not l_brand:
            nutricia_brands = ["nutrilon", "vital", "neocate", "fortisip", "fortini", "nutrison", "peptisorb", "diasip", "loprofin", "profutura"]
            for b in nutricia_brands:
                if b in listing_title_norm:
                    l_brand = b
                    break

        for mp in self.master_products:
            # Title Similarity (40%)
            mp_name_norm = self.normalize_text(mp.get("product_name", ""))
            title_sim = fuzz.token_set_ratio(listing_title_norm, mp_name_norm)
            
            # Attribute Similarity (60%)
            attr_score, attr_matches, detected_brand = self.calculate_attribute_score(listing_attrs, mp)
            
            # MANDATORY REJECTION
            if attr_score == 0:
                continue

            # Combined Score
            total_score = (title_sim * 0.4) + (attr_score * 0.6)
                
            # 3. Dynamic Thresholds & Hard Floors
            # If title similarity is extremely low, it's a candidate for rejection
            if title_sim < 40 and total_score < 80: 
                total_score = 0 # Hard floor for unrelated titles

            # If NO brand was detected and similarity is not strong, reject
            if not l_brand and title_sim < 60:
                total_score = 0

            if total_score > max_total_score:
                max_total_score = total_score
                best_match = mp

        if max_total_score >= 85: 
            match_level = 2
        elif max_total_score >= 70: 
            match_level = 3
        else:
            match_level = 0
            best_match = None if max_total_score < 60 else best_match

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
                "master_product_id": None,
                "match_level": 0,
                "fraud_score": 0, # Unidentified is NOT a violation by default
                "violation_details": {"unidentified": True, "note": "Listing ignored (No Nutricia match)"},
                "is_price_ok": True,
                "is_brand_correct": True,
                "is_publishable_ok": True,
                "risk_level": "Bajo"
            }

        # 1. Attribute-Based Confidence Details
        listing_attrs = listing.get("attributes", {})
        listing_attrs["title"] = listing.get("title", "")
        attr_score, attr_matches, detected_brand = self.calculate_attribute_score(listing_attrs, master_product)
        details["attribute_breakdown"] = {
            "score": attr_score,
            "matches_count": attr_matches,
            "brand": detected_brand or listing_attrs.get("brand") or listing_attrs.get("marca"),
            "net_content": listing_attrs.get("net_content") or listing_attrs.get("weight")
        }
        
        # Explicitly store detected brand for UI
        details["detected_brand"] = detected_brand.title() if detected_brand else "Not detected"

        # Rule A: EAN Presence
        if not listing.get("ean_published") and match_level > 1:
            score += 20
            details["missing_ean"] = True

        # Rule B: Brand Integrity
        found_brand = detected_brand or listing.get("brand_detected") or listing_attrs.get("brand") or listing_attrs.get("marca")
        if found_brand:
            brand_sim = fuzz.ratio(str(found_brand).lower(), master_product["brand"].lower())
            if brand_sim < 85:
                is_brand_correct = False
                score += 30
                details["brand_mismatch"] = {"expected": master_product["brand"], "found": found_brand}

        # Rule C: Price Policy (ZERO TOLERANCE)
        # Using list_price from master_products as the absolute minimum
        # NEW: Volumetric Validation (Enhanced Format Fraud Detection) - Moved UP to use 'detected_qty' in price calc
        vol_match, detected_kg, detected_qty = self.validate_volumetric_match(listing_attrs, master_product)
        m_net = float(master_product.get("fc_net") or 0)
        m_units = int(master_product.get("units_per_pack") or 1)
        
        # Always include detected volume for UI clarity
        details["detected_volume"] = detected_kg if detected_kg > 0 else (listing_attrs.get("net_content") or "Not detected")
        details["detected_qty"] = detected_qty
        
        if master_product.get("list_price"):
            actual_price = float(listing.get("price", 0))
            # Calculate Price per Unit (Standardized)
            unit_price = actual_price / detected_qty if detected_qty > 0 else actual_price
            min_price = float(master_product["list_price"])
            
            # If the quantity doesn't match the master SKU, note it
            if detected_qty != m_units:
                details["non_standard_qty"] = {
                    "listing_qty": detected_qty,
                    "master_qty": m_units,
                    "unit_price_calculated": round(unit_price, 2)
                }

            if unit_price < min_price:
                is_price_ok = False
                score += 100 # Direct 100 for price breaking
                details["low_price"] = {
                    "min_allowed": min_price, 
                    "actual_unit_price": round(unit_price, 2),
                    "total_price": actual_price,
                    "diff": round(min_price - unit_price, 2)
                }

        # Rule D: Volumetric Match result (calculated above)
        if not vol_match:
            score += 100 # Direct 100 for format fraud
            details["volumetric_mismatch"] = {
                "expected_kg": m_net,
                "detected_in_listing": detected_kg if detected_kg > 0 else (listing_attrs.get("net_content") or "unmatched")
            }

        # Rule E: Restricted SKU
        if not master_product.get("is_publishable", True):
            is_publishable_ok = False
            score += 100 # Direct 100 for restricted SKU
            details["restricted_sku_violation"] = True

        # Rule F: Trust Signal - Official Store
        is_official = listing.get("is_official_store", False)
        if is_official:
            m_price = float(master_product.get("list_price") or 0)
            l_price = float(listing.get("price") or 0)
            # If it's an official store and price isn't ridiculously low (e.g., >80% of list), trust it
            if m_price > 0 and l_price >= (m_price * 0.8):
                details["trust_signal"] = "Verified Official Store"
                score = 0 # Force 0 for official stores with sane pricing
        
        # Add Seller Reputation to details for context
        reputation = listing.get("seller_reputation", {})
        if reputation:
            details["seller_reputation"] = {
                "level": reputation.get("level"),
                "power_seller": reputation.get("power_seller")
            }

        # Ensure score stays in range
        final_score = min(score, 100)
        
        return {
            "master_product_id": master_product["id"],
            "match_level": match_level,
            "fraud_score": final_score,
            "violation_details": details,
            "is_price_ok": is_price_ok,
            "is_brand_correct": is_brand_correct,
            "is_publishable_ok": is_publishable_ok,
            "risk_level": self.get_risk_level(final_score)
        }

    def get_risk_level(self, score):
        if score >= 60: return "Alto"
        if score >= 30: return "Medio"
        return "Bajo"
