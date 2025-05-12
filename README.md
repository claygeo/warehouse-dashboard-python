# Warehouse Dashboard (Python)

A Python-based warehouse inventory management dashboard built with Tkinter and Supabase integration. Developed as a prototype to demonstrate inventory management, barcode scanning, cycle counting, and label generation for a warehouse (potentially Curaleaf’s operations), it was later adapted into a JavaScript-based version with a frontend and backend. This suite includes applications for generating barcode labels, scanning items, performing cycle counts, and setting up the database.

## Features

- Generate Labels: Create PDF barcode labels (Code128) from manual input or components.csv, with customizable label sizes (e.g., 4x1.5 inches, 12 labels per sheet).
- Cycle Count Dashboard: Admin (PIN-protected) and user modes for scanning items, comparing quantities with Supabase records, and updating quantities (admin only).
- Inventory Scanner: Scan barcodes (component IDs) to view item details, adjust quantities, and update locations (e.g., Warehouse, Assembly).
- Supabase Integration: Store and manage component data (ID, barcode, description, quantity, location) in a Supabase database.
- Database Setup: Import components from components.csv into Supabase using a setup utility.

## Prerequisites

Python 3.8 or higher
Supabase account with a components table (see Setup for SQL)
Python packages: tkinter, pandas, supabase, python-barcode, pillow, reportlab, configparser
components.csv file with component data (ID, Description)

## Setup

1. Clone the Repository:
git clone https://github.com/claygeo/warehouse-dashboard-python.git

2. Navigate to Project Directory: cd warehouse-dashboard-python

2. Install Python Packages:
pip install pandas supabase python-barcode pillow reportlab
Note: tkinter and configparser are included with Python.

3. Set Up Supabase:
- Create a Supabase project and obtain the URL and anon key.
- Create the components table using the following SQL:CREATE TABLE components (
    id TEXT PRIMARY KEY,
    barcode TEXT UNIQUE,
    description TEXT,
    quantity INTEGER DEFAULT 0,
    location TEXT DEFAULT 'Warehouse'
);

- Update config.ini with your Supabase credentials:
[SUPABASE]
URL = your_supabase_url
KEY = your_supabase_anon_key

4. Prepare Components Data:
- Ensure components.csv is in the project root with columns ID and Description.

5. Import Components:
python supabase_setup.py

Follow prompts to import components.csv into Supabase.

6. Run Applications:
- Main dashboard: python inventory_manager.py
- Barcode scanner: python inventory_scanner.py
- Cycle count dashboard: python cycle_count_dashboard.py
- Generate labels: python generate_labels.py

Notes

- This Python suite was a prototype to showcase warehouse inventory management to managers, later replaced by a JavaScript-based version (e.g., warehouse-inventory-manager).
- The components.csv file contains Curaleaf-specific data; permission was granted.
- The default admin PIN for cycle counts is 0000 (modify in cycle_count_dashboard.py if needed).
- Generated PDF labels are saved with timestamps (e.g., barcode_labels_20250507.pdf).


