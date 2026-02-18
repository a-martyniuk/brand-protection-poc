import sys
import os
from datetime import datetime

# Add the project root to the path so we can import logic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.supabase_handler import SupabaseHandler
import main
import asyncio

def reset_and_run():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] starting database reset...")
    db = SupabaseHandler()
    
    if db.clear_all_data():
        print(f"[{datetime.now().strftime('%H:%M:%S')}] database cleared. starting fresh pipeline...")
        
        # We manually trigger the main pipeline
        try:
            asyncio.run(main.run_pipeline())
            print(f"[{datetime.now().strftime('%H:%M:%S')}] fresh pipeline execution complete.")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] error during pipeline execution: {e}")
    else:
        print("Aborting pipeline run due to database reset failure.")

if __name__ == "__main__":
    reset_and_run()
