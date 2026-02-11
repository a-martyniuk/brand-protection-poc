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
        is_authorized = product.get("seller_name", "").lower() in self.authorized_sellers
        
        # 0. Authorization Violation (Whitelist) - DISABLED per user request
        # if not is_authorized:
        #     violations.append({
        #         "violation_type": "UNAUTHORIZED_SELLER",
        #         "details": {
        #             "seller": product.get("seller_name"),
        #             "location": product.get("seller_location")
        #         }
        #     })

        for policy in self.policies:
            # Simple matching by keyword in title for PoC
            if policy["product_name"].lower() in product["title"].lower():
                
                # 1. Price Violation (MAP)
                if policy["min_price"] and product["price"] < policy["min_price"]:
                    violations.append({
                        "policy_id": policy["id"],
                        "violation_type": "PRICE",
                        "details": {
                            "expected_min": policy["min_price"],
                            "actual_price": product["price"],
                            "diff_pct": round(((policy["min_price"] - product["price"]) / policy["min_price"]) * 100, 2)
                        }
                    })

                # 2. Keyword Violation (Infringement/Counterfeit signals)
                blacklist = policy.get("keywords_blacklist") or []
                found_keywords = [kw for kw in blacklist if kw.lower() in product["title"].lower()]
                if found_keywords:
                    violations.append({
                        "policy_id": policy["id"],
                        "violation_type": "KEYWORD",
                        "details": {
                            "found_keywords": found_keywords
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
