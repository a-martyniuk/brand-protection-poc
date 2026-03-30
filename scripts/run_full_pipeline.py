import subprocess
import sys
import time
from datetime import datetime

def run_step(name, command):
    print("-" * 50)
    print(f"STEP: {name}")
    print(f"COMMAND: {' '.join(command)}")
    print("-" * 50)
    
    start_time = time.time()
    try:
        # Run the command and stream output
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            errors='replace'
        )
        
        for line in process.stdout:
            print(line, end="")
            
        process.wait()
        
        duration = time.time() - start_time
        if process.returncode == 0:
            print(f"\n✅ {name} completed successfully in {duration:.2f}s")
            return True
        else:
            print(f"\n❌ {name} failed with exit code {process.returncode}")
            return False
            
    except Exception as e:
        print(f"\n❌ Unexpected error running {name}: {e}")
        return False

def main():
    print(f"BRAND INTELLIGENCE MASTER PIPELINE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    steps = [
        ("CLEANUP DATABASE", [sys.executable, "scripts/cleanup_db.py"]),
        ("INGEST MASTER DATA", [sys.executable, "scripts/ingest_master_data.py"]),
        ("SUPER DISCOVERY (PHASE 1)", [sys.executable, "scripts/discover_listings.py"]),
        # Identification uses the enriched data to filter noise immediately
        ("IDENTIFICATION & FILTERING (PHASE 2)", [sys.executable, "refresh_audit.py"]),
        # Phase 3 (Enrichment) - API Fast Track
        ("API ENRICHMENT (PHASE 3)", [sys.executable, "enrichers/meli_api_enricher.py", "200"]), 
        
        # Phase 4 (Enrichment) - Browser Deep Track (for EANs, Stock, and Sellers)
        ("BROWSER ENRICHMENT (PHASE 4)", [sys.executable, "enrichers/product_enricher.py", "50"]), 
        
        ("FINAL AUDIT REFRESH", [sys.executable, "refresh_audit.py"])
    ]
    
    summary = []
    for name, cmd in steps:
        success = run_step(name, cmd)
        summary.append((name, "Success" if success else "Failed"))
        
        if not success:
            print(f"\n⚠️ Pipeline interrupted due to failure in {name}")
            # Ask user input or continue? For now, we continue but mark it.
    
    print(f"\n{'='*60}")
    print(f"📊 PIPELINE SUMMARY")
    print(f"{'='*60}")
    for name, status in summary:
        icon = "[OK]" if status == "Success" else "[FAIL]"
        print(f"{icon} {name}: {status}")
    print(f"{'='*60}")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
