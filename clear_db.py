from logic.supabase_handler import SupabaseHandler

def main():
    print("Iniciando borrado completo de la base de datos...")
    db = SupabaseHandler()
    success = db.clear_all_data()
    if success:
        print("Base de datos borrada con éxito.")
    else:
        print("Error borrando base de datos.")

if __name__ == "__main__":
    main()
