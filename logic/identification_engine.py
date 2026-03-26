import re
import logging
from thefuzz import fuzz
from logic.supabase_handler import SupabaseHandler
from logic.constants import (
    NUTRICIA_BRANDS, EXTERNAL_MIMICS, NOISE_CATEGORIES, 
    EXCLUSION_KEYWORDS, VOLUMETRIC_TOLERANCE, LIQUID_DENSITY_MULTIPLIER
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("IdentificationEngine")

class IdentificationEngine:
    def __init__(self):
        self.db = SupabaseHandler()
        # Cache master products for performance
        self.master_products = self.db.get_master_products()
        logger.info(f"Engine initialized with {len(self.master_products)} master products.")

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
            r'(\d+)\s*(?:unidades|units|u|un|items|uds)\b', # 12 unidades, 24u, 2 units
            r'pack\s*x?\s*(\d+)',           # Pack X 4, Pack 4
            r'pack\s+de\s+(\d+)',          # Pack de 6
            r'combo\s*x?\s*(\d+)',         # Combo X 2
            r'promo\s*x?\s*(\d+)',         # Promo X 3
            r'\bx\s?(\d+)\b',              # x 4, x24
            r'\b(\d+)\s?x\b'               # 2x, 4 x
        ]
        
        for p in qty_patterns:
            qty_match = re.search(p, text)
            if qty_match:
                # Extra check: ensure we didn't just grab part of a volume (e.g., 800g)
                candidate = int(qty_match.group(1))
                if candidate > 0 and candidate < 200: # Sanity check for quantity
                    # Ensure it's not immediately followed by a unit of measure
                    if not re.search(f'{candidate}\\s?(ml|gr|g|kg|l)\\b', text):
                        qty = candidate
                        break
            
        # 2. Find Volume/Weight: [number] [ml|g|kg|gr]
        unit_val = 0
        unit_type = None
        # Phase 20 Enhancement: Support 'grs' and 'gs' suffixes
        vol_match = re.search(r'(\d+[.,]?\d*)\s?(ml|grs?|gs?|kg|l)\b', text)
        if vol_match:
            unit_val = float(vol_match.group(1).replace(',', '.'))
            unit_type = vol_match.group(2)
            if unit_type in ['kg', 'l']:
                unit_val *= 1000
                unit_type = 'g' if unit_type == 'kg' else 'ml'
            elif unit_type in ['gr', 'grs', 'g', 'gs']:
                unit_type = 'g'

        # Calculate estimated KG
        total_kg = 0.0
        if unit_val > 0:
            if unit_type == 'g':
                total_kg = (unit_val * qty) / 1000
            elif unit_type == 'ml':
                multiplier = LIQUID_DENSITY_MULTIPLIER if "liquid" in substance_hint or "liquido" in substance_hint else 1.0
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
        
        if m_net == 0: return True, 0, 1
        
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
            # Phase 20 Enhancement: Support 'grs' and 'gs' suffixes
            val_match = re.search(r'(\d+[.,]?\d*)\s?(ml|grs?|gs?|kg|l)', str(l_net_str).lower())
            if val_match:
                val = float(val_match.group(1).replace(',', '.'))
                unit = val_match.group(2)
                
                unit_weight = 0
                if unit in ['g', 'gr', 'grs', 'gs']:
                    unit_weight = val / 1000
                elif unit in ['kg', 'l']:
                    unit_weight = val
                elif unit == 'ml':
                    multiplier = LIQUID_DENSITY_MULTIPLIER if "liquid" in m_substance or "liquido" in m_substance else 1.0
                    unit_weight = (val / 1000) * multiplier
                
                # Smart Fusion: Determine if unit_weight is for 1 unit or the whole pack
                # If it matches m_net * l_qty better than m_net, it's likely total weight
                expected_total = m_net * l_qty
                diff_unit = abs(unit_weight - m_net)
                diff_total = abs(unit_weight - expected_total)
                

                if l_qty > 1 and diff_total < diff_unit and diff_total < (expected_total * 0.15):
                    # Attribute already specifies total weight
                    l_total_kg = unit_weight
                else:
                    # Attribute likely specifies unit weight, so we multiply
                    l_total_kg = unit_weight * l_qty

        # 2. Final Fallback: Fully Regex Title if still undetermined
        if l_total_kg == 0:
            measures = self.extract_measures(title, substance_hint=m_substance)
            l_total_kg = measures.get("total_kg", 0)
        
        # If still 0, we treat it as Warning (False) instead of Silent OK (True)
        # to avoid misleading dashboard messages even if price is OK.
        if l_total_kg == 0: return False, 0, l_qty 
        
        # Scaling master weight by detected quantity for benchmark
        expected_total_kg = m_net * l_qty
        diff = abs(l_total_kg - expected_total_kg)
        return (diff < (expected_total_kg * VOLUMETRIC_TOLERANCE)), l_total_kg, l_qty

    def _check_hard_exclusions(self, title_lower, category):
        """Checks if the product should be rejected immediately based on keywords or category."""
        # 1. Keyword Exclusion
        if any(kw in title_lower for kw in EXCLUSION_KEYWORDS):
            return True, "exclusion_keyword"
            
        # 2. Category Exclusion
        if any(nc.lower() in category.lower() for nc in NOISE_CATEGORIES):
            # Special bypass for Nutricia-like items in health categories
            if not any(b in title_lower for b in ["nutrilon", "vital", "neocate", "fortisip", "fortini"]):
                return True, "noise_category"
        
        return False, None

    def _detect_brand(self, title_lower, attr_brand):
        """Attempts to detect the brand from title or attributes."""
        l_brand = (attr_brand or "").lower()
        if not l_brand:
            for b in NUTRICIA_BRANDS:
                if b in title_lower:
                    return b
        return l_brand

    def calculate_attribute_score(self, listing_attrs, master_product):
        """
        Calculates a compatibility score based on structured attributes + FC Validation.
        """
        score = 100
        matches = 0
        title_lower = listing_attrs.get("title", "").lower()
        category = listing_attrs.get("category", "")

        # 1. Hard Exclusions (REMOVED as per user request)
        # is_noise, reason = self._check_hard_exclusions(title_lower, category)
        # if is_noise:
        #    return 0, 0, l_brand

        # 2. Brand Match
        attr_brand = listing_attrs.get("brand") or listing_attrs.get("marca")
        l_brand = self._detect_brand(title_lower, attr_brand)
        m_brand = (master_product.get("brand") or "").lower()

        if l_brand and m_brand:
            if l_brand != m_brand and l_brand not in m_brand and m_brand not in l_brand:
                # Removed hard mimic rejection (external brands) for now
                score -= 60 
            else:
                matches += 1
        
        # Mandatory Brand Presence check (DISABLED for permissive mode)
        # if m_brand not in title_lower and m_brand not in l_brand:
        #    return 0, 0, l_brand # Hard rejection for lack of brand intent
            
        # 3. Categorical Consistency (REMOVED as per user request)
        # m_substance = (master_product.get("substance") or "").lower()
        # if m_substance in ["polvo", "liquido", "formula", "suplemento"]:
        #    ...

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
        [VERSION: ZeroTolerance_v4 - KeywordMandatory]
        Identifies a master product based on the search keyword provided by the scraper.
        1. REQUISITE: Search keyword must be literally present in the title.
        2. ASSOCIATION: Only then, find the best matching master product for auditing.
        """
        listing_title_norm = self.normalize_text(listing.get("title", ""))
        search_keyword = (listing.get("search_keyword") or "").lower()
        
        # 1. HARD GATE: Keyword MUST be in title
        if not search_keyword or search_keyword not in listing_title_norm:
            # We fail identification immediately if the search intent is missing from title
            return self.generate_audit_report(listing, None, 0)
            
        # 2. MATCHING: Find the best master product among those that match the brand/category
        best_match = None
        max_total_score = 0
        match_level = 0
        
        # We still look for the best SKU among ALL master products to ensure we find the right one
        # but the gate above ensures we only do this for relevant listings.
        listing_attrs = listing.get("attributes", {})
        listing_attrs["title"] = listing.get("title", "") 

        for mp in self.master_products:
            # Fuzzy match to pick the right SKU among the brand's family
            mp_name_norm = self.normalize_text(mp.get("product_name", ""))
            score = fuzz.token_set_ratio(listing_title_norm, mp_name_norm)
            
            if score > max_total_score:
                max_total_score = score
                best_match = mp

        # Determine match level based on the selected SKU's similarity
        if max_total_score >= 85: 
            match_level = 2 # Fuzzy High
        elif max_total_score >= 60: 
            match_level = 3 # Suspicious/Partial
        else:
            # Even if keyword matches, if SKU similarity is too low, we might not want to audit price
            # but for now we'll allow it as match_level 3 if keyword is present.
            match_level = 3
            
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
        details["detected_brand"] = str(detected_brand).title() if detected_brand else "Not detected"

        # Rule A: EAN Presence
        if not listing.get("ean_published") and match_level > 1:
            # score += 20
            details["missing_ean"] = True

        # Rule B: Brand Integrity
        found_brand = detected_brand or listing.get("brand_detected") or listing_attrs.get("brand") or listing_attrs.get("marca")
        if found_brand:
            brand_sim = fuzz.ratio(str(found_brand).lower(), master_product["brand"].lower())
            if brand_sim < 85:
                is_brand_correct = False
                # score += 30
                details["brand_mismatch"] = {"expected": master_product["brand"], "found": found_brand}

        # Rule C: Price Policy (ZERO TOLERANCE)
        # Using list_price from master_products as the absolute minimum
        # NEW: Volumetric Validation (Enhanced Format Fraud Detection) - Moved UP to use 'detected_qty' in price calc
        vol_match, detected_kg, detected_qty = self.validate_volumetric_match(listing_attrs, master_product)
        m_net = float(master_product.get("fc_net") or 0)
        m_units = int(master_product.get("units_per_pack") or 1)
        
        # Always include detected volume and quantity for UI clarity
        details["volumetric_info"] = {
            "detected_total_kg": round(detected_kg, 2) if detected_kg > 0 else 0,
            "unit_weight": round(detected_kg / detected_qty, 3) if (detected_kg > 0 and detected_qty > 0) else 0,
            "detected_qty": detected_qty,
            "expected_total_kg": round(m_net * detected_qty, 2) if detected_qty > 0 else m_net,
            "is_pack": detected_qty > 1
        }
        
        details["detected_volume"] = details["volumetric_info"]["detected_total_kg"]
        details["detected_qty"] = detected_qty
        
        if master_product.get("list_price"):
            actual_price = float(listing.get("price", 0))
            # Calculate Price per Unit (Standardized)
            unit_price = actual_price / detected_qty if detected_qty > 0 else actual_price
            min_price = float(master_product["list_price"])
            
            # Always include unit price for UI clarity in packs
            details["unit_price_info"] = {
                "unit_price": round(unit_price, 2),
                "detected_qty": detected_qty,
                "is_pack": detected_qty > 1
            }

            # If the quantity doesn't match the master SKU, note it
            if detected_qty != m_units:
                details["non_standard_qty"] = {
                    "listing_qty": detected_qty,
                    "master_qty": m_units,
                    "unit_price_calculated": round(unit_price, 2)
                }
                # For frontend compatibility
                details["combo_mismatch"] = {
                    "listing": detected_qty,
                    "master": m_units
                }

            if unit_price < min_price:
                is_price_ok = False
                # score += 100 # Direct 100 for price breaking
                details["low_price"] = {
                    "min_allowed": min_price, 
                    "actual_unit_price": round(unit_price, 2),
                    "total_price": actual_price,
                    "diff": round(min_price - unit_price, 2)
                }

        # Rule D: Volumetric Match result (calculated above)
        if not vol_match:
            # score += 100 # Direct 100 for format fraud
            expected_total_kg = m_net * detected_qty if detected_qty > 0 else m_net
            details["volumetric_mismatch"] = {
                "expected_total_kg": round(expected_total_kg, 2),
                "unit_master_kg": m_net,
                "detected_qty": detected_qty,
                "detected_in_listing": detected_kg if detected_kg > 0 else (listing_attrs.get("net_content") or "unmatched")
            }

        # Rule E: Restricted SKU
        if not master_product.get("is_publishable", True):
            is_publishable_ok = False
            # score += 100 # Direct 100 for restricted SKU
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
        if isinstance(reputation, dict):
            details["seller_reputation"] = {
                "level": reputation.get("level") or reputation.get("level_id"),
                "power_seller": reputation.get("power_seller")
            }
        elif isinstance(reputation, str):
            details["seller_reputation"] = {
                "level": reputation,
                "power_seller": None
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
        return "Bajo"

    def map_violation_to_bpp_reason(self, audit_details):
        """
        Maps internal audit violation flags to MercadoLibre BPP Reason IDs.
        703: Price significantly lower than suggested.
        704: Misleading information about quantity/volume.
        """
        if audit_details.get("low_price"):
            return "703", "Violación de política de precios (PVP)"
        if audit_details.get("volumetric_mismatch"):
            return "704", "Inconsistencia en contenido neto / multipack detectado"
        if audit_details.get("restricted_sku_violation"):
            return "701", "Producto de venta prohibida/restringida"
            
        return None, None
