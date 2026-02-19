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
            "postal", "russia", "stars", "biberones", "almohada", "flocadora", "plantas acuaticas", "estanques", "juntas de moto", "yamaha", "consola central",
            "centella forte", "osteo-gen", "omega-3", "omega 3", "resveratrol", "andrographis", "genciana", "genikinoko", "hepatodiates", "quelat", "enzimas digestivas", "digestive enzymes", "microbiota",
            "protector cervical", "barra alta densidad", "aro flexible", "flex ring", "pilates",
            "triopo", "disparador radio", "flash", "repuesto g2 pro",
            "baberos", "babero",
            "fynutrition", "eth nutrition", "provefarma", "geonat", "igennus", "pharmepa", "genestra", "herb pharm", "euromedica", "qol labs", "physician's choice",
            "glacoxan", "hormiga", "grillo topo", "insecticida", "herbicida", "acaros", "minador",
            "casco", "ls2", "modular", "rebatible",
            "tintura madre", "amor de hortelano", "galium aparine", "galio", "hierbas medicinales", "hepatoprotector", "boldo", "alcachofa",
            "alginato sodio", "gluconolactato calcio", "gastronomia molecular", "percarbonato", "jabón cítrico", "blanqueador",
            "lifeseasons", "dr. mercola", "swanson", "xtrenght", "body advance", "picolinato de cromo", "nutricost",
            "columpio", "mecedor", "joie", "salon line", "todecacho", "gelatina definición", "pazos", "daemonium",
            "serina", "fosfatidilserina", "berberina", "berberine", "melena de leon", "mct oil", "rigo beet", "maca", "nutrirte", "frutalax", "hibiscus", "amilasa", "amiloglucosidasa",
            "plex", "bioplex", "protector decoloración", "clorhexidina", "jabón líquido", "duplex",
            "action fig", "custom scale", "male action",
            "galaxian", "salumagia", "cataclismo",
            "corpo-fuerte", "carlyle", "dra coco march", "god bless you", "leguilab", "primaforce", "nutricost",
            "gomitas", "gominolas", "moorgumy", "joyli", "agumoon", "u-cubes", "musgo marino",
            "pituitaria", "galactorrea", "inductor quiral", "oxiranos", "montacargas galactico", "sintesis de",
            "cartucho hp", "gopro", "bateria recargable", "dispenser",
            "broches", "mochila", "llavero", "bolso", "pinza para el pelo", "lentejuelas", "vintage",
            "pokemon", "tcg", "smiling critters", "poppy playtime", "booster box", "mazo de batalla",
            "brea pasta", "asfaltica", "parches autoadhesivos", "reparación de chaquetas",
            "chupete", "clip bebé",
            "omnilife", "biocros", "teatino", "theanine", "caffeine", "navitas organics", "nutrifoods", "batata morada", "lopecian", "curflex", "cúrcuma", "solgar",
            "reishi", "adaptógenos", "la aldea mdp", "mango orgánico", "diabetes", "hierbas naturales",
            "calcetines", "monedero", "tarjetero", "chaleco", "puffer", "ecocuero",
            "bachillerato", "navarro francisco", "living with pku", "el dorado cósmico", "margarita del mazo", "the flock",
            "ungüento", "katité", "luz de señalización", "señal de giro", "party supplies", "navidad", "codera", "soporte para codo", "miniaturas dnd", "tubbz",
            "panchitalk", "tbleague", "phic",
            "leslabs", "standard process", "now foods", "now suplementos", "primal fx", "dr. ludwig johnson", "okf safari",
            "ganchos de cochecito", "teether", "silla baño", "bañera", "disfraz", "halloween", "costume",
            "junta carter", "junta base", "jailing", "junta cabezal", "honda pc", "guerrero gr6",
            "cerámica", "porcelana", "lechera", "colgante", "mouse pad", "perfil ducal", "nariz escalon", "horquillas",
            "moneda", "franco", "replica", "ducado", "ducale", "casa ducal", "ducado de pastrana", "medinacelli", "duna", "monopolio",
            "genetic", "testo", "sex man", "promarine", "legion fortify", "termofit",
            "nutrinat", "adelgaza-t", "vitalpet", "artrofix", "cordyceps", "huevas de erizo",
            "metaprompts", "grimoire", "promocion artistica",
            "damonjag", "damonjäg", "hodlmoser", "krauterlikor", "licor de hierbas", "vaso acrílico", "posavasos",
            "clarificador", "alguicida", "cacique",
            "propilenglicol", "glicerina vegetal",
            "espesante", "almidón", "fecula de mandioca", "dicomere", "mandioca",
            "pulver", "nutrex", "biobellus", "atlhetica nutrition", "pellcare", "vitalil", "rubor", "i landa", "cosmética natural",
            "calefon", "zanella", "sapucai", "junta tapa",
            "ponce padilla", "defensa de la constitución", "ordenanza municipal", "baraja de cartas",
            "aceite oliva", "virgen extra", "botellón", "fecula de mandioca", "almidón", "dicomere"
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
