import re
from thefuzz import fuzz
from logic.supabase_handler import SupabaseHandler

class IdentificationEngine:
    def __init__(self):
        self.db = SupabaseHandler()
        # Cache master products for performance
        self.master_products = self.db.get_master_products()
        print(f"Identification Engine initialized with {len(self.master_products)} master products.")

    def extract_measures(self, text, substance_hint=None):
        """
        Extracts numbers associated with measures (ml, gr, unidades, xN).
        Returns a dict with 'unit_val', 'unit_type', and 'qty'.
        """
        if not text: return {"total_kg": 0}
        text = text.lower()
        substance_hint = (substance_hint or "").lower()
        
        # 1. Detect Quantity/Pack Patterns
        qty = 1
        # Match patterns like: Pack X 4, Pack de 6, 12 unidades, 24u, x24, x 4
        # We avoid matching the volume (e.g., 800g) as quantity by using word boundaries or specific markers
        qty_patterns = [
            r'(\d+)\s*(?:unidades|units|u|un|items|uds)\b', # 12 unidades, 24u, 2 units
            r'pack\s*x?\s*(\d+)',           # Pack X 4, Pack 4
            r'pack\s+de\s+(\d+)',          # Pack de 6
            r'combo\s*x?\s*(\d+)',         # Combo X 2
            r'promo\s*x?\s*(\d+)',         # Promo X 3
            r'\bx\s?(\d+)\b',              # x 4, x24
            r'\b(\d+)\s?x\b'               # 2x, 4 x
        ]
        
        for p in qty_patterns:
            qty_match = re.search(p, text)
            if qty_match:
                # Extra check: ensure we didn't just grab part of a volume (e.g., 800g)
                candidate = int(qty_match.group(1))
                if candidate > 0 and candidate < 200: # Sanity check for quantity
                    # Ensure it's not immediately followed by a unit of measure
                    if not re.search(f'{candidate}\\s?(ml|gr|g|kg|l)\\b', text):
                        qty = candidate
                        break
            
        # 2. Find Volume/Weight: [number] [ml|g|kg|gr]
        unit_val = 0
        unit_type = None
        # Phase 20 Enhancement: Support 'grs' and 'gs' suffixes
        vol_match = re.search(r'(\d+[.,]?\d*)\s?(ml|grs?|gs?|kg|l)\b', text)
        if vol_match:
            unit_val = float(vol_match.group(1).replace(',', '.'))
            unit_type = vol_match.group(2)
            if unit_type in ['kg', 'l']:
                unit_val *= 1000
                unit_type = 'g' if unit_type == 'kg' else 'ml'
            elif unit_type in ['gr', 'grs', 'g', 'gs']:
                unit_type = 'g'

        # Calculate estimated KG
        total_kg = 0.0
        if unit_val > 0:
            if unit_type == 'g':
                total_kg = (unit_val * qty) / 1000
            elif unit_type == 'ml':
                multiplier = 1.085 if "liquid" in substance_hint or "liquido" in substance_hint else 1.0
                total_kg = ((unit_val * qty) / 1000) * multiplier
                
        return {"total_kg": total_kg, "qty": qty, "unit_val": unit_val, "unit_type": unit_type}

    def normalize_text(self, text):
        if not text: return ""
        text = text.lower()
        # Remove accents
        text = re.sub(r'[áàäâ]', 'a', text)
        text = re.sub(r'[éèëê]', 'e', text)
        text = re.sub(r'[íìïî]', 'i', text)
        text = re.sub(r'[óòöô]', 'o', text)
        text = re.sub(r'[úùüû]', 'u', text)
        # Remove symbols and common noise
        text = re.sub(r'[^a-z0-9\s]', '', text)
        return " ".join(text.split())

    def validate_volumetric_match(self, listing_attrs, master_product):
        """
        Uses FC (Net) and units per pack to validate if the listing volume matches the master SKU.
        Prioritizes enriched structured attributes but cross-references title for multipliers.
        """
        m_net = float(master_product.get("fc_net") or 0)
        m_substance = (master_product.get("substance") or "").lower()
        
        if m_net == 0: return True, 0, 1
        
        # 1. Try to use Enriched Structured Attributes for Volume
        l_net_str = listing_attrs.get("net_content") or listing_attrs.get("weight") or listing_attrs.get("peso neto")
        l_units_str = listing_attrs.get("units_per_pack") or listing_attrs.get("unidades por pack") or listing_attrs.get("cantidad de unidades")
        
        l_total_kg = 0.0
        l_qty = 1
        
        # Get structured quantity if available
        if l_units_str:
            qty_match = re.search(r'(\d+)', str(l_units_str))
            if qty_match: l_qty = int(qty_match.group(1))
        
        # If quantity is still 1, scan the title for potential "Pack X N" patterns
        title = (listing_attrs.get("title") or "").lower()
        if l_qty == 1 and title:
            measures_title = self.extract_measures(title, substance_hint=m_substance)
            # If extract_measures found a qty > 1, use it
            if measures_title.get("qty", 1) > 1:
                l_qty = measures_title["qty"]
        
        if l_net_str:
            # Simple extraction from structured "800g" or "1kg"
            # Phase 20 Enhancement: Support 'grs' and 'gs' suffixes
            val_match = re.search(r'(\d+[.,]?\d*)\s?(ml|grs?|gs?|kg|l)', str(l_net_str).lower())
            if val_match:
                val = float(val_match.group(1).replace(',', '.'))
                unit = val_match.group(2)
                
                unit_weight = 0
                if unit in ['g', 'gr', 'grs', 'gs']:
                    unit_weight = val / 1000
                elif unit in ['kg', 'l']:
                    unit_weight = val
                elif unit == 'ml':
                    multiplier = 1.085 if "liquid" in m_substance or "liquido" in m_substance else 1.0
                    unit_weight = (val / 1000) * multiplier
                
                # Smart Fusion: Determine if unit_weight is for 1 unit or the whole pack
                # If it matches m_net * l_qty better than m_net, it's likely total weight
                expected_total = m_net * l_qty
                diff_unit = abs(unit_weight - m_net)
                diff_total = abs(unit_weight - expected_total)
                

                if l_qty > 1 and diff_total < diff_unit and diff_total < (expected_total * 0.15):
                    # Attribute already specifies total weight
                    l_total_kg = unit_weight
                else:
                    # Attribute likely specifies unit weight, so we multiply
                    l_total_kg = unit_weight * l_qty

        # 2. Final Fallback: Fully Regex Title if still undetermined
        if l_total_kg == 0:
            measures = self.extract_measures(title, substance_hint=m_substance)
            l_total_kg = measures.get("total_kg", 0)
        
        # If still 0, we treat it as Warning (False) instead of Silent OK (True)
        # to avoid misleading dashboard messages even if price is OK.
        if l_total_kg == 0: return False, 0, l_qty 
        
        # Scaling master weight by detected quantity for benchmark
        expected_total_kg = m_net * l_qty
        diff = abs(l_total_kg - expected_total_kg)
        return (diff < (expected_total_kg * 0.15)), l_total_kg, l_qty

    def calculate_attribute_score(self, listing_attrs, master_product):
        """
        Calculates a compatibility score based on structured attributes + FC Validation.
        Also implements strict rejection for known false positives (e.g., pet food).
        """
        score = 100
        matches = 0
        
        # 0. Anti-False Positive Keywords (Hard Rejection)
        title_lower = listing_attrs.get("title", "").lower()
        exclusion_keywords = [
            # Pet & Animal (Vitalcan, etc.)
            "perro", "gato", "mascotas", "vitalcan", "sieger", "dog chow", "cat chow",
            # Pharmaceuticals (Vitalis, etc.)
            "vitalis", "acetilcisteina", "cisteina", "farmacia", "medicamento", "laboratorio vitalis",
            # Biological/Tech Mimics (Hongo, Jebao)
            "hongo", "seta", "reishi", "melena de leon", "suplemento dietario",
            "jebao", "acuario", "pecera", "skimmer", "dosificadora", "iluminacion led",
            # Mobile & Tech Noise (Common overlaps)
            "funda", "vidrio templado", "celular", "case", "protector de pantalla",
            # Personal Care & Beauty
            "shampoo", "acondicionador", "crema", "perfume", "fragancia", "peine", "shampoo vital",
            # Baby Gear & Toys (Non-Nutricia)
            "cochecito", "cuna", "butaca", "bouncer", "mecedora", "juguete", "lego", "playmobil", "muñeca",
            # Automotive & Industrial (Conflicts with MCT Oil / Aceite de Lorenzo)
            "motor", "auto", "camion", "moto ", "lubricante", "filtro aceite", "shell helix", "castrol", "motul", "motorcraft",
            # Furniture & Office (Conflicts with GMPro)
            "escritorio", "mesa", "silla", "mueble", "repisa", "estante", "oficina", "biblioteca", "rack",
            # Gaming & Tech (Conflicts with GMPro)
            "gamer", "rgb", "led", "pc", "computadora", "teclado", "mouse", "auriculares", "monitor", "joystick", "consola", "ps4", "ps5", "xbox",
            # Electronics & Home (Conflicts with GMPro)
            "electrico", "altura regulable", "cable", "usb", "bateria", "cargador", "lampara",
            # Medical Consumables (Exclude from match with Nutritional Products)
            "guia", "set de gravedad", "set enfit", "equipo de alimentacion", "sonda", 
            "bomba de alimentacion", "jeringa", "prolongador", "conexion",
            # Books, Publishing & Authors (Conflicts with Fortini, etc.)
            "libro", "tomo", "geometria", "contables", "manual", "tratado", "diccionario", "enciclopedia", "usado",
            "novela", "editorial", "tapa blanda", "tapa dura", "inedite", "nabu pr", " Nabú", "autor", "escritor",
            "pietro fortini", "annalisa fortini", "fortini brown", "franco fortini", "sara fortini",
            # Religion & History (Conflicts with Fortini names)
            "padre", "cristocentrica", "educacion cristocentrica", "vaticano", "papa", "religioso", "teologia", "renacimiento", "venecia",
            "arte y vida", "bloodlines", "venetian",
            # Media & Music
            "disco", "musica", "artista", "sencillo", "pista",
            # Electronics, Security & specialized Tech (Common Noise)
            "gps", "tracker", "localizador", "rastreador", "rele", "gsm", "alarma", "electrificador", "smart watch", "grasa disipadora", 
            "celular", "antena", "arduino", "modulo gprs", "sirena", "domotica", "control de accesos", "rfid", "wcdma", "central de control",
            "monofasico", "trifasico", "avisador", "electrificacion", "comunicador eventos", "g100", "genno", "zkteco", "inbio", "rastreo",
            "shiel sim", "gprs bds", "transmision voz", "posicionamiento", "abre portones", "barreras", "vecinal", "intelbras",
            # Fitness & Sports
            "fitness", "aerobic", "plataforma escalon", "balines", "tiro al blanco", "gamo pro", "precisión", "cast irons", "afeitadora", "cortapatillas",
            # Construction, Hardware & Adhesives
            "impermeabilizante", "sella fisuras", "tapa goteras", "gotita", "voligoma", "pegamento", "sellador", "caucho goma", "terrazas", "terrasas", "liquitech",
            # Beauty, Dermo-cosmetics & Personal Care
            "criogel", "lidherma", "labial", "brillo", "afirmante", "anticelulitico", "locion", "karite", "lip gloss", "micropigmentador", "cuidado de la piel",
            # Cleaning, Chemicals & Home
            "limpiador", "líquido rigel", "lavanda", "colonia", "pino", "cherry", "colchon", "inflable", "camping", "flocar césped", "bateria portátil",
            # Pharma/Supplements (Out of Scope)
            "peptona", "linfar", "peptonum", "cambrooke", "ketovie", "cetogenik", "ketologic", "ketomeal", "digecaps", "floragut", "cisteina", "vitalis", "hongo cola de pavo",
            # Pets & Animal Care
            "vitalcan", "perro", "cachorro", "gato", "mascota", "alimento balanceado", "alimento seco",
            # Car Care & Detailing
            "detailing", "pulido", "pasta para pulir", "zeocar", "pastas de pulir",
            # Aquarium, Garden & Tools
            "acuario", "pecera", "acuarios", "carbón activado", "namaste biomineral", "oro negro", "fertilizante", "calculadora", "tester", "medidor ph", "electrodo", "medidor",
            # Hygiene, Beauty & Misc Home
            "cepillo dental", "shampoo", "mascarilla", "toilette", "kaiak", "perfume", "otowil", "almendras", "aceite de oliva", "siete lagos", "flota flota", "flotador",
            # Automotive Maintenance & Oils
            "amortiguador", "cazoleta", "crapodina", "fusible", "filtro", "castrol", "motul", "valvoline", "liqui moly", "motorcraft", "ac delco", "gulf pride", "shell helix", "total quartz",
            "aceite mineral", "aceite sintetico", "aceite moto", "aceite motor", "20w50", "10w40", "5w30", "actevo",
            # Pool, Tools & Toys
            "floculante", "mak floc", "piscina", "pileta", "cloro", "compresor", "michelin", "maxi bag", "film autoadherente", "x-shot", "municiones", "goma espuma",
            # Barber & Haircutting
            "yilho", "maquina de corte", "maquina patillera", "cuchilla oster", "cool care", "corte de pelo", "recortador", "nasal", "babyliss", "wahl", "andis", "shampoo barber",
            # Personal Care & Hair Loss (Verify if Valcatil is noise) - Keeping it for now if it's unrelated, but being cautious
            "valcatil", "anticaida", "dentifix", "calostro",
            # Sports Nutrition
            "whey protein", "masa muscular", "gold nutrition", "onefit",
            # Collectibles & Misc
            "postal", "russia", "stars", "biberones", "almohada", "flocadora", "plantas acuaticas", "estanques", "juntas de moto", "yamaha", "consola central",
            # Phase 6: Misc Supplements (Out of Scope)
            "centella forte", "osteo-gen", "omega-3", "omega 3", "resveratrol", "andrographis", "genciana", "genikinoko", "hepatodiates", "quelat", "enzimas digestivas", "digestive enzymes", "microbiota",
            # Phase 6: Fitness & Gym Gear
            "protector cervical", "barra alta densidad", "aro flexible", "flex ring", "pilates",
            # Phase 6: Photography/Electronics
            "triopo", "disparador radio", "flash", "repuesto g2 pro",
            # Phase 6: Baby/Clothing
            "baberos", "babero",
            # Phase 6: Out-of-Scope Brands
            "fynutrition", "eth nutrition", "provefarma", "geonat", "igennus", "pharmepa", "genestra", "herb pharm", "euromedica", "qol labs", "physician's choice",
            # Phase 7: Garden/Insecticides/Herbicides
            "glacoxan", "hormiga", "grillo topo", "insecticida", "herbicida", "acaros", "minador",
            # Phase 7: Motorcycle Gear
            "casco", "ls2", "modular", "rebatible",
            # Phase 7: Herbal/Medicinal Plants
            "tintura madre", "amor de hortelano", "galium aparine", "galio", "hierbas medicinales", "hepatoprotector", "boldo", "alcachofa",
            # Phase 7: Cleaning/Chemicals (Misc)
            "alginato sodio", "gluconolactato calcio", "gastronomia molecular", "percarbonato", "jabón cítrico", "blanqueador",
            # Phase 7: Out-of-Scope Brands (Supplements)
            "lifeseasons", "dr. mercola", "swanson", "xtrenght", "body advance", "picolinato de cromo", "nutricost",
            # Phase 7: Baby Gear & Misc
            "columpio", "mecedor", "joie", "salon line", "todecacho", "gelatina definición", "pazos", "daemonium",
            # Phase 8: Amino Acids & Supplements (Out of Scope)
            "fosfatidilserina", "berberina", "berberine", "melena de leon", "rigo beet", "maca", "nutrirte", "frutalax", "hibiscus", "amilasa", "amiloglucosidasa",
            # Phase 8: Cosmetics & Hair Care
            "plex", "bioplex", "protector decoloración", "clorhexidina", "jabón líquido", "duplex",
            # Phase 8: Action Figures & Toys
            "action fig", "custom scale", "male action",
            # Phase 8: Obscure Books & Titles
            "galaxian", "salumagia", "cataclismo",
            # Phase 8: Out-of-Scope Brands
            "corpo-fuerte", "carlyle", "dra coco march", "god bless you", "leguilab", "primaforce", "nutricost",
            # Phase 9: Gummies & Candy-like Supplements
            "gomitas", "gominolas", "moorgumy", "joyli", "agumoon", "u-cubes", "musgo marino",
            # Phase 9: Books & Educational/Medical Info
            "pituitaria", "galactorrea", "inductor quiral", "oxiranos", "montacargas galactico", "sintesis de",
            # Phase 9: Electronics & General Tools
            "cartucho hp", "gopro", "bateria recargable", "dispenser",
            # Phase 9: Fashion, Travel & Accessories
            "broches", "mochila", "llavero", "bolso", "pinza para el pelo", "lentejuelas", "vintage",
            # Phase 9: Toys & Collectibles
            "pokemon", "tcg", "smiling critters", "poppy playtime", "booster box", "mazo de batalla",
            # Phase 9: Construction & Hardware
            "brea pasta", "asfaltica", "parches autoadhesivos", "reparación de chaquetas",
            # Phase 9: Baby Misc
            "chupete", "clip bebé",
            # Phase 9: Out-of-Scope Brands & Specific Supps
            "omnilife", "biocros", "teatino", "theanine", "caffeine", "navitas organics", "nutrifoods", "batata morada", "lopecian", "curflex", "cúrcuma", "solgar",
            # Phase 10: Adaptogens & Natural Treatments (Misc)
            "reishi", "adaptógenos", "la aldea mdp", "mango orgánico", "diabetes", "hierbas naturales",
            # Phase 10: Clothing & Fashion
            "calcetines", "monedero", "tarjetero", "chaleco", "puffer", "ecocuero",
            # Phase 10: Books (Educational & Fiction)
            "bachillerato", "navarro francisco", "living with pku", "el dorado cósmico", "margarita del mazo", "the flock",
            # Phase 10: Misc Home & Gear
            "ungüento", "katité", "luz de señalización", "señal de giro", "party supplies", "navidad", "codera", "soporte para codo", "miniaturas dnd", "tubbz",
            # Phase 10: Action Figure Clothing
            "panchitalk", "tbleague", "phic",
            # Phase 10: Out-of-Scope Brands
            "leslabs", "standard process", "now foods", "now suplementos", "primal fx", "dr. ludwig johnson", "okf safari",
            # Phase 11: Baby Gear & Toys
            "ganchos de cochecito", "teether", "silla baño", "bañera", "disfraz", "halloween", "costume",
            # Phase 11: Moto & Engine Parts
            "junta carter", "junta base", "jailing", "junta cabezal", "honda pc", "guerrero gr6",
            # Phase 11: Home & Decor noise
            "cerámica", "porcelana", "lechera", "colgante", "mouse pad", "perfil ducal", "nariz escalon", "horquillas",
            # Phase 11: Collectibles & History
            "moneda", "franco", "replica", "ducado", "ducale", "casa ducal", "ducado de pastrana", "medinacelli", "duna", "monopolio",
            # Phase 11: Sports & Performance (Hard Rejection)
            "genetic", "testo", "sex man", "promarine", "legion fortify", "termofit",
            # Phase 11: Misc Health (Out of scope)
            "nutrinat", "adelgaza-t", "vitalpet", "artrofix", "cordyceps", "huevas de erizo",
            # Phase 11: Books (More labels)
            "metaprompts", "grimoire", "promocion artistica",
            # Phase 12: Liquor & Aperitifs
            "damonjag", "damonjäg", "hodlmoser", "krauterlikor", "licor de hierbas", "vaso acrílico", "posavasos",
            # Phase 12: Pool Chemicals
            "clarificador", "alguicida", "cacique",
            # Phase 12: Industrial & Chemistry
            "propilenglicol", "glicerina vegetal",
            # Phase 12: Food & Cooking
            "espesante", "almidón", "fecula de mandioca", "dicomere", "mandioca",
            # Phase 12: General Health & Cosmetics (Out of scope)
            "pulver", "nutrex", "biobellus", "atlhetica nutrition", "pellcare", "vitalil", "rubor", "i landa", "cosmética natural",
            # Phase 12: Misc Home & Moto
            "calefon", "zanella", "sapucai", "junta tapa",
            # Phase 12: Legal & Books (Labels)
            "ponce padilla", "defensa de la constitución", "ordenanza municipal", "baraja de cartas",
            # Phase 13: Olive Oil & Broad Food
            "aceite oliva", "virgen extra", "botellón", "fecula de mandioca", "almidón", "dicomere",
            # Phase 14: Keto, MCT & Food Noise
            "alfajor", "low carb", "dátil", "mayonesa", "salsa", "harina", "cetomix",
            # Phase 14: Competitor & Large Health Brands
            "ensure", "glucerna", "abbott", "natier", "nutrinías", "ahora suplementos", "gentech", "hochsport",
            # Phase 14: Sports & Misc Supplements
            "creatina", "natural whey", "propoleo",
            # Phase 14: Beauty, Hair & Clothing
            "alisado", "liss expert", "l'oréal", "loreal", "babydoll", "conejita", "ropa interior", "adornos navideños",
            # Phase 14: Auto & Books (Misc)
            "ypf extravida", "extravida", "bestway", "intex", "fluoretação", "heroina intergalactica", "maximalismo", "una historia de",
            # Phase 15: Competitors (Baby Milk)
            "sancor bebe", "sancor bebé", "nido", "hero baby",
            # Phase 15: Generic Milks & Basic Foods
            "leche entera", "leche descremada", "leche en polvo", "larga vida", "fortificada",
            # Phase 15: Health & Beauty Noise
            "arcor bagó", "arcor bago", "star nutrition", "centrum", "la roche-posay", "roche-posay", "alfaparf", "alta moda", "serum", "sérum", "hialurónico", "colágeno", "colageno", "magnesio",
            # Phase 15: Misc & Hardware
            "hypertherm", "tobera", "tapete", "foam infantil", "maternidad", "vestido", "hartmann", "simplicius", "linanthus",
            # Phase 16: Shake & Competitor Specialists
            "shake mix", "remplaza comida", "comida con", "comidamed", "aminomeed",
            # Phase 16: Motor Parts (Gaskets)
            "juego de juntas", "juntas para moto", "junta completa", "juki", "morini", "mondial", "honda c 90", "honda c90",
            # Phase 16: Lingerie & Sexy Clothing
            "lencería", "sexual", "sexy", "encaje", "pijama", "camisola", "body sexy",
            # Phase 16: Baby Gear & Toys
            "cortapelo", "audifonos baby", "baby bump", "hair clip", "tummy time", "juguetes sensoriales",
            # Phase 16: Misc Home & Specialized Health
            "dulkre", "edulcorante", "plato decorativo", "crown ducal", "etiquetas escolares", "lubricante intimo", "lubrigel", "refresh liquigel", "gotas lubricantes", "monoherb", "tremella",
            # Phase 17: Motor & Industrial (Kawasaki, Electrical)
            "kawasaki", "adly", "siambretta", "vimergy", "cable acelerador", "bomba de aceite", "grasa litio", "bulbo sensor", "sensor presion", "interruptor termomagnetico", "interruptor termomagnético", "aceite caja",
            # Phase 17: Clothing & Baby Safety
            "remera", "body bebe", "body bebé", "candado de seguridad", "regaliz",
            # Phase 17: Specialized Supplements & Hair
            "pudding", "protein factory", "syntha-6", "syntha 6", "goma xantica", "syrup fusion", "oleos vitales", "system 3",
            # Phase 18: Nootropics & Specialized Supplements
            "bacopa", "tmgenex", "tmg genex", "nootropics", "threonato", "neuro-protección", "vitamina k completa",
            # Phase 18: Competitors (Specialist Milk)
            "aminomed", "fresenius kabi", "nutribio",
            # Phase 18: Industrial & Tooling
            "jebao", "diodo doble", "boyero eléctrico", "regulador de carga", "pedal max", "aceite gulf", "pegamil", "bulit azul",
            # Phase 18: Food & Oil Misc
            "aceite de coco", "aceite de ricino", "ducoco", "maniax", "maxim white", "mocha gold",
            # Phase 18: Misc (Books & CDs)
            "mamimiau", "pastrana", "usa import cd",
            # Phase 19: Competitors & Specific Lines
            "sancor advanced", "nuskin", "lifepak", "pampita", "collagen", "colágeno", "colageno",
            # Phase 19: Generic Pharma & Hair
            "total magnesiano", "fidelite", "máscara capilar", "mascara capilar",
            # Phase 19: Motor & Accessories
            "tapa llenado", "funda compatible", "ufree", "novah",
            # Phase 20: Nutricia Adjacent (Aggressive Noise)
            "fresubin", "frebini", "reconvan", "fresenius kabi",
            # Phase 21: Liquor & Generic Oils
            "licor", "giffard", "lichi-li", "aceite de cocina", "aceite de girasol", "aceite mezcla",
            # Phase 22: Typos & Generic Filter Refinement
            "infantrini", "infartrini", "aceite nativo", "aceite de oliva", "aceite puro",
            # Phase 23: Aggressive Noise (Identificando...)
            "casco", "ls2", "escritorio", "fusible", "bateria", "alimento balanceado", "perro", "gato", "asfalto", "brea", "tintura", "ampolla", "rgb", "gamer",
            "mueble", "silla", "colchoneta", "gimnasia", "pilates", "arduino", "gsm", "gps", "tracker", "alarma", "rele", "relé", "celular", "funda", "vidrio templado",
            "repuesto", "junta", "motor", "aceite moto", "aceite motor", "lubricante", "afeitadora", "cortapatillas", "perfume", "fragancia",
            # Phase 24: Screenshot Noise (Identificando... Refined)
            "puerta", "trasera", "delantera", "baul", "gol trend", "voyage", "muñeco", "figura de carton", "dune", "monopoly", "atlas de rutas", "despolvillador",
            "yerba", "toalla", "pelota", "mordedor", "juguete de madera", "montessori", "handheld grass", "máquina para césped", "charla interactiva", "moldes para tubos",
            "gabapentina", "cd ", "libro", "manual", "historia de", "caracterización"
        ]
        if any(kw in title_lower for kw in exclusion_keywords):
            return 0, 0, None # Hard rejection for noise
            
        # 0.1 Category-Based Rejection (Aggressive)
        noise_categories = [
            "Accesorios para Vehículos", "Computación", "Hogar, Muebles y Jardín", 
            "Animales y Mascotas", "Belleza y Cuidado Personal", "Industrias y Oficinas",
            "Electrónica, Audio y Video", "Celulares y Teléfonos", "Herramientas", "Construcción",
            "Libros, Revistas y Comics", "Música, Películas y Series", "Juegos y Juguetes", 
            "Antigüedades y Colecciones", "Otras categorías"
        ]
        l_cat = listing_attrs.get("category", "")
        if any(nc.lower() in l_cat.lower() for nc in noise_categories):
            # Special bypass for Nutricia-like items in health categories
            if not any(b in title_lower for b in ["nutrilon", "vital", "neocate", "fortisip", "fortini"]):
                return 0, 0, None

        # 1. Brand Match (Critical)
        l_brand = (listing_attrs.get("brand") or listing_attrs.get("marca") or "").lower()
        m_brand = (master_product.get("brand") or "").lower()
        
        # If scraper didn't detect brand, try to find it in title
        nutricia_brands = [
            "nutrilon", "vital", "neocate", "fortisip", "fortini", "nutrison", "peptisorb", "diasip", "loprofin",
            "infatrini", "ketocal", "souvenaid", "cubitan", "mct oil", "monogen", "liquigen", "secalbum", 
            "espesan", "gmpro", "galactomin", "ketoblend", "maxamum", "lophlex", "ls baby", "fortifit", 
            "duocal", "polimerosa", "advanta", "pku", "flocare", "anamix", "l'serina", "serina", "profutura"
        ]
        if not l_brand:
            for b in nutricia_brands:
                if b in title_lower:
                    l_brand = b
                    break
        
        if l_brand and m_brand:
            # If brands are explicitly different and non-overlapping, it's a mismatch
            if l_brand != m_brand and l_brand not in m_brand and m_brand not in l_brand:
                # REJECT known external brands that mimic Nutricia names
                external_mimics = ["vitalcan", "vitalis", "vitalife"]
                if any(mimic in title_lower for mimic in external_mimics):
                    return 0, 0, l_brand # Hard rejection
                score -= 60 
            else:
                matches += 1
        
        # NEW CRITICAL RULE: Mandatory Brand Presence
        # If the master brand keyword is not in the title, reject the match
        # This prevents generic "infant" or "protein" products from other brands from matching
        if m_brand not in title_lower and m_brand not in l_brand:
            return 0, 0, l_brand # Hard rejection for lack of brand intent
            
        # 1.1 Category Consistency check
        # If the master is a supplement/formula but the title strongly indicates furniture/tech
        m_substance = (master_product.get("substance") or "").lower()
        if m_substance in ["polvo", "liquido", "formula", "suplemento"]:
            tech_indicators = ["gamer", "rgb", "escritorio", "monitor", "pc", "teclado"]
            if any(ti in title_lower for ti in tech_indicators):
                return 0, 0, "Categorical Mismatch"

        # 2. Volumetric/FC Validation (Updated with structured data)
        vol_match, detected_kg, detected_qty = self.validate_volumetric_match(listing_attrs, master_product)
        if not vol_match:
            score -= 60 # Heavy penalty for format fraud
        else:
            matches += 1

        # 3. Stage Match
        m_stage = str(master_product.get("stage") or "").lower()
        if m_stage and m_stage != "nan" and m_stage != "none":
            l_text = (title_lower + " " + str(listing_attrs.get("stage", ""))).lower()
            if m_stage in l_text:
                matches += 1
            else:
                score -= 30

        return max(0, score), matches, l_brand

    def identify_product(self, listing):
        """
        Executes weighted matching logic and returns a comprehensive audit report.
        """
        listing_title_norm = self.normalize_text(listing.get("title", ""))
        listing_ean = listing.get("ean_published")
        listing_attrs = listing.get("attributes", {})
        listing_attrs["title"] = listing.get("title", "") 
        
        best_match = None
        match_level = 0
        max_total_score = 0
        
        # 1. Level 1: Match exact by EAN (Strong) - Priority
        if listing_ean:
            for mp in self.master_products:
                if mp.get("ean") == listing_ean:
                    best_match = mp
                    match_level = 1
                    break

        # 2. Level 2: Weighted Attribute + Title Match
        # Pre-detect brand to use in strict floors
        l_brand = (listing_attrs.get("brand") or listing_attrs.get("marca") or "").lower()
        if not l_brand:
            nutricia_brands = ["nutrilon", "vital", "neocate", "fortisip", "fortini", "nutrison", "peptisorb", "diasip", "loprofin", "profutura"]
            for b in nutricia_brands:
                if b in listing_title_norm:
                    l_brand = b
                    break

        for mp in self.master_products:
            # Title Similarity (40%)
            mp_name_norm = self.normalize_text(mp.get("product_name", ""))
            title_sim = fuzz.token_set_ratio(listing_title_norm, mp_name_norm)
            
            # Attribute Similarity (60%)
            attr_score, attr_matches, detected_brand = self.calculate_attribute_score(listing_attrs, mp)
            
            # MANDATORY REJECTION
            if attr_score == 0:
                continue

            # Combined Score
            total_score = (title_sim * 0.4) + (attr_score * 0.6)
                
            # 3. Dynamic Thresholds & Hard Floors
            # If title similarity is extremely low, it's a candidate for rejection
            if title_sim < 40 and total_score < 80: 
                total_score = 0 # Hard floor for unrelated titles

            # If NO brand was detected and similarity is not strong, reject
            if not l_brand and title_sim < 60:
                total_score = 0

            if total_score > max_total_score:
                max_total_score = total_score
                best_match = mp

        if max_total_score >= 85: 
            match_level = 2
        elif max_total_score >= 70: 
            match_level = 3
        else:
            match_level = 0
            best_match = None if max_total_score < 60 else best_match

        # 3. Generate Full Audit
        audit = self.generate_audit_report(listing, best_match, match_level)
        return audit

    def generate_audit_report(self, listing, master_product, match_level):
        """
        Runs all compliance rules and returns result + score.
        [VERSION: ZeroTolerance_v3]
        """
        details = {}
        score = 0
        is_price_ok = True
        is_brand_correct = True
        is_publishable_ok = True
        
        if not master_product:
            return {
                "master_product_id": None,
                "match_level": 0,
                "fraud_score": 0, # Unidentified is NOT a violation by default
                "violation_details": {"unidentified": True, "note": "Listing ignored (No Nutricia match)"},
                "is_price_ok": True,
                "is_brand_correct": True,
                "is_publishable_ok": True,
                "risk_level": "Bajo"
            }

        # 1. Attribute-Based Confidence Details
        listing_attrs = listing.get("attributes", {})
        listing_attrs["title"] = listing.get("title", "")
        attr_score, attr_matches, detected_brand = self.calculate_attribute_score(listing_attrs, master_product)
        details["attribute_breakdown"] = {
            "score": attr_score,
            "matches_count": attr_matches,
            "brand": detected_brand or listing_attrs.get("brand") or listing_attrs.get("marca"),
            "net_content": listing_attrs.get("net_content") or listing_attrs.get("weight")
        }
        
        # Explicitly store detected brand for UI
        details["detected_brand"] = detected_brand.title() if detected_brand else "Not detected"

        # Rule A: EAN Presence
        if not listing.get("ean_published") and match_level > 1:
            score += 20
            details["missing_ean"] = True

        # Rule B: Brand Integrity
        found_brand = detected_brand or listing.get("brand_detected") or listing_attrs.get("brand") or listing_attrs.get("marca")
        if found_brand:
            brand_sim = fuzz.ratio(str(found_brand).lower(), master_product["brand"].lower())
            if brand_sim < 85:
                is_brand_correct = False
                score += 30
                details["brand_mismatch"] = {"expected": master_product["brand"], "found": found_brand}

        # Rule C: Price Policy (ZERO TOLERANCE)
        # Using list_price from master_products as the absolute minimum
        # NEW: Volumetric Validation (Enhanced Format Fraud Detection) - Moved UP to use 'detected_qty' in price calc
        vol_match, detected_kg, detected_qty = self.validate_volumetric_match(listing_attrs, master_product)
        m_net = float(master_product.get("fc_net") or 0)
        m_units = int(master_product.get("units_per_pack") or 1)
        
        # Always include detected volume and quantity for UI clarity
        details["volumetric_info"] = {
            "detected_total_kg": round(detected_kg, 2) if detected_kg > 0 else 0,
            "unit_weight": round(detected_kg / detected_qty, 3) if (detected_kg > 0 and detected_qty > 0) else 0,
            "detected_qty": detected_qty,
            "expected_total_kg": round(m_net * detected_qty, 2) if detected_qty > 0 else m_net,
            "is_pack": detected_qty > 1
        }
        
        details["detected_volume"] = details["volumetric_info"]["detected_total_kg"]
        details["detected_qty"] = detected_qty
        
        if master_product.get("list_price"):
            actual_price = float(listing.get("price", 0))
            # Calculate Price per Unit (Standardized)
            unit_price = actual_price / detected_qty if detected_qty > 0 else actual_price
            min_price = float(master_product["list_price"])
            
            # Always include unit price for UI clarity in packs
            details["unit_price_info"] = {
                "unit_price": round(unit_price, 2),
                "detected_qty": detected_qty,
                "is_pack": detected_qty > 1
            }

            # If the quantity doesn't match the master SKU, note it
            if detected_qty != m_units:
                details["non_standard_qty"] = {
                    "listing_qty": detected_qty,
                    "master_qty": m_units,
                    "unit_price_calculated": round(unit_price, 2)
                }
                # For frontend compatibility
                details["combo_mismatch"] = {
                    "listing": detected_qty,
                    "master": m_units
                }

            if unit_price < min_price:
                is_price_ok = False
                score += 100 # Direct 100 for price breaking
                details["low_price"] = {
                    "min_allowed": min_price, 
                    "actual_unit_price": round(unit_price, 2),
                    "total_price": actual_price,
                    "diff": round(min_price - unit_price, 2)
                }

        # Rule D: Volumetric Match result (calculated above)
        if not vol_match:
            score += 100 # Direct 100 for format fraud
            expected_total_kg = m_net * detected_qty if detected_qty > 0 else m_net
            details["volumetric_mismatch"] = {
                "expected_total_kg": round(expected_total_kg, 2),
                "unit_master_kg": m_net,
                "detected_qty": detected_qty,
                "detected_in_listing": detected_kg if detected_kg > 0 else (listing_attrs.get("net_content") or "unmatched")
            }

        # Rule E: Restricted SKU
        if not master_product.get("is_publishable", True):
            is_publishable_ok = False
            score += 100 # Direct 100 for restricted SKU
            details["restricted_sku_violation"] = True

        # Rule F: Trust Signal - Official Store
        is_official = listing.get("is_official_store", False)
        if is_official:
            m_price = float(master_product.get("list_price") or 0)
            l_price = float(listing.get("price") or 0)
            # If it's an official store and price isn't ridiculously low (e.g., >80% of list), trust it
            if m_price > 0 and l_price >= (m_price * 0.8):
                details["trust_signal"] = "Verified Official Store"
                score = 0 # Force 0 for official stores with sane pricing
        
        # Add Seller Reputation to details for context
        reputation = listing.get("seller_reputation", {})
        if reputation:
            details["seller_reputation"] = {
                "level": reputation.get("level"),
                "power_seller": reputation.get("power_seller")
            }

        # Ensure score stays in range
        final_score = min(score, 100)
        
        return {
            "master_product_id": master_product["id"],
            "match_level": match_level,
            "fraud_score": final_score,
            "violation_details": details,
            "is_price_ok": is_price_ok,
            "is_brand_correct": is_brand_correct,
            "is_publishable_ok": is_publishable_ok,
            "risk_level": self.get_risk_level(final_score)
        }

    def get_risk_level(self, score):
        if score >= 60: return "Alto"
        if score >= 30: return "Medio"
        return "Bajo"

    def map_violation_to_bpp_reason(self, audit_details):
        """
        Maps internal audit violation flags to MercadoLibre BPP Reason IDs.
        703: Price significantly lower than suggested.
        704: Misleading information about quantity/volume.
        """
        if audit_details.get("low_price"):
            return "703", "Violación de política de precios (PVP)"
        if audit_details.get("volumetric_mismatch"):
            return "704", "Inconsistencia en contenido neto / multipack detectado"
        if audit_details.get("restricted_sku_violation"):
            return "701", "Producto de venta prohibida/restringida"
            
        return None, None
