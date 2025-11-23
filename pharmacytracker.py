# pharmacy_tracker.py
# Pharmacy Inventory & Expiry Tracker
# Pure Python (sqlite3 + tkinter). No external dependencies.

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import csv
import os

DB_FILE = "pharmacy.db"
DATE_FORMAT = "%Y-%m-%d"  # ISO format YYYY-MM-DD (easy to sort and compare)

# ---------- Database setup ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        category TEXT,
        batch_no TEXT,
        quantity INTEGER NOT NULL,
        price REAL,
        supplier TEXT,
        expiry_date TEXT,           -- stored as YYYY-MM-DD
        created_on TEXT
    )
    """)
    conn.commit()
    return conn

conn = init_db()
cur = conn.cursor()

# ---------- Utility functions ----------
def parse_date(s):
    """Return datetime.date or raise ValueError"""
    return datetime.strptime(s, DATE_FORMAT).date()

def today_str():
    return datetime.now().strftime(DATE_FORMAT)

# ---------- GUI ----------
root = tk.Tk()
root.title("Pharmacy Inventory & Expiry Tracker")
root.geometry("1000x650")
root.configure(bg="#f0f4f8")

# Top title
title = tk.Label(root, text="Pharmacy Inventory & Expiry Tracker", font=("Helvetica", 18, "bold"), bg="#f0f4f8")
title.pack(pady=10)

# --- Input frame (left) ---
left_frame = tk.Frame(root, bg="#f0f4f8")
left_frame.pack(side=tk.LEFT, padx=12, pady=6, fill=tk.Y)

lbl_info = tk.Label(left_frame, text="Add / Update Product", font=("Helvetica", 12, "bold"), bg="#f0f4f8")
lbl_info.grid(row=0, column=0, columnspan=2, pady=(0,8))

# form fields
tk.Label(left_frame, text="Product Name:", bg="#f0f4f8").grid(row=1, column=0, sticky='w', pady=4)
entry_name = tk.Entry(left_frame, width=28)
entry_name.grid(row=1, column=1, pady=4)

tk.Label(left_frame, text="Category:", bg="#f0f4f8").grid(row=2, column=0, sticky='w', pady=4)
entry_cat = tk.Entry(left_frame, width=28)
entry_cat.grid(row=2, column=1, pady=4)

tk.Label(left_frame, text="Batch No:", bg="#f0f4f8").grid(row=3, column=0, sticky='w', pady=4)
entry_batch = tk.Entry(left_frame, width=28)
entry_batch.grid(row=3, column=1, pady=4)

tk.Label(left_frame, text="Quantity:", bg="#f0f4f8").grid(row=4, column=0, sticky='w', pady=4)
entry_qty = tk.Entry(left_frame, width=28)
entry_qty.grid(row=4, column=1, pady=4)

tk.Label(left_frame, text="Price (₹):", bg="#f0f4f8").grid(row=5, column=0, sticky='w', pady=4)
entry_price = tk.Entry(left_frame, width=28)
entry_price.grid(row=5, column=1, pady=4)

tk.Label(left_frame, text="Supplier:", bg="#f0f4f8").grid(row=6, column=0, sticky='w', pady=4)
entry_supplier = tk.Entry(left_frame, width=28)
entry_supplier.grid(row=6, column=1, pady=4)

tk.Label(left_frame, text=f"Expiry Date ({DATE_FORMAT}):", bg="#f0f4f8").grid(row=7, column=0, sticky='w', pady=4)
entry_expiry = tk.Entry(left_frame, width=28)
entry_expiry.grid(row=7, column=1, pady=4)

# selected item id for update
selected_id = None

# ---------- Treeview & Right panel ----------
right_frame = tk.Frame(root, bg="#ffffff")
right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=6)

# Search frame
search_frame = tk.Frame(right_frame, bg="#ffffff")
search_frame.pack(fill=tk.X, pady=(6,4))

tk.Label(search_frame, text="Search:", bg="#ffffff").pack(side=tk.LEFT, padx=(6,4))
search_var = tk.StringVar()
search_entry = tk.Entry(search_frame, textvariable=search_var, width=30)
search_entry.pack(side=tk.LEFT, padx=4)

tk.Label(search_frame, text="Filter by:", bg="#ffffff").pack(side=tk.LEFT, padx=(8,4))
filter_by_var = tk.StringVar(value="product_name")
filter_menu = ttk.Combobox(search_frame, textvariable=filter_by_var, values=["product_name", "category", "batch_no", "supplier"], width=12, state="readonly")
filter_menu.pack(side=tk.LEFT, padx=4)

def do_search(event=None):
    q = search_var.get().strip()
    col = filter_by_var.get()
    if q == "":
        load_table()
        return
    sql = f"SELECT id, product_name, category, batch_no, quantity, price, supplier, expiry_date FROM inventory WHERE {col} LIKE ? ORDER BY expiry_date"
    cur.execute(sql, (f"%{q}%",))
    rows = cur.fetchall()
    populate_table(rows)

search_btn = tk.Button(search_frame, text="Search", command=do_search)
search_btn.pack(side=tk.LEFT, padx=6)
clear_btn = tk.Button(search_frame, text="Clear", command=lambda: (search_var.set(""), load_table()))
clear_btn.pack(side=tk.LEFT)

# Treeview (table)
cols = ("id", "product_name", "category", "batch_no", "quantity", "price", "supplier", "expiry_date")
tree = ttk.Treeview(right_frame, columns=cols, show="headings", height=20)
for c in cols:
    tree.heading(c, text=c.replace("_", " ").title())
    # set width for readability
    if c == "product_name":
        tree.column(c, width=220)
    elif c == "expiry_date":
        tree.column(c, width=110)
    else:
        tree.column(c, width=100)

tree.pack(fill=tk.BOTH, padx=6, pady=6, expand=True)

# scrollbar
vsb = ttk.Scrollbar(right_frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=vsb.set)
vsb.pack(side=tk.RIGHT, fill=tk.Y)

# Footer buttons frame
buttons_frame = tk.Frame(right_frame, bg="#ffffff")
buttons_frame.pack(fill=tk.X, pady=6)

# ---------- Database operations: add, update, delete ----------
def clear_form():
    global selected_id
    selected_id = None
    entry_name.delete(0, tk.END)
    entry_cat.delete(0, tk.END)
    entry_batch.delete(0, tk.END)
    entry_qty.delete(0, tk.END)
    entry_price.delete(0, tk.END)
    entry_supplier.delete(0, tk.END)
    entry_expiry.delete(0, tk.END)

def add_product():
    name = entry_name.get().strip()
    cat = entry_cat.get().strip()
    batch = entry_batch.get().strip()
    qty = entry_qty.get().strip()
    price = entry_price.get().strip()
    supplier = entry_supplier.get().strip()
    expiry = entry_expiry.get().strip()

    if not name or not qty:
        messagebox.showerror("Validation Error", "Product name and quantity are required.")
        return
    try:
        qty_i = int(qty)
        if qty_i < 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Validation Error", "Quantity must be a non-negative integer.")
        return

    if price:
        try:
            price_f = float(price)
        except ValueError:
            messagebox.showerror("Validation Error", "Price must be a number (use '.' for decimals).")
            return
    else:
        price_f = None

    if expiry:
        try:
            # validate date
            parse_date(expiry)
        except Exception:
            messagebox.showerror("Validation Error", f"Expiry date must be in {DATE_FORMAT} format.")
            return

    created_on = today_str()
    cur.execute("""
        INSERT INTO inventory (product_name, category, batch_no, quantity, price, supplier, expiry_date, created_on)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, cat, batch, qty_i, price_f, supplier, expiry if expiry else None, created_on))
    conn.commit()
    messagebox.showinfo("Success", "Product added to inventory.")
    clear_form()
    load_table()

