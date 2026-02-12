import json
from datetime import datetime

def read_enricher_status():
    """Read and display enricher status."""
    try:
        with open('enricher_status.json', 'r') as f:
            status = json.load(f)
        
        print("=" * 80)
        print("ENRICHER STATUS")
        print("=" * 80)
        
        if status.get('running'):
            print("🟢 Status: RUNNING")
        else:
            print("⚪ Status: IDLE")
        
        if status.get('started_at'):
            print(f"Started: {status['started_at']}")
        
        if status.get('last_update'):
            print(f"Last update: {status['last_update']}")
        
        print(f"\nProgress: {status.get('processed', 0)}/{status.get('total_products', 0)} products")
        print(f"  ✓ Enriched: {status.get('enriched', 0)}")
        print(f"  ✗ Failed: {status.get('failed', 0)}")
        
        if status.get('current_product'):
            current = status['current_product']
            print(f"\nCurrent product:")
            print(f"  [{current.get('timestamp')}] {current.get('meli_id')}")
            print(f"  {current.get('title')}")
            print(f"  {current.get('url')}")
        
        if status.get('history'):
            print(f"\n" + "=" * 80)
            print(f"RECENT HISTORY (last {min(10, len(status['history']))} products)")
            print("=" * 80)
            
            for entry in status['history'][-10:]:
                timestamp = entry['timestamp'].split('T')[1][:8] if 'T' in entry['timestamp'] else entry['timestamp']
                status_icon = {
                    'enriched': '✓',
                    'failed': '✗',
                    'no_data': '⚠'
                }.get(entry['status'], '?')
                
                print(f"[{timestamp}] {status_icon} {entry['meli_id']}")
                if entry.get('ean'):
                    print(f"  EAN: {entry['ean']}")
                if entry.get('error'):
                    print(f"  Error: {entry['error'][:60]}")
        
        print("\n" + "=" * 80)
        
    except FileNotFoundError:
        print("⚪ Enricher has not been run yet (no status file found)")
    except Exception as e:
        print(f"Error reading status: {e}")

if __name__ == "__main__":
    read_enricher_status()
