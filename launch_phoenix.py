import phoenix as px
import time
import sys
import os

def launch():
    print("--- PHOENIX MINIMAL LAUNCHER ---")
    
    # Set environment variables for Phoenix to be picked up
    os.environ["PHOENIX_PORT"] = os.getenv("PORT", "6006")
    os.environ["PHOENIX_HOST"] = os.getenv("PHOENIX_HOST", "0.0.0.0") # Listen on all interfaces
    
    # Use workspace dir for data, prioritizing environment variables
    data_dir = os.getenv("PHOENIX_WORKING_DIR", os.path.abspath("phoenix_data"))
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    os.environ["PHOENIX_WORKING_DIR"] = data_dir
    os.environ["PHOENIX_DATA_DIR"] = os.getenv("PHOENIX_DATA_DIR", data_dir)

    try:
        print(f"Launching Phoenix (port 6006, data_dir: {data_dir})...")
        session = px.launch_app()
        print("\n" + "="*40)
        print(f"SUCCESS: Phoenix is running at {session.url}")
        print("="*40)
        print("\nKEEP THIS TERMINAL OPEN.")
        
        while True:
            time.sleep(10)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    launch()
