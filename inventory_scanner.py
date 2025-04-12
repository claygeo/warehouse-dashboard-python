import pandas as pd
import os
from supabase import create_client
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.font import Font
import threading
import time
from datetime import datetime
import configparser
import sys

# Configuration handling
def load_config():
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    # Check if config file exists
    if not os.path.exists(config_file):
        # Create a new config file with default settings
        config['SUPABASE'] = {
            'URL': 'https://afryyzueaapvlnibdcks.supabase.co',
            'KEY': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFmcnl5enVlYWFwdmxuaWJkY2tzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM2NDM4MDksImV4cCI6MjA1OTIxOTgwOX0._D6NLfM5-rYnkIab9J8dGFde6C8uDvJz0S3_gGadn2o'
        }
        
        with open(config_file, 'w') as f:
            config.write(f)
        
        messagebox.showwarning(
            "Configuration Required", 
            f"Please edit the {config_file} file with your Supabase credentials."
        )
        sys.exit(1)
    
    # Read config
    config.read(config_file)
    return config

# Initialize configuration
config = load_config()
SUPABASE_URL = config['SUPABASE']['URL']
SUPABASE_KEY = config['SUPABASE']['KEY']

# Initialize Supabase client
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Error connecting to Supabase: {e}")
    messagebox.showerror("Connection Error", f"Failed to connect to Supabase: {e}")
    sys.exit(1)

