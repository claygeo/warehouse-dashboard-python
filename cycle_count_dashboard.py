import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.font import Font
import threading
import time
from datetime import datetime
import configparser
import sys
import os
from supabase import create_client

# Configuration handling
def load_config():
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    if not os.path.exists(config_file):
        config['SUPABASE'] = {
            'URL': '',
            'KEY': ''
        }
        
        with open(config_file, 'w') as f:
            config.write(f)
        
        messagebox.showwarning(
            "Configuration Required", 
            f"Please edit the {config_file} file with your Supabase credentials."
        )
        sys.exit(1)
    
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

# Cycle Count Dashboard Application
class CycleCountDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Cycle Count Dashboard")
        self.root.geometry("800x600")
        self.root.configure(bg="#f0f0f0")
        
        # Configure styles
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0', font=('Arial', 12))
        self.style.configure('TButton', font=('Arial', 12))
        
        # Default PIN
        self.default_pin = "0000"
        
        # Current mode (admin or user)
        self.mode = None
        
        # Current item being counted
        self.current_item = None
        
        # Session tracking
        self.scanned_items = {}  # Dictionary to store scanned items: {barcode: {details}}
        self.all_items = {}  # Dictionary of all items: {barcode: {id, description}}
        
        # Load all items at startup
        self.load_all_items()
        
        # Show the main menu directly
        self.show_main_menu()
    
    def load_all_items(self):
        """Load all items from Supabase to track unscanned items."""
        try:
            result = supabase.table('components').select('barcode', 'id', 'description').execute()
            if result.data:
                self.all_items = {item['barcode']: {'id': item['id'], 'description': item['description']} for item in result.data}
                print(f"Loaded {len(self.all_items)} items from Supabase")
            else:
                self.all_items = {}
                print("No items found in Supabase")
        except Exception as e:
            print(f"Error loading all items: {e}")
            self.all_items = {}
    
    def show_main_menu(self):
        """Display the main menu with options for Admin Count and User Count."""
        # Clear the window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Main frame
        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_font = Font(family="Arial", size=18, weight="bold")
        self.title_label = tk.Label(self.main_frame, text="Cycle Count Dashboard", 
                                   font=title_font, bg="#f0f0f0")
        self.title_label.pack(pady=20)
        
        # Menu options
        ttk.Button(self.main_frame, text="Start New Scan Session", 
                  command=self.start_new_session).pack(pady=10)
        ttk.Button(self.main_frame, text="Admin Count", 
                  command=self.show_admin_pin_screen).pack(pady=10)
        ttk.Button(self.main_frame, text="User Count", 
                  command=lambda: self.show_count_screen("user")).pack(pady=10)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                                   relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.check_connection()
    
    def check_connection(self):
        """Check the connection to Supabase."""
        def perform_check():
            try:
                result = supabase.table('components').select('*').limit(1).execute()
                self.status_var.set(f"Connected to database. {datetime.now().strftime('%H:%M:%S')}")
            except Exception as e:
                self.status_var.set(f"Error connecting to database: {str(e)}")
        
        threading.Thread(target=perform_check).start()
    
    def start_new_session(self):
        """Start a new scan session by resetting tracked items."""
        self.scanned_items.clear()
        self.status_var.set("New scan session started. Select a mode to begin.")
        messagebox.showinfo("Session Started", "New scan session has begun. Scanned items will be tracked.")
    
    def show_admin_pin_screen(self):
        """Display the PIN entry screen for Admin Count."""
        # Clear the window
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Title
        title_font = Font(family="Arial", size=18, weight="bold")
        self.title_label = tk.Label(self.main_frame, text="Admin Count PIN", 
                                   font=title_font, bg="#f0f0f0")
        self.title_label.pack(pady=20)
        
        # PIN entry
        ttk.Label(self.main_frame, text="Enter PIN:").pack(pady=(20, 5))
        
        self.pin_var = tk.StringVar()
        self.pin_entry = ttk.Entry(self.main_frame, textvariable=self.pin_var, 
                                  width=20, font=('Arial', 14), show="*")
        self.pin_entry.pack(pady=5)
        self.pin_entry.bind('<Return>', self.validate_admin_pin)
        self.pin_entry.focus()
        
        # Login button
        self.login_button = ttk.Button(self.main_frame, text="Submit", 
                                      command=self.validate_admin_pin)
        self.login_button.pack(pady=20)
    
    def validate_admin_pin(self, event=None):
        """Validate the PIN for Admin Count and proceed if correct."""
        entered_pin = self.pin_var.get().strip()
        if entered_pin == self.default_pin:
            self.show_count_screen("admin")
        else:
            messagebox.showerror("Invalid PIN", "Incorrect PIN. Returning to menu.")
            self.pin_var.set("")
            self.show_main_menu()
    
    def show_count_screen(self, mode):
        """Display the cycle count screen for the specified mode (admin or user)."""
        self.mode = mode
        
        # Clear the window
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Title
        title_font = Font(family="Arial", size=18, weight="bold")
        self.title_label = tk.Label(self.main_frame, text=f"{mode.capitalize()} Cycle Count", 
                                   font=title_font, bg="#f0f0f0")
        self.title_label.pack(pady=10)
        
        # Barcode entry
        ttk.Label(self.main_frame, text="Scan Barcode:").pack(pady=(20, 5))
        
        self.barcode_var = tk.StringVar()
        self.barcode_entry = ttk.Entry(self.main_frame, textvariable=self.barcode_var, 
                                      width=30, font=('Arial', 14))
        self.barcode_entry.pack(pady=5)
        self.barcode_entry.bind('<Return>', self.lookup_barcode)
        if mode == "user":
            self.barcode_entry.focus()  # Focus on barcode entry for User mode
        else:
            self.barcode_entry.focus()  # Focus on barcode entry for Admin mode (after PIN)
        
        # Look up button
        self.lookup_button = ttk.Button(self.main_frame, text="Look Up Item", 
                                       command=self.lookup_barcode)
        self.lookup_button.pack(pady=10)
        
        # Results frame
        self.result_frame = ttk.Frame(self.main_frame, padding=10)
        self.result_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # Item information labels
        self.id_var = tk.StringVar()
        self.desc_var = tk.StringVar()
        self.supabase_qty_var = tk.StringVar()
        self.user_qty_var = tk.StringVar()
        self.match_var = tk.StringVar()
        
        # Info frame for displaying item details
        self.info_frame = ttk.Frame(self.result_frame)
        self.info_frame.pack(fill=tk.X, expand=True, pady=10)
        
        # Create two columns
        left_frame = ttk.Frame(self.info_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_frame = ttk.Frame(self.info_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Left column - labels
        ttk.Label(left_frame, text="Item ID:").pack(anchor=tk.W, pady=5)
        if self.mode == "admin":
            ttk.Label(left_frame, text="Description:").pack(anchor=tk.W, pady=5)
            ttk.Label(left_frame, text="Supabase Quantity:").pack(anchor=tk.W, pady=5)
        ttk.Label(left_frame, text="Your Count:").pack(anchor=tk.W, pady=5)
        ttk.Label(left_frame, text="Match Status:").pack(anchor=tk.W, pady=5)
        
        # Right column - values
        ttk.Label(right_frame, textvariable=self.id_var).pack(anchor=tk.W, pady=5)
        if self.mode == "admin":
            ttk.Label(right_frame, textvariable=self.desc_var).pack(anchor=tk.W, pady=5)
            ttk.Label(right_frame, textvariable=self.supabase_qty_var).pack(anchor=tk.W, pady=5)
        self.user_qty_entry = ttk.Entry(right_frame, textvariable=self.user_qty_var, width=10)
        self.user_qty_entry.pack(anchor=tk.W, pady=5)
        self.user_qty_entry.bind('<Return>', self.compare_quantities)
        self.match_label = ttk.Label(right_frame, textvariable=self.match_var)
        self.match_label.pack(anchor=tk.W, pady=5)
        
        # Buttons frame
        self.buttons_frame = ttk.Frame(self.result_frame)
        self.buttons_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(self.buttons_frame, text="Compare", 
                  command=self.compare_quantities).pack(side=tk.LEFT, padx=5)
        if self.mode == "admin":
            ttk.Button(self.buttons_frame, text="Update Quantity", 
                      command=self.update_quantity).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.buttons_frame, text="View Session Status", 
                  command=self.show_session_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.buttons_frame, text="Back to Menu", 
                  command=self.show_main_menu).pack(side=tk.LEFT, padx=5)
        
        # Initialize
        self.clear_display()
        self.status_var.set(f"{mode.capitalize()} mode active. Scan a barcode to begin.")
    
    def clear_display(self):
        """Clear the display fields and prepare for the next scan."""
        self.id_var.set("")
        self.desc_var.set("")
        self.supabase_qty_var.set("")
        self.user_qty_var.set("")
        self.match_var.set("")
        self.match_label.configure(background="#f0f0f0")
        self.current_item = None
        self.barcode_var.set("")
        self.barcode_entry.focus()  # Focus back on barcode entry for the next scan
    
    def lookup_barcode(self, event=None):
        """Look up the scanned barcode in Supabase."""
        barcode = self.barcode_var.get().strip()
        
        if not barcode:
            messagebox.showwarning("Input Error", "Please scan a barcode")
            return
        
        self.status_var.set(f"Looking up barcode: {barcode}...")
        self.root.update_idletasks()
        
        def perform_lookup():
            try:
                # Query Supabase for the barcode (which is the component ID)
                result = supabase.table('components').select('*').eq('barcode', barcode).execute()
                
                # Check if we got a match
                if result.data and len(result.data) > 0:
                    item = result.data[0]
                    # Track the scanned item
                    self.scanned_items[barcode] = {
                        'id': item['id'],
                        'description': item['description'],
                        'supabase_qty': item['quantity'],
                        'user_qty': None
                    }
                    self.root.after(0, lambda: self.display_item(item))
                else:
                    self.root.after(0, lambda: self.handle_not_found(barcode))
            except Exception as e:
                self.root.after(0, lambda: self.handle_error(str(e)))
        
        threading.Thread(target=perform_lookup).start()
    
    def display_item(self, item):
        """Display the item details based on the mode."""
        self.current_item = item
        self.id_var.set(item['id'])
        if self.mode == "admin":
            self.desc_var.set(item['description'])
            self.supabase_qty_var.set(str(item['quantity']))
        self.user_qty_var.set("")
        self.match_var.set("")
        self.match_label.configure(background="#f0f0f0")
        
        self.status_var.set(f"Item found: {item['id']}. Enter your count.")
        self.user_qty_entry.focus()  # Focus on quantity entry after lookup
    
    def handle_not_found(self, barcode):
        """Handle case where the barcode is not found."""
        self.clear_display()
        self.status_var.set(f"No item found with barcode: {barcode}")
        messagebox.showinfo("Not Found", f"No item found with barcode: {barcode}")
        self.barcode_entry.focus()
    
    def handle_error(self, error_msg):
        """Handle errors during lookup."""
        self.status_var.set(f"Error: {error_msg}")
        messagebox.showerror("Database Error", f"An error occurred: {error_msg}")
        self.clear_display()
        self.barcode_entry.focus()
    
    def compare_quantities(self, event=None):
        """Compare the user's counted quantity with the Supabase quantity."""
        if not self.current_item:
            messagebox.showwarning("No Item", "Please scan an item first")
            return
        
        try:
            user_qty = int(self.user_qty_var.get().strip())
            if user_qty < 0:
                messagebox.showwarning("Invalid Quantity", "Quantity cannot be negative")
                return
            
            supabase_qty = int(self.current_item['quantity'])
            
            if user_qty == supabase_qty:
                self.match_var.set("Match")
                self.match_label.configure(background="green")
                self.status_var.set("Quantities match!")
            else:
                self.match_var.set("Mismatch")
                self.match_label.configure(background="red")
                if self.mode == "admin":
                    self.status_var.set(f"Mismatch: Supabase has {supabase_qty}, you counted {user_qty}")
                else:
                    self.status_var.set("Quantities do not match")
            
            # Update tracked item with user quantity
            barcode = self.current_item['barcode']
            if barcode in self.scanned_items:
                self.scanned_items[barcode]['user_qty'] = user_qty
            
            # Clear the display for the next scan after 3 seconds
            self.root.after(15000, self.clear_display)
        
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid number")
            self.user_qty_var.set("")
            self.user_qty_entry.focus()
    
    def update_quantity(self):
        """Update the quantity in Supabase (admin mode only)."""
        if self.mode != "admin":
            return
        
        if not self.current_item:
            messagebox.showwarning("No Item", "Please scan an item first")
            return
        
        try:
            new_qty = int(self.user_qty_var.get().strip())
            if new_qty < 0:
                messagebox.showwarning("Invalid Quantity", "Quantity cannot be negative")
                return
            
            # Update in Supabase
            result = supabase.table('components').update(
                {"quantity": new_qty}
            ).eq('barcode', self.current_item['barcode']).execute()
            
            # Update display
            self.supabase_qty_var.set(str(new_qty))
            self.current_item['quantity'] = new_qty
            self.compare_quantities()  # Re-compare to update the match status
            
            # Update tracked item with new quantity
            barcode = self.current_item['barcode']
            if barcode in self.scanned_items:
                self.scanned_items[barcode]['user_qty'] = new_qty
                self.scanned_items[barcode]['supabase_qty'] = new_qty
            
            # Clear the display for the next scan after 3 seconds
            self.root.after(3000, self.clear_display)
        
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid number")
            self.user_qty_var.set("")
            self.user_qty_entry.focus()
        except Exception as e:
            self.status_var.set(f"Error updating quantity: {str(e)}")
            messagebox.showerror("Update Error", f"Failed to update quantity: {str(e)}")
    
    def show_session_status(self):
        """Display the session status in a new window using Treeview."""
        # Create a new top-level window
        status_window = tk.Toplevel(self.root)
        status_window.title("Session Status")
        status_window.geometry("800x600")
        status_window.configure(bg="#f0f0f0")
        
        # Scanned items section
        ttk.Label(status_window, text="Scanned Items:", font=('Arial', 12, 'bold')).pack(pady=5)
        scanned_frame = ttk.Frame(status_window)
        scanned_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Treeview for scanned items
        if self.mode == "admin":
            columns = ("ID", "Description", "Supabase Qty", "User Qty")
            scanned_tree = ttk.Treeview(scanned_frame, columns=columns, show="headings")
            scanned_tree.heading("ID", text="ID")
            scanned_tree.heading("Description", text="Description")
            scanned_tree.heading("Supabase Qty", text="Supabase Qty")
            scanned_tree.heading("User Qty", text="User Qty")
            scanned_tree.column("ID", width=100)
            scanned_tree.column("Description", width=300)
            scanned_tree.column("Supabase Qty", width=100)
            scanned_tree.column("User Qty", width=100)
        else:
            columns = ("ID",)
            scanned_tree = ttk.Treeview(scanned_frame, columns=columns, show="headings")
            scanned_tree.heading("ID", text="ID")
            scanned_tree.column("ID", width=100)
        
        # Scrollbar for scanned items
        scrollbar = ttk.Scrollbar(scanned_frame, orient="vertical", command=scanned_tree.yview)
        scanned_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scanned_tree.pack(fill=tk.BOTH, expand=True)
        
        # Populate scanned items
        for barcode, details in self.scanned_items.items():
            if self.mode == "admin":
                scanned_tree.insert("", tk.END, values=(
                    details['id'],
                    details['description'],
                    details['supabase_qty'],
                    details['user_qty'] if details['user_qty'] is not None else "N/A"
                ))
            else:
                scanned_tree.insert("", tk.END, values=(details['id'],))
        
        # Unscanned items section
        ttk.Label(status_window, text="Unscanned Items:", font=('Arial', 12, 'bold')).pack(pady=5)
        unscanned_frame = ttk.Frame(status_window)
        unscanned_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Treeview for unscanned items
        if self.mode == "admin":
            columns = ("ID", "Description")
            unscanned_tree = ttk.Treeview(unscanned_frame, columns=columns, show="headings")
            unscanned_tree.heading("ID", text="ID")
            unscanned_tree.heading("Description", text="Description")
            unscanned_tree.column("ID", width=100)
            unscanned_tree.column("Description", width=300)
        else:
            columns = ("ID",)
            unscanned_tree = ttk.Treeview(unscanned_frame, columns=columns, show="headings")
            unscanned_tree.heading("ID", text="ID")
            unscanned_tree.column("ID", width=100)
        
        # Scrollbar for unscanned items
        scrollbar = ttk.Scrollbar(unscanned_frame, orient="vertical", command=unscanned_tree.yview)
        unscanned_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        unscanned_tree.pack(fill=tk.BOTH, expand=True)
        
        # Populate unscanned items
        unscanned_items = [barcode for barcode in self.all_items.keys() if barcode not in self.scanned_items]
        for barcode in unscanned_items:
            item = self.all_items[barcode]
            if self.mode == "admin":
                unscanned_tree.insert("", tk.END, values=(item['id'], item['description']))
            else:
                unscanned_tree.insert("", tk.END, values=(item['id'],))
        
        # Close button
        ttk.Button(status_window, text="Close", command=status_window.destroy).pack(pady=10)

# Main function
def main():
    root = tk.Tk()
    app = CycleCountDashboard(root)
    root.mainloop()

if __name__ == "__main__":
    main()