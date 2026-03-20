# logic/constants.py

# --- Brand Config ---
NUTRICIA_BRANDS = [
    "nutrilon", "vital", "neocate", "fortisip", "fortini", "nutrison", "peptisorb", "diasip", "loprofin",
    "infatrini", "ketocal", "souvenaid", "cubitan", "mct oil", "monogen", "liquigen", "secalbum", 
    "espesan", "gmpro", "galactomin", "ketoblend", "maxamum", "lophlex", "ls baby", "fortifit", 
    "duocal", "polimerosa", "advanta", "pku", "flocare", "anamix", "l'serina", "serina", "profutura"
]

EXTERNAL_MIMICS = ["vitalcan", "vitalis", "vitalife"]

# --- Classification Config ---
NOISE_CATEGORIES = [
    "Accesorios para Vehículos", "Computación", "Hogar, Muebles y Jardín", 
    "Animales y Mascotas", "Belleza y Cuidado Personal", "Industrias y Oficinas",
    "Electrónica, Audio y Video", "Celulares y Teléfonos", "Herramientas", "Construcción",
    "Libros, Revistas y Comics", "Música, Películas y Series", "Juegos y Juguetes", 
    "Antigüedades y Colecciones", "Otras categorías"
]

# --- Hard Rejection Keywords ---
# This list is used to flag items as 'noise' automatically.
EXCLUSION_KEYWORDS = [
    # Pet & Animal
    "perro", "gato", "mascotas", "vitalcan", "sieger", "dog chow", "cat chow", "cachorro", "alimento balanceado", "alimento seco", "vitalpet",
    # Pharmaceuticals
    "vitalis", "acetilcisteina", "cisteina", "farmacia", "medicamento", "laboratorio vitalis", "digecaps", "floragut", "peptona", "linfar", "peptonum", "lopecian", "curflex", "cúrcuma", "solgar",
    # Biological/Tech Mimics
    "hongo", "seta", "reishi", "melena de leon", "suplemento dietario", "jebao", "acuario", "pecera", "skimmer", "dosificadora", "iluminacion led",
    # Mobile & Tech Noise
    "funda", "vidrio templado", "celular", "case", "protector de pantalla", "cargador", "usb", "bateria", "cable", "mouse pad", "caja", "teclado", "mouse", "auriculares", "monitor", "joystick", "consola", "ps4", "ps5", "xbox", "pc", "computadora", "gamer", "rgb", "led", "electrico", "cargador portatil", "antena", "arduino", "modulo gprs", "sirena", "domotica", "control de accesos", "rfid", "wcdma", "central de control",
    # Personal Care & Beauty
    "shampoo", "acondicionador", "crema", "perfume", "fragancia", "peine", "shampoo vital", "lip gloss", "brillo", "labial", "afirmante", "anticelulitico", "locion", "karite", "micropigmentador", "cepillo dental", "mascarilla", "toilette", "kaiak", "otowil", "almendras", "aceite de oliva", "alisado", "liss expert", "l'oréal", "loreal", "serum", "sérum", "hialurónico", "colágeno", "colageno", "magnesio", "máscara capilar", "mascara capilar", "fidelite", "plex", "bioplex", "protector decoloración", "clorhexidina", "jabón líquido", "duplex", "rubor",
    # Baby Gear & Toys (Non-Nutricia)
    "cochecito", "cuna", "butaca", "bouncer", "mecedora", "juguete", "lego", "playmobil", "muñeca", "baberos", "babero", "chupete", "clip bebé", "columpio", "mecedor", "joie", "salon line", "todecacho", "gelatina definición", "ganchos de cochecito", "teether", "silla baño", "bañera", "disfraz", "halloween", "costume", "biberones", "almohada", "mordedor", "juguete de madera", "montessori",
    # Automotive & Industrial
    "motor", "auto", "camion", "moto ", "lubricante", "filtro aceite", "shell helix", "castrol", "motul", "motorcraft", "amortiguador", "cazoleta", "crapodina", "fusible", "aceite mineral", "aceite sintetico", "aceite moto", "aceite motor", "20w50", "10w40", "5w30", "actevo", "valvoline", "liqui moly", "ac delco", "gulf pride", "total quartz", "ypf extravida", "extravida", "juego de juntas", "juntas para moto", "junta", "jailing", "honda pc", "honda c 90", "honda c90", "kawasaki", "adly", "siambretta", "bulbo sensor", "sensor presion", "grasa litio", "aceite caja", "carter", "base", "tapa", "llenado",
    # Furniture & Office
    "escritorio", "mesa", "silla", "mueble", "repisa", "estante", "oficina", "biblioteca", "rack", "repuesto", "puerta", "trasera", "delantera", "baul", "gol trend", "voyage",
    # Media & Books
    "libro", "tomo", "geometria", "contables", "manual", "tratado", "diccionario", "enciclopedia", "usado", "novela", "editorial", "tapa blanda", "tapa dura", "inedite", "nabu pr", " Nabú", "autor", "escritor", "postal", "cd ", "disco", "musica", "artista", "sencillo", "pista", "una historia de", "atlas de rutas",
    # Fortini/Specific Name Noise
    "pietro fortini", "annalisa fortini", "fortini brown", "franco fortini", "sara fortini", "padre", "cristocentrica", "educacion cristocentrica", "vaticano", "papa", "religioso", "teologia", "renacimiento", "venecia", "arte y vida", "bloodlines", "venetian", "galaxian", "salumagia", "cataclismo", "mamimiau", "pastrana", "usa import cd", "ponce padilla", "defensa de la constitución", "ordenanza municipal", "baraja de cartas",
    # Construction & Chemicals
    "impermeabilizante", "sella fisuras", "tapa goteras", "gotita", "voligoma", "pegamento", "sellador", "caucho goma", "terrazas", "liquitech", "floculante", "mak floc", "piscina", "pileta", "cloro", "compresor", "michelin", "film autoadherente", "asfalto", "brea", "parches autoadhesivos", "glacoxan", "hormiga", "insecticida", "herbicida", "acaros", "alginato sodio", "gluconolactato calcio", "gastronomia molecular", "percarbonato", "jabón cítrico", "blanqueador",
    # Health/Pharma (Out of Scope)
    "ketovie", "cetogenik", "ketologic", "ketomeal", "centella forte", "osteo-gen", "omega-3", "omega 3", "resveratrol", "andrographis", "genciana", "genikinoko", "hepatodiates", "quelat", "enzimas digestivas", "digestive enzymes", "microbiota", "lifeseasons", "dr. mercola", "swanson", "xtrenght", "body advance", "picolinato de cromo", "nutricost", "fosfatidilserina", "berberina", "maca", "nutrirte", "frutalax", "hibiscus", "amilasa", "amiloglucosidasa", "gomitas", "gominolas", "moorgumy", "joyli", "agumoon", "u-cubes", "musgo marino", "omnilife", "biocros", "teatino", "theanine", "caffeine", "navitas organics", "nutrifoods", "batata morada", "berberine", "melena de leon", "cordyceps", "huevas de erizo",
    # Nootropics & Specialized Supps
    "bacopa", "tmgenex", "tmg genex", "nootropics", "threonato", "neuro-protección", "vitamina k completa", "syntha-6", "syntha 6"
]

# --- Volumetric Config ---
VOLUMETRIC_TOLERANCE = 0.15 # 15% allowance for weight mismatch
LIQUID_DENSITY_MULTIPLIER = 1.085 # Standard formula density proxy