def on_tree_select(event):
    global selected_id
    sel = tree.selection()
    if not sel:
        return
    item = tree.item(sel[0])['values']
    if not item:
        return
    selected_id = item[0]
    # populate form with selected row
    entry_name.delete(0, tk.END); entry_name.insert(0, item[1])
    entry_cat.delete(0, tk.END); entry_cat.insert(0, item[2])
    entry_batch.delete(0, tk.END); entry_batch.insert(0, item[3])
    entry_qty.delete(0, tk.END); entry_qty.insert(0, item[4])
    entry_price.delete(0, tk.END); entry_price.insert(0, item[5])
    entry_supplier.delete(0, tk.END); entry_supplier.insert(0, item[6])
    entry_expiry.delete(0, tk.END); entry_expiry.insert(0, item[7] if item[7] else "")

def update_product():
    global selected_id
    if not selected_id:
        messagebox.showerror("Selection Error", "Select a product from the table to update.")
        return
    name = entry_name.get().strip()
    cat = entry_cat.get().strip()
    batch = entry_batch.get().strip()
    qty = entry_qty.get().strip()
    price = entry_price.get().strip()
    supplier = entry_supplier.get().strip()
    expiry = entry_expiry.get().strip()

    if not name or not qty:
        messagebox.showerror("Validation Error", "Product name and quantity are required.")
        return
    try:
        qty_i = int(qty)
        if qty_i < 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Validation Error", "Quantity must be a non-negative integer.")
        return

    if price:
        try:
            price_f = float(price)
        except ValueError:
            messagebox.showerror("Validation Error", "Price must be a number.")
            return
    else:
        price_f = None

    if expiry:
        try:
            parse_date(expiry)
        except Exception:
            messagebox.showerror("Validation Error", f"Expiry date must be in {DATE_FORMAT} format.")
            return

    cur.execute("""
        UPDATE inventory
        SET product_name=?, category=?, batch_no=?, quantity=?, price=?, supplier=?, expiry_date=?
        WHERE id=?
    """, (name, cat, batch, qty_i, price_f, supplier, expiry if expiry else None, selected_id))
    conn.commit()
    messagebox.showinfo("Success", "Product updated.")
    clear_form()
    load_table()

