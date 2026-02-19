import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from logic.supabase_handler import SupabaseHandler
from logic.identification_engine import IdentificationEngine

def cleanup_noise():
    print("🧹 Starting Database Cleanup (Purging Unrelated Noise)...")
    db = SupabaseHandler()
    engine = IdentificationEngine()
    
    # 1. Fetch all listings
    print("Fetching active listings from 'meli_listings'...")
    listings = db.supabase.table("meli_listings").select("*").execute().data
    print(f"Total listings to check: {len(listings)}")
    
    deleted_count = 0
    ids_to_delete = []
    
    for l in listings:
        title = l.get("title", "")
        # Run a quick check: does this item get hard-rejected by all master products?
        # In reality, it matches the brand part but then fails attributes.
        # We check if it matches ANY master product with a score > 0.
        
        listing_attrs = {"title": title}
        is_noise = True
        
        # Check against a sample or just run the identifies
        # If it's the noise terms we just added, they return 0, MATCH_FAILED
        
        # More direct: check against the exclusion keywords directly for efficiency
        exclusion_keywords = [
            "guia", "set de gravedad", "set enfit", "equipo de alimentacion", "sonda", 
            "bomba de alimentacion", "jeringa", "prolongador", "conexion",
            "libro", "tomo", "geometria", "contables", "manual", "tratado", "diccionario", "enciclopedia", "usado",
            "novela", "editorial", "tapa blanda", "tapa dura", "inedite", "nabu pr", "autor", "escritor",
            "pietro fortini", "annalisa fortini", "fortini brown", "franco fortini", "sara fortini",
            "padre", "cristocentrica", "vaticano", "papa", "religioso", "teologia", "renacimiento", "venecia",
            "arte y vida", "bloodlines", "venetian", "cd ", "disco", "musica", "artista", "sencillo", "album", "pista",
            "gps", "tracker", "localizador", "rastreador", "rele", "gsm", "alarma", "electrificador", "smart watch", "grasa disipadora", 
            "celular", "antena", "arduino", "modulo gprs", "sirena", "domotica", "control de accesos", "rfid", "wcdma", "central de control",
            "monofasico", "trifasico", "avisador", "electrificacion", "comunicador eventos", "g100", "genno", "zkteco", "inbio", "rastreo",
            "shiel sim", "gprs bds", "transmision voz", "posicionamiento", "abre portones", "barreras", "vecinal", "intelbras",
            "fitness", "aerobic", "plataforma escalon", "balines", "tiro al blanco", "gamo pro", "precisión", "cast irons", "afeitadora", "cortapatillas",
            "impermeabilizante", "sella fisuras", "tapa goteras", "gotita", "voligoma", "pegamento", "sellador", "caucho goma", "terrazas", "terrasas", "liquitech",
            "criogel", "lidherma", "labial", "brillo", "afirmante", "anticelulitico", "locion", "karite", "lip gloss", "micropigmentador", "cuidado de la piel",
            "limpiador", "líquido rigel", "lavanda", "colonia", "pino", "cherry", "colchon", "inflable", "camping", "flocar césped", "bateria portátil",
            "fijo rural", "gabinete verde", "videojuego", "monstruos galacticos", "licorice", "herbera", "voluminizador",
            "peptona", "linfar", "peptonum", "cambrooke", "ketovie", "cetogenik", "ketologic", "ketomeal", "digecaps", "floragut", "cisteina", "vitalis", "hongo cola de pavo",
            "vitalcan", "perro", "cachorro", "gato", "mascota", "alimento balanceado", "alimento seco",
            "detailing", "pulido", "pasta para pulir", "zeocar", "pastas de pulir",
            "acuario", "pecera", "acuarios", "carbón activado", "namaste biomineral", "oro negro", "fertilizante", "calculadora", "tester", "medidor ph", "electrodo", "medidor",
            "cepillo dental", "shampoo", "mascarilla", "toilette", "kaiak", "perfume", "otowil", "almendras", "aceite de oliva", "siete lagos", "flota flota", "flotador",
            "amortiguador", "cazoleta", "crapodina", "fusible", "filtro", "castrol", "motul", "valvoline", "liqui moly", "motorcraft", "ac delco", "gulf pride", "shell helix", "total quartz",
            "aceite mineral", "aceite sintetico", "aceite moto", "aceite motor", "20w50", "10w40", "5w30", "actevo",
            "floculante", "mak floc", "piscina", "pileta", "cloro", "compresor", "michelin", "maxi bag", "film autoadherente", "x-shot", "municiones", "goma espuma",
            "yilho", "maquina de corte", "maquina patillera", "cuchilla oster", "cool care", "corte de pelo", "recortador", "nasal", "babyliss", "wahl", "andis", "shampoo barber",
            "valcatil", "anticaida", "dentifix", "calostro",
            "whey protein", "masa muscular", "gold nutrition", "onefit",
            "postal", "russia", "stars", "biberones", "almohada", "flocadora", "plantas acuaticas", "estanques", "juntas de moto", "yamaha", "consola central"
        ]
        
        title_lower = title.lower()
        if any(kw in title_lower for kw in exclusion_keywords):
            ids_to_delete.append(l["id"])
            deleted_count += 1
            if deleted_count % 10 == 0:
                print(f"Found {deleted_count} noise items so far...")

    if ids_to_delete:
        print(f"🚨 Ready to delete {len(ids_to_delete)} items from DB.")
        # Delete in batches to avoid issues
        batch_size = 50
        for i in range(0, len(ids_to_delete), batch_size):
            batch = ids_to_delete[i:i + batch_size]
            db.supabase.table("meli_listings").delete().in_("id", batch).execute()
        print(f"✅ Successfully deleted {len(ids_to_delete)} unrelated noise items.")
    else:
        print("✨ No noise items found with current filters.")

if __name__ == "__main__":
    cleanup_noise()
