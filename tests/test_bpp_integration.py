import asyncio
import os
from integrations.meli_bpp_client import MeliBPPClient
from logic.identification_engine import IdentificationEngine

async def test_bpp_flow():
    print("🧪 Testing BPP Integration Flow (MOCK MODE)...")
    
    engine = IdentificationEngine()
    bpp = MeliBPPClient(mock_mode=True)
    
    # 1. Simulate an Audit with a violation
    # Case: Price Violation
    audit_details = {
        "low_price": {
            "min_allowed": 5000,
            "actual_unit_price": 3750,
            "diff": 1250
        },
        "detected_qty": 4
    }
    
    print("\n1. Mapping internal violation to BPP reason...")
    reason_id, reason_desc = engine.map_violation_to_bpp_reason(audit_details)
    print(f"   Mapped: {reason_id} -> {reason_desc}")
    
    if not reason_id:
        print("❌ FAIL: Could not map violation to reason.")
        return

    # 2. Simulate BPP Reporting
    print("\n2. Reporting to MercadoLibre BPP...")
    item_id = "MLA12345678"
    result = bpp.report_violation(
        item_id=item_id,
        reason_id=reason_id,
        comment=f"Infracción detectada: {reason_desc}. Precio unidad ${audit_details['low_price']['actual_unit_price']} vs Mínimo ${audit_details['low_price']['min_allowed']}."
    )
    
    if result["status"] == "success":
        print(f"✅ SUCCESS: Reported with ID {result['complaint_id']}")
        print(f"   Message: {result['message']}")
    else:
        print(f"❌ FAIL: Error reporting to BPP: {result['message']}")

if __name__ == "__main__":
    asyncio.run(test_bpp_flow())