def delete_product():
    sel = tree.selection()
    if not sel:
        messagebox.showerror("Selection Error", "Select a product from the table to delete.")
        return
    item = tree.item(sel[0])['values']
    pid = item[0]
    confirm = messagebox.askyesno("Delete", f"Delete product ID {pid}? This cannot be undone.")
    if not confirm:
        return
    cur.execute("DELETE FROM inventory WHERE id=?", (pid,))
    conn.commit()
    messagebox.showinfo("Deleted", "Product removed from inventory.")
    clear_form()
    load_table()

# ---------- Table population ----------
def populate_table(rows):
    # clear existing
    for r in tree.get_children():
        tree.delete(r)
    for row in rows:
        tree.insert("", tk.END, values=row)

def load_table():
    cur.execute("SELECT id, product_name, category, batch_no, quantity, price, supplier, expiry_date FROM inventory ORDER BY expiry_date")
    rows = cur.fetchall()
    populate_table(rows)

# ---------- Expiry & low-stock utilities ----------
def show_expiring_soon():
    # popup to ask days threshold
    ans = tk.simpledialog.askinteger("Expiring Soon", "Show items expiring within how many days?", initialvalue=30, minvalue=1)
    if ans is None:
        return
    cutoff = datetime.now().date() + timedelta(days=ans)
    cur.execute("SELECT id, product_name, category, batch_no, quantity, price, supplier, expiry_date FROM inventory WHERE expiry_date IS NOT NULL")
    rows = cur.fetchall()
    results = []
    for r in rows:
        if r[7]:
            try:
                d = parse_date(r[7])
                if d <= cutoff:
                    results.append(r)
            except Exception:
                pass
    if not results:
        messagebox.showinfo("No Results", f"No items expiring within {ans} days.")
        return
    # show results in a new window with treeview
    win = tk.Toplevel(root)
    win.title(f"Items expiring within {ans} days")
    tv = ttk.Treeview(win, columns=cols, show="headings")
    for c in cols:
        tv.heading(c, text=c.replace("_", " ").title())
        tv.column(c, width=120)
    tv.pack(fill=tk.BOTH, expand=True)
    for r in results:
        tv.insert("", tk.END, values=r)

