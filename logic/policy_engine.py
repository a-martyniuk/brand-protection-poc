import json

class PolicyEngine:
    def __init__(self, policies):
        """
        :param policies: List of policy dictionaries from Supabase
        """
        self.policies = policies

    def evaluate_product(self, product):
        """
        Evaluates a single product against all relevant policies.
        :param product: Dictionary containing product data (title, price, seller, etc.)
        :return: List of detected violations
        """
        violations = []
        
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
    # Test Data
    sample_policies = [
        {
            "id": "policy-123",
            "product_name": "iPhone 15",
            "min_price": 1000000,
            "keywords_blacklist": ["replica", "símil", "alternativo"]
        }
    ]
    
    sample_product = {
        "title": "iPhone 15 128GB - Símil Original",
        "price": 850000,
        "uuid": "prod-456"
    }

    engine = PolicyEngine(sample_policies)
    results = engine.evaluate_product(sample_product)
    print(json.dumps(results, indent=2))
