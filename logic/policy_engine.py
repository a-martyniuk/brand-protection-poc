import json

class PolicyEngine:
    def __init__(self, policies, authorized_sellers=None):
        """
        :param policies: List of policy dictionaries from Supabase
        :param authorized_sellers: List of strings (seller names or IDs)
        """
        self.policies = policies
        self.authorized_sellers = [s.lower() for s in (authorized_sellers or [])]

    def evaluate_product(self, product):
        """
        Evaluates a single product against all relevant policies.
        :param product: Dictionary containing product data (title, price, seller, etc.)
        :return: List of detected violations
        """
        violations = []
        
        # POC Rules for Demo (Hardcoded mapping for accuracy in evaluation)
        # This maps keywords in title -> Expected MIN List Price
        POC_MAP_RULES = {
            "Profutura 1": 46000.0,
            "Profutura 2": 45000.0,
            "Profutura 3": 44000.0,
            "Profutura 4": 43000.0,
            "Vital 3": 35000.0
        }

        # 1. Determine Expected Price
        expected_price = product.get("official_expected_price")
        
        # If no expected price from context, try POC Keyword Matching
        if not expected_price:
            for kw, price in POC_MAP_RULES.items():
                if kw.lower() in product["title"].lower():
                    expected_price = price
                    break

        # 2. Price Violation (MAP)
        if expected_price and product.get("price", 0) > 0:
            if product["price"] < expected_price:
                # Calculate deviation
                diff_pct = round(((expected_price - product["price"]) / expected_price) * 100, 2)
                
                # Only flag significant drops (e.g. > 1%) to avoid noise/cents
                if diff_pct > 1.0:
                    violations.append({
                        "product_id": product.get("uuid"),
                        "violation_type": "PRICE",
                        "details": {
                            "expected_min": expected_price,
                            "actual_price": product["price"],
                            "diff_pct": diff_pct,
                            "official_id": product.get("official_product_id") or "POC_MATCHED"
                        }
                    })

        # 3. Keyword Violation (Infringement/Counterfeit signals)
        # Using a standard set of suspicious keywords for the PoC
        global_blacklist = ["replica", "imitacion", "alternativo", "tipo original", "vencida", "oferta prohibida"]
        found_keywords = [kw for kw in global_blacklist if kw.lower() in product["title"].lower()]
        
        if found_keywords:
            violations.append({
                "product_id": product.get("uuid"),
                "violation_type": "KEYWORD",
                "details": {
                    "found_keywords": found_keywords,
                    "actual_price": product["price"],
                    "official_id": product.get("official_product_id")
                }
            })
        
        return violations

    def process_all(self, products):
        """
        Processes a list of products and returns a list of violation records ready for DB insertion.
        """
        all_violations = []
        for product in products:
            product_violations = self.evaluate_product(product)
            for v in product_violations:
                # We need the product's DB UUID for the foreign key, 
                # this assumes the product has been inserted/upserted already.
                v["product_id"] = product.get("uuid") 
                all_violations.append(v)
        
        return all_violations

if __name__ == "__main__":
    # Test Data for Nutricia Bagó
    sample_policies = [
        {
            "id": "pol-nut-001",
            "product_name": "Nutrilon Profutura 4",
            "min_price": 15000,
            "keywords_blacklist": ["vencida", "oferta prohibida"]
        },
        {
            "id": "pol-nut-002",
            "product_name": "Vital 3",
            "min_price": 8000,
            "keywords_blacklist": []
        }
    ]
    
    sample_product = {
        "title": "Leche Nutrilon Profutura 4 800g - Oferta Vencida",
        "price": 12000,
        "uuid": "prod-abc-123"
    }

    engine = PolicyEngine(sample_policies)
    results = engine.evaluate_product(sample_product)
    print(json.dumps(results, indent=2))
