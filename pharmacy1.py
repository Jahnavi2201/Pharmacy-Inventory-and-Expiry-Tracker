import sqlite3
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta

# Database connection
conn = sqlite3.connect("pharmacy_simple.db")
cur = conn.cursor()

# Create table
cur.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    quantity INTEGER,
    expiry TEXT
)
""")
conn.commit()

# ------------------ Functions ------------------

def add_item():
    name = entry_name.get().strip()
    qty = entry_qty.get().strip()
    expiry = entry_expiry.get().strip()

    if not name or not qty or not expiry:
        messagebox.showerror("Error", "All fields are required!")
        return

    try:
        qty = int(qty)
    except:
        messagebox.showerror("Error", "Quantity must be a number")
        return
    
    try:
        datetime.strptime(expiry, "%Y-%m-%d")
    except:
        messagebox.showerror("Error", "Expiry must be in YYYY-MM-DD format")
        return

    cur.execute("INSERT INTO inventory (name, quantity, expiry) VALUES (?, ?, ?)",
                (name, qty, expiry))
    conn.commit()
    messagebox.showinfo("Success", "Item added!")
    load_items()
    clear_fields()

def load_items():
    listbox.delete(0, tk.END)
    cur.execute("SELECT * FROM inventory")
    rows = cur.fetchall()
    for r in rows:
        listbox.insert(tk.END, f"ID:{r[0]} | {r[1]} | Qty:{r[2]} | Exp:{r[3]}")

def clear_fields():
    entry_name.delete(0, tk.END)
    entry_qty.delete(0, tk.END)
    entry_expiry.delete(0, tk.END)

def delete_item():
    selected = listbox.curselection()
    if not selected:
        messagebox.showerror("Error", "Select an item to delete")
        return
    item_text = listbox.get(selected[0])
    item_id = int(item_text.split("|")[0].replace("ID:", "").strip())

    cur.execute("DELETE FROM inventory WHERE id=?", (item_id,))
    conn.commit()
    load_items()
    messagebox.showinfo("Deleted", "Item removed")

def check_expiry():
    listbox.delete(0, tk.END)
    today = datetime.now().date()
    upcoming = today + timedelta(days=30)

    cur.execute("SELECT * FROM inventory")
    rows = cur.fetchall()

    for r in rows:
        exp_date = datetime.strptime(r[3], "%Y-%m-%d").date()
        if exp_date <= upcoming:
            listbox.insert(tk.END, f"EXPIRING SOON → ID:{r[0]} | {r[1]} | Exp:{r[3]}")
    
    if listbox.size() == 0:
        messagebox.showinfo("Info", "No items expiring soon")

# ------------------ GUI ------------------

root = tk.Tk()
root.title("Simple Pharmacy Inventory Tracker")
root.geometry("420x500")

tk.Label(root, text="Pharmacy Inventory Tracker", font=("Arial", 16, "bold")).pack(pady=10)

# Input fields
tk.Label(root, text="Medicine Name").pack()
entry_name = tk.Entry(root, width=30)
entry_name.pack()

tk.Label(root, text="Quantity").pack()
entry_qty = tk.Entry(root, width=30)
entry_qty.pack()

tk.Label(root, text="Expiry (YYYY-MM-DD)").pack()
entry_expiry = tk.Entry(root, width=30)
entry_expiry.pack()

# Buttons
tk.Button(root, text="Add Item", width=20, command=add_item).pack(pady=8)
tk.Button(root, text="Delete Selected", width=20, command=delete_item).pack(pady=8)
tk.Button(root, text="Show Expiring Soon", width=20, command=check_expiry).pack(pady=8)
tk.Button(root, text="Refresh List", width=20, command=load_items).pack(pady=8)

# Listbox to show items
listbox = tk.Listbox(root, width=50, height=15)
listbox.pack(pady=10)

# Load items on startup
load_items()

root.mainloop()
