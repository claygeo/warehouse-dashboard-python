import pandas as pd
import sys
import os
import configparser
from supabase import create_client
from datetime import datetime

def load_config():
    """Load configuration from config.ini file or create it if not exists"""
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    # Check if config file exists
    if not os.path.exists(config_file):
        # Create a new config file with default settings
        config['SUPABASE'] = {
            'URL': '',
            'KEY': 
        }
        
        with open(config_file, 'w') as f:
            config.write(f)
        
        print(f"Please edit the {config_file} file with your Supabase credentials.")
        sys.exit(1)
    
    # Read config
    config.read(config_file)
    return config

def import_components(csv_file, supabase):
    """Import components from CSV file to Supabase"""
    try:
        # Read CSV file
        df = pd.read_csv(csv_file, encoding='utf-8')
        print(f"Loaded {len(df)} rows from {csv_file}")
        
        # Collect all barcodes to check for duplicates
        barcodes = {}
        duplicate_count = 0
        
        # Process each component
        count = 0
        for index, row in df.iterrows():
            id_str = row["ID"]
            desc = row["Description"]
            
            # Use the component ID directly as the barcode
            barcode = id_str
            
            # Check for duplicates (should not happen since IDs are unique)
            if barcode in barcodes:
                print(f"WARNING: Duplicate barcode {barcode} for {id_str} and {barcodes[barcode]}")
                duplicate_count += 1
                continue
            
            barcodes[barcode] = id_str
            
            # Insert into Supabase
            data = {
                "id": id_str,
                "barcode": barcode,  # Store the component ID as the barcode
                "description": desc,
                "quantity": 0,  # Default quantity
                "location": "Warehouse"  # Default location
            }
            
            try:
                # Upsert (insert if not exists, update if exists)
                result = supabase.table('components').upsert(data).execute()
                count += 1
                
                # Print progress every 10 records
                if count % 10 == 0:
                    print(f"Processed {count} records...")
            except Exception as e:
                print(f"Error importing {id_str}: {e}")
                
        print(f"Successfully imported {count} components to Supabase")
        if duplicate_count > 0:
            print(f"WARNING: Found {duplicate_count} duplicate barcodes (these were skipped)")
        return True
    except Exception as e:
        print(f"Error importing components: {e}")
        return False

def check_table_exists(supabase):
    """Check if the components table exists in Supabase"""
    try:
        result = supabase.table('components').select('id').limit(1).execute()
        if hasattr(result, 'data'):
            return True
        return False
    except Exception as e:
        print(f"Error checking table: {e}")
        return False

def main():
    """Main function to set up Supabase database"""
    print("Supabase Setup Utility")
    print("======================")
    
    # Load configuration
    config = load_config()
    SUPABASE_URL = config['SUPABASE']['URL']
    SUPABASE_KEY = config['SUPABASE']['KEY']
    
    # Check for placeholder values
    if SUPABASE_URL == 'YOUR_SUPABASE_URL' or SUPABASE_KEY == 'YOUR_SUPABASE_SERVICE_KEY':
        print("Error: You must update the config.ini file with your actual Supabase credentials.")
        sys.exit(1)
    
    # Initialize Supabase client
    try:
        print("Connecting to Supabase...")
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Connected successfully!")
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
        sys.exit(1)
    
    # Check if table exists
    if check_table_exists(supabase):
        print("The 'components' table already exists in your Supabase project.")
        # Ask if user wants to clear the table before importing
        clear_choice = input("Do you want to clear the table before importing? (y/n): ")
        if clear_choice.lower() == 'y':
            try:
                supabase.table('components').delete().execute()
                print("Table cleared successfully.")
            except Exception as e:
                print(f"Error clearing table: {e}")
                proceed = input("Continue anyway? (y/n): ")
                if proceed.lower() != 'y':
                    sys.exit(0)
    else:
        print("The 'components' table does not exist. Please create it using SQL from the README.md file.")
        proceed = input("Do you want to continue anyway? (y/n): ")
        if proceed.lower() != 'y':
            sys.exit(0)
    
    # Ask if user wants to import components
    csv_file = "components.csv"
    if os.path.exists(csv_file):
        import_choice = input(f"Found {csv_file}. Do you want to import components? (y/n): ")
        if import_choice.lower() == 'y':
            import_components(csv_file, supabase)
    else:
        print(f"Warning: {csv_file} not found. Cannot import components.")
    
    print("\nSetup complete! You can now run inventory_scanner.py")

if __name__ == "__main__":
    main()