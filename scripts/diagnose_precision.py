import re
from logic.supabase_handler import SupabaseHandler

def diagnose():
    db = SupabaseHandler()
    print("🔍 Fetching active listings to scan for precision issues...")
    
    # Fetch all listings currently NOT marked as noise
    res = db.supabase.table('meli_listings').select('id, title, search_keyword').not_.like('item_status', 'noise%').execute()
    listings = res.data or []
    
    conflicts = []
    print(f"📊 Scanning {len(listings)} listings...")
    
    for l in listings:
        title = l.get('title', '').lower()
        kw = (l.get('search_keyword') or '').lower()
        
        if not kw: continue
        
        # Check if keyword is in title but NOT as a whole word
        in_title = kw in title
        whole_word = bool(re.search(rf'\b{re.escape(kw)}\b', title))
        
        if in_title and not whole_word:
            conflicts.append({
                "id": l['id'],
                "kw": kw,
                "title": l['title']
            })
            
    print(f"\n✅ Scan Complete. Found {len(conflicts)} potential False Positives.")
    for c in conflicts[:20]:
        print(f"   - [KW: {c['kw']}] {c['title']}")
        
    if len(conflicts) > 20:
        print(f"   ... and {len(conflicts) - 20} more.")

if __name__ == "__main__":
    diagnose()
