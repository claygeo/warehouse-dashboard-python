import pandas as pd
from barcode import Code128  # Changed from UPCA to Code128
from barcode.writer import ImageWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
from datetime import datetime

# Load data from CSV file with UTF-8 encoding
df = pd.read_csv("components.csv", encoding='utf-8')
print(f"Loaded {len(df)} rows from components.csv")

# Function to generate a Code 128 barcode with the component ID
def generate_barcode(id_str):
    # Use the component ID directly as the barcode value
    barcode_value = id_str
    
    # Debug info
    print(f"ID: {id_str}, Barcode: {barcode_value}")
    
    # Create Code 128 barcode
    barcode = Code128(barcode_value, writer=ImageWriter())
    return barcode

# Create a PDF with labels
def create_labels(df, output_pdf="barcode_labels.pdf"):
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter  # 8.5 x 11 inches (612 x 792 points)
    label_width, label_height = 4 * 72, 1.5 * 72  # 4" x 1.5" in points (288 x 108 points)
    labels_per_row, rows_per_page = 2, 6  # 2 columns, 6 rows per page (12 labels per sheet)
    x_offset, y_offset = 0.25 * 72, 1 * 72  # Margins: 0.25" on sides, 1" on top/bottom

    for index, row in df.iterrows():
        id_str = row["ID"]
        page_num = index // (labels_per_row * rows_per_page)
        label_num = index % (labels_per_row * rows_per_page)
        row_num = label_num // labels_per_row
        col_num = label_num % labels_per_row

        if label_num == 0 and index != 0:
            c.showPage()  # New page

        # Calculate position of the label
        x = x_offset + col_num * label_width
        y = height - y_offset - (row_num + 1) * label_height

        # Generate barcode
        barcode = generate_barcode(id_str)
        barcode_file = f"temp_{id_str}"
        barcode.save(barcode_file)  # Saves as PNG
        barcode_path = f"{barcode_file}.png"

        # Draw the component abbreviation (ID) at the top of the label
        c.setFont("Helvetica", 10)
        c.drawString(x + 5, y + label_height - 20, id_str)  # Position at the top

        # Draw barcode below the abbreviation
        barcode_height = 60  # Height of the barcode image in points
        barcode_y = y + label_height - 30 - barcode_height  # Position below the text
        c.drawImage(barcode_path, x + 5, barcode_y, width=label_width - 10, height=barcode_height)

        # Clean up temp file
        os.remove(barcode_path)

    c.save()
    print(f"Labels saved to {output_pdf}")

# Generate the labels
create_labels(df, f"barcode_labels_{datetime.now().strftime('%Y%m%d')}.pdf")