def show_low_stock():
    ans = tk.simpledialog.askinteger("Low Stock Threshold", "Show items with quantity below what threshold?", initialvalue=5, minvalue=0)
    if ans is None:
        return
    cur.execute("SELECT id, product_name, category, batch_no, quantity, price, supplier, expiry_date FROM inventory WHERE quantity <= ? ORDER BY quantity", (ans,))
    rows = cur.fetchall()
    if not rows:
        messagebox.showinfo("No Results", f"No items with quantity <= {ans}.")
        return
    win = tk.Toplevel(root)
    win.title(f"Items with quantity <= {ans}")
    tv = ttk.Treeview(win, columns=cols, show="headings")
    for c in cols:
        tv.heading(c, text=c.replace("_", " ").title())
        tv.column(c, width=120)
    tv.pack(fill=tk.BOTH, expand=True)
    for r in rows:
        tv.insert("", tk.END, values=r)

# ---------- Export to CSV ----------
def export_csv():
    rows = []
    for iid in tree.get_children():
        rows.append(tree.item(iid)['values'])
    if not rows:
        messagebox.showwarning("No Data", "No data to export. Load table or run a search first.")
        return
    # ask file
    default_name = f"pharmacy_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=default_name, filetypes=[("CSV files","*.csv"), ("All files","*.*")])
    if not path:
        return
    header = ["id", "product_name", "category", "batch_no", "quantity", "price", "supplier", "expiry_date"]
    try:
        with open(path, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        messagebox.showinfo("Exported", f"Exported {len(rows)} rows to {os.path.basename(path)}")
    except Exception as e:
        messagebox.showerror("Export Error", f"Could not write CSV: {e}")

# ---------- Layout buttons ----------
btn_add = tk.Button(left_frame, text="Add Product", width=20, command=add_product, bg="#b3e6b3")
btn_add.grid(row=9, column=0, columnspan=2, pady=(10,4))

btn_update = tk.Button(left_frame, text="Update Selected", width=20, command=update_product, bg="#fff2b3")
btn_update.grid(row=10, column=0, columnspan=2, pady=(4,4))

btn_delete = tk.Button(left_frame, text="Delete Selected", width=20, command=delete_product, bg="#ffb3b3")
btn_delete.grid(row=11, column=0, columnspan=2, pady=(4,8))

btn_clear = tk.Button(left_frame, text="Clear Form", width=20, command=clear_form)
btn_clear.grid(row=12, column=0, columnspan=2, pady=(4,8))

# right-side action buttons
btn_expiring = tk.Button(buttons_frame, text="Expiring Soon", command=show_expiring_soon, bg="#ffd9b3")
btn_expiring.pack(side=tk.LEFT, padx=6)

btn_low = tk.Button(buttons_frame, text="Low Stock", command=show_low_stock, bg="#ffd9b3")
btn_low.pack(side=tk.LEFT, padx=6)

btn_export = tk.Button(buttons_frame, text="Export CSV", command=export_csv, bg="#cfe8ff")
btn_export.pack(side=tk.LEFT, padx=6)

btn_refresh = tk.Button(buttons_frame, text="Refresh Table", command=load_table, bg="#e6e6e6")
btn_refresh.pack(side=tk.LEFT, padx=6)

# Bind tree selection
tree.bind("<<TreeviewSelect>>", on_tree_select)

# Load table on start
load_table()

# Helpful note label
note = tk.Label(root, text=f"Date format: {DATE_FORMAT} (e.g. 2025-11-23). Use exact format for expiry.", bg="#f0f4f8", fg="#333")
note.pack(side=tk.BOTTOM, pady=6)

# Start GUI
root.mainloop()