# Barcode scanner UI application
class BarcodeScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Scanner")
        self.root.geometry("800x600")
        self.root.configure(bg="#f0f0f0")
        
        # Configure styles
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0', font=('Arial', 12))
        self.style.configure('TButton', font=('Arial', 12))
        
        # Main frame
        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_font = Font(family="Arial", size=18, weight="bold")
        self.title_label = tk.Label(self.main_frame, text="Inventory Scanner", 
                                   font=title_font, bg="#f0f0f0")
        self.title_label.pack(pady=10)
        
        # Barcode entry
        ttk.Label(self.main_frame, text="Scan or Enter Barcode:").pack(pady=(20, 5))
        
        self.barcode_var = tk.StringVar()
        self.entry = ttk.Entry(self.main_frame, textvariable=self.barcode_var, 
                              width=30, font=('Arial', 14))
        self.entry.pack(pady=5)
        self.entry.bind('<Return>', self.lookup_barcode)
        self.entry.focus()
        
        # Scan button
        self.scan_button = ttk.Button(self.main_frame, text="Look Up Item", 
                                     command=self.lookup_barcode)
        self.scan_button.pack(pady=10)
        
        # Results frame
        self.result_frame = ttk.Frame(self.main_frame, padding=10)
        self.result_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # Item information labels
        self.id_var = tk.StringVar()
        self.desc_var = tk.StringVar()
        self.qty_var = tk.StringVar()
        self.location_var = tk.StringVar()
        
        info_frame = ttk.Frame(self.result_frame)
        info_frame.pack(fill=tk.X, expand=True, pady=10)
        
        # Create two columns
        left_frame = ttk.Frame(info_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_frame = ttk.Frame(info_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Left column - labels
        ttk.Label(left_frame, text="Item ID:").pack(anchor=tk.W, pady=5)
        ttk.Label(left_frame, text="Description:").pack(anchor=tk.W, pady=5)
        ttk.Label(left_frame, text="Quantity:").pack(anchor=tk.W, pady=5)
        ttk.Label(left_frame, text="Location:").pack(anchor=tk.W, pady=5)
        
        # Right column - values
        ttk.Label(right_frame, textvariable=self.id_var).pack(anchor=tk.W, pady=5)
        ttk.Label(right_frame, textvariable=self.desc_var).pack(anchor=tk.W, pady=5)
        ttk.Label(right_frame, textvariable=self.qty_var).pack(anchor=tk.W, pady=5)
        ttk.Label(right_frame, textvariable=self.location_var).pack(anchor=tk.W, pady=5)
        
        # Quantity adjustment frame
        self.qty_frame = ttk.Frame(self.result_frame)
        self.qty_frame.pack(fill=tk.X, pady=20)
        
        ttk.Label(self.qty_frame, text="Adjust Quantity:").pack(side=tk.LEFT, padx=5)
        
        self.qty_change_var = tk.StringVar(value="1")
        qty_spinbox = ttk.Spinbox(self.qty_frame, from_=-100, to=100, 
                                 textvariable=self.qty_change_var, width=5)
        qty_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(self.qty_frame, text="Add", 
                  command=lambda: self.update_quantity(True)).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(self.qty_frame, text="Remove", 
                  command=lambda: self.update_quantity(False)).pack(side=tk.LEFT, padx=5)
        
        # Location update frame
        self.location_frame = ttk.Frame(self.result_frame)
        self.location_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(self.location_frame, text="Update Location:").pack(side=tk.LEFT, padx=5)
        
        self.new_location_var = tk.StringVar()
        locations = ["Warehouse", "Assembly", "Shipping", "Returns", "Inspection"]
        location_dropdown = ttk.Combobox(self.location_frame, textvariable=self.new_location_var, 
                                         values=locations, width=15)
        location_dropdown.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(self.location_frame, text="Update Location", 
                  command=self.update_location).pack(side=tk.LEFT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                                   relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Initialize
        self.current_barcode = None
        self.clear_display()
        self.check_connection()
    
    def check_connection(self):
        def perform_check():
            try:
                # Try to fetch one record to test connection
                result = supabase.table('components').select('*').limit(1).execute()
                self.status_var.set(f"Connected to database. Ready to scan. {datetime.now().strftime('%H:%M:%S')}")
            except Exception as e:
                self.status_var.set(f"Error connecting to database: {str(e)}")
        
        # Run this in a thread to avoid blocking UI
        threading.Thread(target=perform_check).start()
    
    def clear_display(self):
        self.id_var.set("")
        self.desc_var.set("")
        self.qty_var.set("")
        self.location_var.set("")
        self.current_barcode = None
    
    def lookup_barcode(self, event=None):
        barcode = self.barcode_var.get().strip()
        
        if not barcode:
            messagebox.showwarning("Input Error", "Please enter a barcode")
            return
        
        # The scanned barcode is now the component ID (e.g., "BOT050")
        lookup_barcode = barcode

        self.status_var.set(f"Looking up barcode: {lookup_barcode}...")
        self.root.update_idletasks()
        
        def perform_lookup():
            try:
                # Query Supabase for the barcode (which is now the component ID)
                # Try matching by barcode first
                result = supabase.table('components').select('*').eq('barcode', lookup_barcode).execute()
                
                # If no match, try matching by ID (for manual entry of the ID)
                if not result.data or len(result.data) == 0:
                    result = supabase.table('components').select('*').eq('id', lookup_barcode).execute()
                
                # Check if we got a match
                if result.data and len(result.data) > 0:
                    item = result.data[0]
                    
                    # Update the UI (from the main thread)
                    self.root.after(0, lambda: self.display_item(item))
                else:
                    # No match found
                    self.root.after(0, lambda: self.handle_not_found(lookup_barcode))
            except Exception as e:
                # Handle error
                self.root.after(0, lambda: self.handle_error(str(e)))
        
        # Run the lookup in a separate thread to keep UI responsive
        threading.Thread(target=perform_lookup).start()
    
    def display_item(self, item):
        self.current_barcode = item['barcode']
        self.id_var.set(item['id'])
        self.desc_var.set(item['description'])
        self.qty_var.set(str(item['quantity']))
        self.location_var.set(item['location'])
        
        # Update the barcode entry field to show the item ID
        self.barcode_var.set(item['id'])
        
        self.status_var.set(f"Item found: {item['id']} - {item['description']}")
        
        # Keep focus on the entry field for the next scan
        self.entry.focus()
    
    def handle_not_found(self, barcode):
        self.clear_display()
        self.status_var.set(f"No item found with barcode: {barcode}")
        messagebox.showinfo("Not Found", f"No item found with barcode: {barcode}")
        
        # Clear the entry for next scan
        self.barcode_var.set("")
        self.entry.focus()
    
    def handle_error(self, error_msg):
        self.status_var.set(f"Error: {error_msg}")
        messagebox.showerror("Database Error", f"An error occurred: {error_msg}")
        
        # Clear the entry for next scan
        self.barcode_var.set("")
        self.entry.focus()
    
    def update_quantity(self, is_add):
        if not self.current_barcode:
            messagebox.showwarning("No Item", "Please scan an item first")
            return
        
        try:
            # Get current quantity from display
            current_qty = int(self.qty_var.get())
            change_qty = int(self.qty_change_var.get())
            
            if not is_add:
                change_qty = -change_qty
            
            new_qty = current_qty + change_qty
            
            # Don't allow negative quantities
            if new_qty < 0:
                messagebox.showwarning("Invalid Quantity", "Quantity cannot be negative")
                return
            
            # Update in Supabase
            result = supabase.table('components').update(
                {"quantity": new_qty}
            ).eq('barcode', self.current_barcode).execute()
            
            # Update display
            self.qty_var.set(str(new_qty))
            
            action = "added to" if change_qty > 0 else "removed from"
            self.status_var.set(f"{abs(change_qty)} {action} inventory. New quantity: {new_qty}")
            
        except Exception as e:
            self.status_var.set(f"Error updating quantity: {str(e)}")
            messagebox.showerror("Update Error", f"Failed to update quantity: {str(e)}")
    
    def update_location(self):
        if not self.current_barcode:
            messagebox.showwarning("No Item", "Please scan an item first")
            return
        
        new_location = self.new_location_var.get().strip()
        if not new_location:
            messagebox.showwarning("Input Error", "Please select a location")
            return
        
        try:
            # Update in Supabase
            result = supabase.table('components').update(
                {"location": new_location}
            ).eq('barcode', self.current_barcode).execute()
            
            # Update display
            self.location_var.set(new_location)
            self.status_var.set(f"Location updated to: {new_location}")
            
        except Exception as e:
            self.status_var.set(f"Error updating location: {str(e)}")
            messagebox.showerror("Update Error", f"Failed to update location: {str(e)}")

# Main function
def main():
    # Start the UI
    root = tk.Tk()
    app = BarcodeScannerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()