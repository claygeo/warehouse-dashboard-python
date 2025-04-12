import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from tkinter.font import Font
import threading
import time
from datetime import datetime
import configparser
import sys
import os
import pandas as pd
from supabase import create_client
from barcode import Code128
from barcode.writer import ImageWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Configuration handling
def load_config():
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    if not os.path.exists(config_file):
        config['SUPABASE'] = {
            'URL': 'https://afryyzueaapvlnibdcks.supabase.co',
            'KEY': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFmcnl5enVlYWFwdmxuaWJkY2tzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM2NDM4MDksImV4cCI6MjA1OTIxOTgwOX0._D6NLfM5-rYnkIab9J8dGFde6C8uDvJz0S3_gGadn2o'
        }
        with open(config_file, 'w') as f:
            config.write(f)
        messagebox.showwarning("Configuration Required", f"Please edit the {config_file} file with your Supabase credentials.")
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

# Main Application Class
class InventoryManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Manager")
        self.root.geometry("1000x700")
        self.root.configure(bg="#f0f0f0")

        # Style configuration
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0', font=('Arial', 12))
        self.style.configure('TButton', font=('Arial', 12))
        self.style.configure('TNotebook', background='#f0f0f0')

        # Data storage (initialize before tabs)
        self.components_df = None
        self.scanned_items = {}
        self.all_items = {}
        self.load_all_items()  # Load items before setting up tabs

        # Notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tabs
        self.generate_tab = ttk.Frame(self.notebook)
        self.count_tab = ttk.Frame(self.notebook)
        self.print_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.generate_tab, text="Generate Labels")
        self.notebook.add(self.count_tab, text="Count Items")
        self.notebook.add(self.print_tab, text="Print Settings")

        # Initialize tab content
        self.setup_generate_tab()
        self.setup_count_tab()
        self.setup_print_tab()

        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.check_connection()

    def check_connection(self):
        def perform_check():
            try:
                supabase.table('components').select('*').limit(1).execute()
                self.status_var.set(f"Connected to database. {datetime.now().strftime('%H:%M:%S')}")
            except Exception as e:
                self.status_var.set(f"Error connecting to database: {str(e)}")
        threading.Thread(target=perform_check).start()

    def load_all_items(self):
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

    # Generate Labels Tab
    def setup_generate_tab(self):
        self.gen_frame = ttk.Frame(self.generate_tab, padding=20)
        self.gen_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_font = Font(family="Arial", size=18, weight="bold")
        ttk.Label(self.gen_frame, text="Generate Barcode Labels", font=title_font).pack(pady=10)

        # Manual Entry
        ttk.Label(self.gen_frame, text="Manual Entry (ID,Description - one per line):").pack(pady=(10, 0))
        self.manual_entry = tk.Text(self.gen_frame, height=5, width=50, font=('Arial', 12))
        self.manual_entry.pack(pady=5)

        # CSV Upload
        ttk.Label(self.gen_frame, text="Or Upload CSV File:").pack(pady=(10, 0))
        ttk.Button(self.gen_frame, text="Browse", command=self.upload_csv).pack(pady=5)

        # Generate Button
        ttk.Button(self.gen_frame, text="Generate Labels & Sync", command=self.generate_and_sync).pack(pady=20)

        # Progress
        self.gen_progress_var = tk.StringVar(value="Ready")
        ttk.Label(self.gen_frame, textvariable=self.gen_progress_var).pack(pady=5)

    def upload_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            try:
                self.components_df = pd.read_csv(file_path, encoding='utf-8')
                self.gen_progress_var.set(f"Loaded {len(self.components_df)} rows from {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load CSV: {e}")
                self.gen_progress_var.set("Error loading CSV")

    def generate_and_sync(self):
        # Process manual entry or CSV
        if self.components_df is None:
            manual_text = self.manual_entry.get("1.0", tk.END).strip()
            if manual_text:
                lines = manual_text.split('\n')
                data = []
                for line in lines:
                    if ',' in line:
                        id_str, desc = line.split(',', 1)
                        data.append({'ID': id_str.strip(), 'Description': desc.strip()})
                if data:
                    self.components_df = pd.DataFrame(data)
                else:
                    messagebox.showwarning("Input Error", "Please enter valid ID,Description pairs or upload a CSV")
                    return
            else:
                messagebox.showwarning("Input Error", "Please enter data manually or upload a CSV")
                return

        # Sync with Supabase
        self.gen_progress_var.set("Syncing with Supabase...")
        self.root.update_idletasks()
        success = self.import_components(self.components_df)
        if success:
            self.gen_progress_var.set("Generating labels...")
            self.root.update_idletasks()
            output_pdf = f"barcode_labels_{datetime.now().strftime('%Y%m%d')}.pdf"
            self.create_labels(self.components_df, output_pdf)
            self.gen_progress_var.set(f"Labels generated: {output_pdf}")
            self.components_df = None  # Reset after processing
            self.manual_entry.delete("1.0", tk.END)
            self.load_all_items()  # Refresh items list
        else:
            self.gen_progress_var.set("Failed to sync with Supabase")

    def import_components(self, df):
        try:
            barcodes = {}
            duplicate_count = 0
            count = 0
            for index, row in df.iterrows():
                id_str = row["ID"]
                desc = row["Description"]
                barcode = id_str

                if barcode in barcodes:
                    print(f"WARNING: Duplicate barcode {barcode} for {id_str} and {barcodes[barcode]}")
                    duplicate_count += 1
                    continue

                barcodes[barcode] = id_str
                data = {
                    "id": id_str,
                    "barcode": barcode,
                    "description": desc,
                    "quantity": 0,
                    "location": "Warehouse"
                }
                result = supabase.table('components').upsert(data).execute()
                count += 1
                if count % 10 == 0:
                    print(f"Processed {count} records...")

            print(f"Successfully imported {count} components to Supabase")
            if duplicate_count > 0:
                print(f"WARNING: Found {duplicate_count} duplicate barcodes (skipped)")
            return True
        except Exception as e:
            print(f"Error importing components: {e}")
            return False

    def generate_barcode(self, id_str):
        barcode_value = id_str
        barcode = Code128(barcode_value, writer=ImageWriter())
        return barcode

    def create_labels(self, df, output_pdf):
        c = canvas.Canvas(output_pdf, pagesize=letter)
        width, height = letter
        label_width, label_height = 4 * 72, 1.5 * 72
        labels_per_row, rows_per_page = 2, 6
        x_offset, y_offset = 0.25 * 72, 1 * 72

        for index, row in df.iterrows():
            id_str = row["ID"]
            page_num = index // (labels_per_row * rows_per_page)
            label_num = index % (labels_per_row * rows_per_page)
            row_num = label_num // labels_per_row
            col_num = label_num % labels_per_row

            if label_num == 0 and index != 0:
                c.showPage()

            x = x_offset + col_num * label_width
            y = height - y_offset - (row_num + 1) * label_height

            barcode = self.generate_barcode(id_str)
            barcode_file = f"temp_{id_str}"
            barcode.save(barcode_file)
            barcode_path = f"{barcode_file}.png"

            c.setFont("Helvetica", 10)
            c.drawString(x + 5, y + label_height - 20, id_str)
            barcode_height = 60
            barcode_y = y + label_height - 30 - barcode_height
            c.drawImage(barcode_path, x + 5, barcode_y, width=label_width - 10, height=barcode_height)
            os.remove(barcode_path)

        c.save()
        print(f"Labels saved to {output_pdf}")

    # Count Items Tab
    def setup_count_tab(self):
        self.count_frame = ttk.Frame(self.count_tab, padding=20)
        self.count_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_font = Font(family="Arial", size=18, weight="bold")
        self.count_title = tk.Label(self.count_frame, text="Cycle Count Dashboard", font=title_font, bg="#f0f0f0")
        self.count_title.pack(pady=10)

        # Mode selection
        ttk.Button(self.count_frame, text="Start New Session", command=self.start_new_session).pack(pady=5)
        ttk.Button(self.count_frame, text="Admin Count", command=self.show_admin_pin_screen).pack(pady=5)
        ttk.Button(self.count_frame, text="User Count", command=lambda: self.show_count_screen("user")).pack(pady=5)

    def start_new_session(self):
        self.scanned_items.clear()
        self.status_var.set("New scan session started.")
        messagebox.showinfo("Session Started", "New scan session has begun.")

    def show_admin_pin_screen(self):
        for widget in self.count_frame.winfo_children():
            widget.destroy()

        title_font = Font(family="Arial", size=18, weight="bold")
        ttk.Label(self.count_frame, text="Admin Count PIN", font=title_font).pack(pady=20)
        ttk.Label(self.count_frame, text="Enter PIN:").pack(pady=(20, 5))
        self.pin_var = tk.StringVar()
        self.pin_entry = ttk.Entry(self.count_frame, textvariable=self.pin_var, width=20, font=('Arial', 14), show="*")
        self.pin_entry.pack(pady=5)
        self.pin_entry.bind('<Return>', self.validate_admin_pin)
        self.pin_entry.focus()
        ttk.Button(self.count_frame, text="Submit", command=self.validate_admin_pin).pack(pady=20)

    def validate_admin_pin(self, event=None):
        if self.pin_var.get().strip() == "0000":
            self.show_count_screen("admin")
        else:
            messagebox.showerror("Invalid PIN", "Incorrect PIN.")
            self.pin_var.set("")
            self.setup_count_tab()

    def show_count_screen(self, mode):
        self.mode = mode
        for widget in self.count_frame.winfo_children():
            widget.destroy()

        title_font = Font(family="Arial", size=18, weight="bold")
        ttk.Label(self.count_frame, text=f"{mode.capitalize()} Cycle Count", font=title_font).pack(pady=10)
        ttk.Label(self.count_frame, text="Scan Barcode:").pack(pady=(20, 5))
        self.barcode_var = tk.StringVar()
        self.barcode_entry = ttk.Entry(self.count_frame, textvariable=self.barcode_var, width=30, font=('Arial', 14))
        self.barcode_entry.pack(pady=5)
        self.barcode_entry.bind('<Return>', self.lookup_barcode)
        self.barcode_entry.focus()
        ttk.Button(self.count_frame, text="Look Up Item", command=self.lookup_barcode).pack(pady=10)

        self.result_frame = ttk.Frame(self.count_frame, padding=10)
        self.result_frame.pack(fill=tk.BOTH, expand=True, pady=20)

        self.id_var = tk.StringVar()
        self.desc_var = tk.StringVar()
        self.supabase_qty_var = tk.StringVar()
        self.user_qty_var = tk.StringVar()
        self.match_var = tk.StringVar()

        info_frame = ttk.Frame(self.result_frame)
        info_frame.pack(fill=tk.X, expand=True, pady=10)
        left_frame = ttk.Frame(info_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_frame = ttk.Frame(info_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ttk.Label(left_frame, text="Item ID:").pack(anchor=tk.W, pady=5)
        if mode == "admin":
            ttk.Label(left_frame, text="Description:").pack(anchor=tk.W, pady=5)
            ttk.Label(left_frame, text="Supabase Quantity:").pack(anchor=tk.W, pady=5)
        ttk.Label(left_frame, text="Your Count:").pack(anchor=tk.W, pady=5)
        ttk.Label(left_frame, text="Match Status:").pack(anchor=tk.W, pady=5)

        ttk.Label(right_frame, textvariable=self.id_var).pack(anchor=tk.W, pady=5)
        if mode == "admin":
            ttk.Label(right_frame, textvariable=self.desc_var).pack(anchor=tk.W, pady=5)
            ttk.Label(right_frame, textvariable=self.supabase_qty_var).pack(anchor=tk.W, pady=5)
        self.user_qty_entry = ttk.Entry(right_frame, textvariable=self.user_qty_var, width=10)
        self.user_qty_entry.pack(anchor=tk.W, pady=5)
        self.user_qty_entry.bind('<Return>', self.compare_quantities)
        self.match_label = ttk.Label(right_frame, textvariable=self.match_var)
        self.match_label.pack(anchor=tk.W, pady=5)

        buttons_frame = ttk.Frame(self.result_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        ttk.Button(buttons_frame, text="Compare", command=self.compare_quantities).pack(side=tk.LEFT, padx=5)
        if mode == "admin":
            ttk.Button(buttons_frame, text="Update Quantity", command=self.update_quantity).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="View Session Status", command=self.show_session_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Back", command=self.setup_count_tab).pack(side=tk.LEFT, padx=5)

        self.clear_display()
        self.status_var.set(f"{mode.capitalize()} mode active. Scan a barcode to begin.")

    def clear_display(self):
        self.id_var.set("")
        self.desc_var.set("")
        self.supabase_qty_var.set("")
        self.user_qty_var.set("")
        self.match_var.set("")
        self.match_label.configure(background="#f0f0f0")
        self.current_item = None
        self.barcode_var.set("")
        self.barcode_entry.focus()

    def lookup_barcode(self, event=None):
        barcode = self.barcode_var.get().strip()
        if not barcode:
            messagebox.showwarning("Input Error", "Please scan a barcode")
            return

        self.status_var.set(f"Looking up barcode: {barcode}...")
        self.root.update_idletasks()

        def perform_lookup():
            try:
                result = supabase.table('components').select('*').eq('barcode', barcode).execute()
                if result.data and len(result.data) > 0:
                    item = result.data[0]
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
        self.current_item = item
        self.id_var.set(item['id'])
        if self.mode == "admin":
            self.desc_var.set(item['description'])
            self.supabase_qty_var.set(str(item['quantity']))
        self.user_qty_var.set("")
        self.match_var.set("")
        self.match_label.configure(background="#f0f0f0")
        self.status_var.set(f"Item found: {item['id']}. Enter your count.")
        self.user_qty_entry.focus()

    def handle_not_found(self, barcode):
        self.clear_display()
        self.status_var.set(f"No item found with barcode: {barcode}")
        messagebox.showinfo("Not Found", f"No item found with barcode: {barcode}")

    def handle_error(self, error_msg):
        self.status_var.set(f"Error: {error_msg}")
        messagebox.showerror("Database Error", f"An error occurred: {error_msg}")
        self.clear_display()

    def compare_quantities(self, event=None):
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
                self.status_var.set(f"Mismatch: Supabase has {supabase_qty}, you counted {user_qty}")

            barcode = self.current_item['barcode']
            if barcode in self.scanned_items:
                self.scanned_items[barcode]['user_qty'] = user_qty
            self.root.after(3000, self.clear_display)

        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid number")
            self.user_qty_var.set("")
            self.user_qty_entry.focus()

    def update_quantity(self):
        if self.mode != "admin" or not self.current_item:
            return

        try:
            new_qty = int(self.user_qty_var.get().strip())
            if new_qty < 0:
                messagebox.showwarning("Invalid Quantity", "Quantity cannot be negative")
                return

            supabase.table('components').update({"quantity": new_qty}).eq('barcode', self.current_item['barcode']).execute()
            self.supabase_qty_var.set(str(new_qty))
            self.current_item['quantity'] = new_qty
            self.compare_quantities()

            barcode = self.current_item['barcode']
            if barcode in self.scanned_items:
                self.scanned_items[barcode]['user_qty'] = new_qty
                self.scanned_items[barcode]['supabase_qty'] = new_qty
            self.root.after(3000, self.clear_display)

        except Exception as e:
            self.status_var.set(f"Error updating quantity: {str(e)}")
            messagebox.showerror("Update Error", f"Failed to update quantity: {str(e)}")

    def show_session_status(self):
        status_window = tk.Toplevel(self.root)
        status_window.title("Session Status")
        status_window.geometry("800x600")
        status_window.configure(bg="#f0f0f0")

        ttk.Label(status_window, text="Scanned Items:", font=('Arial', 12, 'bold')).pack(pady=5)
        scanned_frame = ttk.Frame(status_window)
        scanned_frame.pack(fill=tk.BOTH, expand=True, pady=5)

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

        scrollbar = ttk.Scrollbar(scanned_frame, orient="vertical", command=scanned_tree.yview)
        scanned_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scanned_tree.pack(fill=tk.BOTH, expand=True)

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

        ttk.Label(status_window, text="Unscanned Items:", font=('Arial', 12, 'bold')).pack(pady=5)
        unscanned_frame = ttk.Frame(status_window)
        unscanned_frame.pack(fill=tk.BOTH, expand=True, pady=5)

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

        scrollbar = ttk.Scrollbar(unscanned_frame, orient="vertical", command=unscanned_tree.yview)
        unscanned_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        unscanned_tree.pack(fill=tk.BOTH, expand=True)

        unscanned_items = [barcode for barcode in self.all_items.keys() if barcode not in self.scanned_items]
        for barcode in unscanned_items:
            item = self.all_items[barcode]
            if self.mode == "admin":
                unscanned_tree.insert("", tk.END, values=(item['id'], item['description']))
            else:
                unscanned_tree.insert("", tk.END, values=(item['id'],))

        ttk.Button(status_window, text="Close", command=status_window.destroy).pack(pady=10)

    # Print Settings Tab
    def setup_print_tab(self):
        self.print_frame = ttk.Frame(self.print_tab, padding=20)
        self.print_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_font = Font(family="Arial", size=18, weight="bold")
        ttk.Label(self.print_frame, text="Print Settings", font=title_font).pack(pady=10)

        # Component Selection
        ttk.Label(self.print_frame, text="Select Components to Print:").pack(pady=(10, 5))
        self.print_listbox = tk.Listbox(self.print_frame, height=10, selectmode=tk.MULTIPLE)
        self.print_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.update_print_listbox()

        # Print Options
        self.include_id_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.print_frame, text="Include ID on Label", variable=self.include_id_var).pack(pady=5)

        self.label_size_var = tk.StringVar(value="4x1.5")
        ttk.Label(self.print_frame, text="Label Size (inches):").pack(pady=(10, 0))
        ttk.Combobox(self.print_frame, textvariable=self.label_size_var, values=["4x1.5", "3x1", "2x1"]).pack(pady=5)

        # Print Button
        ttk.Button(self.print_frame, text="Print Selected Labels", command=self.print_selected_labels).pack(pady=20)

    def update_print_listbox(self):
        self.print_listbox.delete(0, tk.END)
        for barcode, item in self.all_items.items():
            self.print_listbox.insert(tk.END, f"{item['id']} - {item['description']}")

    def print_selected_labels(self):
        selected_indices = self.print_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Selection Error", "Please select at least one component to print")
            return

        selected_items = []
        for idx in selected_indices:
            item_text = self.print_listbox.get(idx)
            id_str = item_text.split(" - ")[0]
            desc = item_text.split(" - ")[1]
            selected_items.append({"ID": id_str, "Description": desc})

        df = pd.DataFrame(selected_items)
        label_size = self.label_size_var.get().split("x")
        label_width, label_height = float(label_size[0]) * 72, float(label_size[1]) * 72
        output_pdf = f"selected_labels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        c = canvas.Canvas(output_pdf, pagesize=letter)
        width, height = letter
        labels_per_row = max(1, int((width - 0.5 * 72) // label_width))
        rows_per_page = max(1, int((height - 2 * 72) // label_height))
        x_offset, y_offset = 0.25 * 72, 1 * 72

        for index, row in df.iterrows():
            id_str = row["ID"]
            page_num = index // (labels_per_row * rows_per_page)
            label_num = index % (labels_per_row * rows_per_page)
            row_num = label_num // labels_per_row
            col_num = label_num % labels_per_row

            if label_num == 0 and index != 0:
                c.showPage()

            x = x_offset + col_num * label_width
            y = height - y_offset - (row_num + 1) * label_height

            barcode = self.generate_barcode(id_str)
            barcode_file = f"temp_{id_str}"
            barcode.save(barcode_file)
            barcode_path = f"{barcode_file}.png"

            if self.include_id_var.get():
                c.setFont("Helvetica", 10)
                c.drawString(x + 5, y + label_height - 20, id_str)

            barcode_height = min(60, label_height - 30)
            barcode_y = y + label_height - 30 - barcode_height
            c.drawImage(barcode_path, x + 5, barcode_y, width=label_width - 10, height=barcode_height)
            os.remove(barcode_path)

        c.save()
        self.status_var.set(f"Printed labels to {output_pdf}")
        messagebox.showinfo("Success", f"Labels printed to {output_pdf}")

# Main function
def main():
    root = tk.Tk()
    app = InventoryManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()