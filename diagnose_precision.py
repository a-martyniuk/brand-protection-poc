import re
from logic.supabase_handler import SupabaseHandler

def diagnose():
    db = SupabaseHandler()
    print("🔍 Fetching active listings to scan for precision issues...")
    
    # Fetch all listings currently NOT marked as noise
    # We use a batch size of 1000 to be safe
    all_listings = []
    offset = 0
    while True:
        res = db.supabase.table('meli_listings').select('id, title, search_keyword').not_.like('item_status', 'noise%').range(offset, offset + 999).execute()
        data = res.data or []
        if not data: break
        all_listings.extend(data)
        if len(data) < 1000: break
        offset += 1000
    
    conflicts = []
    print(f"📊 Scanning {len(all_listings)} listings...")
    
    for l in all_listings:
        title = l.get('title', '').lower()
        # Clean title exactly like the engine does
        title_norm = title.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        title_norm = re.sub(r"[^a-z0-9\s]", " ", title_norm)
        title_norm = re.sub(r"\s+", " ", title_norm).strip()
        
        kw = (l.get('search_keyword') or '').lower()
        if not kw: continue
        
        # Check if keyword is in title but NOT as a whole word
        in_title = kw in title_norm
        whole_word = bool(re.search(rf'\b{re.escape(kw)}\b', title_norm))
        
        if in_title and not whole_word:
            conflicts.append({
                "id": l['id'],
                "kw": kw,
                "title": l['title']
            })
            
    print(f"\n✅ Scan Complete. Found {len(conflicts)} potential False Positives.")
    for c in conflicts[:50]:
        print(f"   - [KW: {c['kw']}] {c['title']}")
        
    if len(conflicts) > 50:
        print(f"   ... and {len(conflicts) - 50} more.")

if __name__ == "__main__":
    diagnose()
