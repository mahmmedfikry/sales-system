import os
import shutil
import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk, filedialog

# ==========================================
# 1. CONSTANTS & CONFIGURATION
# ==========================================
DB_NAME = "ibn_ezz_pos.db"

# Color Palette (Modern Dark & Professional Theme)
COLOR_BG_DARK = "#1E1E2E"
COLOR_SIDEBAR = "#11111B"
COLOR_CARD = "#2A2A3C"
COLOR_ACCENT = "#74C7EC"
COLOR_SUCCESS = "#A6E3A1"
COLOR_WARNING = "#F9E2AF"
COLOR_DANGER = "#F38BA8"
COLOR_TEXT = "#CDD6F4"
COLOR_TEXT_MUTED = "#BAC2DE"
COLOR_INPUT_BG = "#313244"


# ==========================================
# 2. DATABASE ARCHITECTURE MANAGER
# ==========================================
class DatabaseManager:
    def __init__(self, db_path=DB_NAME):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Products Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barcode TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    buy_price REAL NOT NULL,
                    sell_price REAL NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 0,
                    category TEXT DEFAULT 'عام'
                );
            """)

            # Invoices Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    customer_name TEXT DEFAULT 'عميل نقدي',
                    total_amount REAL NOT NULL,
                    discount REAL DEFAULT 0.0,
                    final_amount REAL NOT NULL,
                    paid_amount REAL NOT NULL,
                    change_amount REAL NOT NULL
                );
            """)

            # Invoice Items Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS invoice_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    subtotal REAL NOT NULL,
                    FOREIGN KEY (invoice_id) REFERENCES invoices (id) ON DELETE CASCADE
                );
            """)

            # Indexes for High Performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date);")
            conn.commit()

    def add_product(self, barcode, name, buy_price, sell_price, quantity, category):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO products (barcode, name, buy_price, sell_price, quantity, category)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (barcode, name, buy_price, sell_price, quantity, category))
            conn.commit()

    def update_product(self, prod_id, barcode, name, buy_price, sell_price, quantity, category):
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE products 
                SET barcode=?, name=?, buy_price=?, sell_price=?, quantity=?, category=?
                WHERE id=?
            """, (barcode, name, buy_price, sell_price, quantity, category, prod_id))
            conn.commit()

    def delete_product(self, prod_id):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM products WHERE id=?", (prod_id,))
            conn.commit()

    def get_all_products(self, search_query=""):
        with self.get_connection() as conn:
            if search_query:
                query = "%" + search_query + "%"
                return conn.execute("""
                    SELECT * FROM products 
                    WHERE name LIKE ? OR barcode LIKE ? OR category LIKE ?
                    ORDER BY id DESC
                """, (query, query, query)).fetchall()
            return conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()

    def get_product_by_barcode(self, barcode):
        with self.get_connection() as conn:
            return conn.execute("SELECT * FROM products WHERE barcode=?", (barcode,)).fetchone()

    # Atomic Transaction for POS Checkout
    def process_sale(self, customer_name, cart_items, total_amount, discount, final_amount, paid_amount, change_amount):
        conn = self.get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE;")
            cursor = conn.cursor()

            # Insert Invoice
            cursor.execute("""
                INSERT INTO invoices (customer_name, total_amount, discount, final_amount, paid_amount, change_amount)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (customer_name, total_amount, discount, final_amount, paid_amount, change_amount))
            
            invoice_id = cursor.lastrowid

            # Insert Invoice Items & Update Stock
            for item in cart_items:
                cursor.execute("""
                    INSERT INTO invoice_items (invoice_id, product_id, product_name, quantity, unit_price, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (invoice_id, item['id'], item['name'], item['qty'], item['price'], item['subtotal']))

                # Stock Deduction with check
                cursor.execute("""
                    UPDATE products 
                    SET quantity = quantity - ? 
                    WHERE id = ? AND quantity >= ?
                """, (item['qty'], item['id'], item['qty']))

                if cursor.rowcount == 0:
                    raise ValueError(f"المخزون غير كافٍ للمنتج: {item['name']}")

            conn.commit()
            return invoice_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_invoices(self):
        with self.get_connection() as conn:
            return conn.execute("SELECT * FROM invoices ORDER BY id DESC").fetchall()

    def get_invoice_details(self, invoice_id):
        with self.get_connection() as conn:
            inv = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
            items = conn.execute("SELECT * FROM invoice_items WHERE invoice_id=?", (invoice_id,)).fetchall()
            return inv, items

    def get_reports_summary(self):
        with self.get_connection() as conn:
            total_sales = conn.execute("SELECT COALESCE(SUM(final_amount), 0) FROM invoices").fetchone()[0]
            total_invoices = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
            total_products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            low_stock = conn.execute("SELECT COUNT(*) FROM products WHERE quantity <= 5").fetchone()[0]
            return {
                "sales": total_sales,
                "invoices": total_invoices,
                "products": total_products,
                "low_stock": low_stock
            }

    def reset_database(self):
        with self.get_connection() as conn:
            conn.execute("DROP TABLE IF EXISTS invoice_items;")
            conn.execute("DROP TABLE IF EXISTS invoices;")
            conn.execute("DROP TABLE IF EXISTS products;")
            conn.commit()
        self.init_db()


# ==========================================
# 3. GUI APPLICATION MAIN FRAMEWORK
# ==========================================
class IbnEzzApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.title("نظام إدارة المبيعات والمخازن - متجر ابن عز")
        self.geometry("1280x760")
        self.minsize(1024, 600)
        self.configure(bg=COLOR_BG_DARK)

        self.cart = []

        self.setup_styles()
        self.build_ui()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Configure General Treeview
        style.configure("Treeview",
                        background=COLOR_CARD,
                        foreground=COLOR_TEXT,
                        fieldbackground=COLOR_CARD,
                        rowheight=30,
                        font=("Segoe UI", 10))
        style.map("Treeview", background=[("selected", COLOR_ACCENT)], foreground=[("selected", COLOR_SIDEBAR)])

        style.configure("Treeview.Heading",
                        background=COLOR_SIDEBAR,
                        foreground=COLOR_TEXT,
                        font=("Segoe UI", 10, "bold"))

        # Notebook Styles
        style.configure("TNotebook", background=COLOR_BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background=COLOR_SIDEBAR, foreground=COLOR_TEXT, padding=[15, 8], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", COLOR_ACCENT)], foreground=[("selected", COLOR_SIDEBAR)])

    def build_ui(self):
        # Header Bar
        header = tk.Frame(self, bg=COLOR_SIDEBAR, height=60)
        header.pack(side=tk.TOP, fill=tk.X)

        title_lbl = tk.Label(header, text="🛒 متجر ابن عز - نظام المبيعات الاحترافي", font=("Segoe UI", 16, "bold"), bg=COLOR_SIDEBAR, fg=COLOR_ACCENT)
        title_lbl.pack(side=tk.RIGHT, padx=20, pady=10)

        # Main Tab Control
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tabs Setup
        self.tab_pos = tk.Frame(self.notebook, bg=COLOR_BG_DARK)
        self.tab_products = tk.Frame(self.notebook, bg=COLOR_BG_DARK)
        self.tab_invoices = tk.Frame(self.notebook, bg=COLOR_BG_DARK)
        self.tab_reports = tk.Frame(self.notebook, bg=COLOR_BG_DARK)
        self.tab_settings = tk.Frame(self.notebook, bg=COLOR_BG_DARK)

        self.notebook.add(self.tab_pos, text="  شاشة البيع (POS)  ")
        self.notebook.add(self.tab_products, text="  إدارة المنتجات  ")
        self.notebook.add(self.tab_invoices, text="  سجل الفواتير  ")
        self.notebook.add(self.tab_reports, text="  التقارير والإحصائيات  ")
        self.notebook.add(self.tab_settings, text="  الصيانة والنسخ الاحتياطي  ")

        # Build Tab Contents
        self.build_pos_tab()
        self.build_products_tab()
        self.build_invoices_tab()
        self.build_reports_tab()
        self.build_settings_tab()

    # ------------------------------------------
    # TAB 1: POS SCREEN
    # ------------------------------------------
    def build_pos_tab(self):
        left_frame = tk.Frame(self.tab_pos, bg=COLOR_CARD, width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)

        right_frame = tk.Frame(self.tab_pos, bg=COLOR_BG_DARK)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Product Search Bar (Top Right)
        search_frame = tk.Frame(right_frame, bg=COLOR_BG_DARK)
        search_frame.pack(fill=tk.X, pady=5)

        tk.Label(search_frame, text="البحث (باركود / اسم):", bg=COLOR_BG_DARK, fg=COLOR_TEXT, font=("Segoe UI", 11)).pack(side=tk.RIGHT, padx=5)
        self.pos_search_entry = tk.Entry(search_frame, bg=COLOR_INPUT_BG, fg=COLOR_TEXT, font=("Segoe UI", 11), insertbackground=COLOR_TEXT)
        self.pos_search_entry.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)
        self.pos_search_entry.bind("<KeyRelease>", self.filter_pos_products)
        self.pos_search_entry.bind("<Return>", self.quick_add_barcode)

        # Products Quick List Table
        self.pos_prod_tree = ttk.Treeview(right_frame, columns=("id", "barcode", "name", "price", "stock"), show="headings")
        self.pos_prod_tree.heading("id", text="ID")
        self.pos_prod_tree.heading("barcode", text="الباركود")
        self.pos_prod_tree.heading("name", text="اسم المنتج")
        self.pos_prod_tree.heading("price", text="السعر")
        self.pos_prod_tree.heading("stock", text="المخزون")

        self.pos_prod_tree.column("id", width=40, anchor="center")
        self.pos_prod_tree.column("barcode", width=120, anchor="center")
        self.pos_prod_tree.column("name", width=200, anchor="e")
        self.pos_prod_tree.column("price", width=80, anchor="center")
        self.pos_prod_tree.column("stock", width=80, anchor="center")
        self.pos_prod_tree.pack(fill=tk.BOTH, expand=True, pady=5)
        self.pos_prod_tree.bind("<Double-1>", self.add_to_cart_selected)

        # Left Cart Area
        tk.Label(left_frame, text="سلة المبيعات الحالية", font=("Segoe UI", 12, "bold"), bg=COLOR_CARD, fg=COLOR_ACCENT).pack(pady=10)

        self.cart_tree = ttk.Treeview(left_frame, columns=("name", "qty", "price", "total"), show="headings")
        self.cart_tree.heading("name", text="المنتج")
        self.cart_tree.heading("qty", text="الكمية")
        self.cart_tree.heading("price", text="السعر")
        self.cart_tree.heading("total", text="الإجمالي")

        self.cart_tree.column("name", width=120, anchor="e")
        self.cart_tree.column("qty", width=50, anchor="center")
        self.cart_tree.column("price", width=60, anchor="center")
        self.cart_tree.column("total", width=70, anchor="center")
        self.cart_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Controls & Payment Panel
        pay_panel = tk.Frame(left_frame, bg=COLOR_CARD)
        pay_panel.pack(fill=tk.X, padx=5, pady=10)

        tk.Label(pay_panel, text="اسم العميل:", bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=0, column=1, sticky="e", pady=2)
        self.cust_name_entry = tk.Entry(pay_panel, bg=COLOR_INPUT_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT)
        self.cust_name_entry.insert(0, "عميل نقدي")
        self.cust_name_entry.grid(row=0, column=0, fill=tk.X, pady=2, padx=5)

        tk.Label(pay_panel, text="الخصم (ج.م):", bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=1, column=1, sticky="e", pady=2)
        self.discount_entry = tk.Entry(pay_panel, bg=COLOR_INPUT_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT)
        self.discount_entry.insert(0, "0")
        self.discount_entry.grid(row=1, column=0, fill=tk.X, pady=2, padx=5)
        self.discount_entry.bind("<KeyRelease>", lambda e: self.update_cart_totals())

        tk.Label(pay_panel, text="المبلغ المدفوع:", bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=2, column=1, sticky="e", pady=2)
        self.paid_entry = tk.Entry(pay_panel, bg=COLOR_INPUT_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT)
        self.paid_entry.insert(0, "0")
        self.paid_entry.grid(row=2, column=0, fill=tk.X, pady=2, padx=5)
        self.paid_entry.bind("<KeyRelease>", lambda e: self.update_cart_totals())

        self.lbl_total = tk.Label(left_frame, text="الإجمالي: 0.00 ج.م", font=("Segoe UI", 12, "bold"), bg=COLOR_CARD, fg=COLOR_SUCCESS)
        self.lbl_total.pack(pady=5)

        self.lbl_change = tk.Label(left_frame, text="الباقي: 0.00 ج.م", font=("Segoe UI", 11), bg=COLOR_CARD, fg=COLOR_WARNING)
        self.lbl_change.pack(pady=2)

        btn_box = tk.Frame(left_frame, bg=COLOR_CARD)
        btn_box.pack(fill=tk.X, pady=10)

        tk.Button(btn_box, text="إتمام الدفع والطباعة 🖨️", bg=COLOR_SUCCESS, fg="#000", font=("Segoe UI", 11, "bold"), command=self.complete_sale).pack(fill=tk.X, padx=5, pady=2)
        tk.Button(btn_box, text="إفرغ السلة 🗑️", bg=COLOR_DANGER, fg="#FFF", font=("Segoe UI", 9), command=self.clear_cart).pack(fill=tk.X, padx=5, pady=2)

        self.load_pos_products()

    def load_pos_products(self, query=""):
        for row in self.pos_prod_tree.get_children():
            self.pos_prod_tree.delete(row)
        products = self.db.get_all_products(query)
        for p in products:
            self.pos_prod_tree.insert("", tk.END, values=(p['id'], p['barcode'], p['name'], f"{p['sell_price']:.2f}", p['quantity']))

    def filter_pos_products(self, event=None):
        q = self.pos_search_entry.get().strip()
        self.load_pos_products(q)

    def quick_add_barcode(self, event=None):
        barcode = self.pos_search_entry.get().strip()
        if not barcode:
            return
        prod = self.db.get_product_by_barcode(barcode)
        if prod:
            self.add_to_cart(prod)
            self.pos_search_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("تنبيه", "المنتج غير موجود بجدول المنتجات")

    def add_to_cart_selected(self, event=None):
        selected = self.pos_prod_tree.selection()
        if not selected:
            return
        item_id = self.pos_prod_tree.item(selected[0])['values'][0]
        products = self.db.get_all_products()
        prod = next((p for p in products if p['id'] == item_id), None)
        if prod:
            self.add_to_cart(prod)

    def add_to_cart(self, prod):
        if prod['quantity'] <= 0:
            messagebox.showerror("خطأ", "المنتج نفد من المخزون!")
            return

        for item in self.cart:
            if item['id'] == prod['id']:
                if item['qty'] + 1 > prod['quantity']:
                    messagebox.showerror("خطأ", "الكمية المطلوبة تتجاوز المتاح بالمخزون!")
                    return
                item['qty'] += 1
                item['subtotal'] = item['qty'] * item['price']
                self.refresh_cart_tree()
                return

        self.cart.append({
            'id': prod['id'],
            'name': prod['name'],
            'price': prod['sell_price'],
            'qty': 1,
            'subtotal': prod['sell_price']
        })
        self.refresh_cart_tree()

    def refresh_cart_tree(self):
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        for item in self.cart:
            self.cart_tree.insert("", tk.END, values=(item['name'], item['qty'], f"{item['price']:.2f}", f"{item['subtotal']:.2f}"))
        self.update_cart_totals()

    def update_cart_totals(self):
        raw_total = sum(i['subtotal'] for i in self.cart)
        try:
            discount = float(self.discount_entry.get().strip() or 0)
        except ValueError:
            discount = 0.0

        final_total = max(0.0, raw_total - discount)
        self.lbl_total.config(text=f"الإجمالي: {final_total:.2f} ج.م")

        try:
            paid = float(self.paid_entry.get().strip() or 0)
        except ValueError:
            paid = 0.0

        change = paid - final_total if paid >= final_total else 0.0
        self.lbl_change.config(text=f"الباقي: {change:.2f} ج.م")

    def clear_cart(self):
        self.cart = []
        self.refresh_cart_tree()

    def complete_sale(self):
        if not self.cart:
            messagebox.showwarning("تنبيه", "سلة المبيعات فارغة!")
            return

        cust_name = self.cust_name_entry.get().strip() or "عميل نقدي"
        raw_total = sum(i['subtotal'] for i in self.cart)
        
        try:
            discount = float(self.discount_entry.get().strip() or 0)
            paid = float(self.paid_entry.get().strip() or 0)
        except ValueError:
            messagebox.showerror("خطأ", "برجاء كتابة أرقام صحيحة في الخصم والمبلغ المدفوع")
            return

        final_total = max(0.0, raw_total - discount)
        if paid < final_total:
            messagebox.showerror("خطأ", "المبلغ المدفوع أقل من إجمالي الفاتورة!")
            return

        change = paid - final_total

        try:
            inv_id = self.db.process_sale(cust_name, self.cart, raw_total, discount, final_total, paid, change)
            messagebox.showinfo("نجاح", f"تم حفظ الفاتورة بنجاح رقم: #{inv_id}")
            self.show_receipt_preview(inv_id)
            self.clear_cart()
            self.load_pos_products()
            self.load_products_table()
            self.load_invoices_table()
            self.load_reports_data()
        except Exception as e:
            messagebox.showerror("خطأ في العملية", str(e))

    def show_receipt_preview(self, invoice_id):
        inv, items = self.db.get_invoice_details(invoice_id)
        win = tk.Toplevel(self)
        win.title(f"معاينة الفاتورة #{invoice_id}")
        win.geometry("380x520")
        win.configure(bg="#FFF")

        txt = tk.Text(win, bg="#FFF", fg="#000", font=("Courier", 10))
        txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        receipt_str = "=================================\n"
        receipt_str += "          متجر ابن عز           \n"
        receipt_str += "       إدارة المبيعات والمخازن    \n"
        receipt_str += "=================================\n"
        receipt_str += f"رقم الفاتورة: #{inv['id']}\n"
        receipt_str += f"التاريخ: {inv['invoice_date']}\n"
        receipt_str += f"العميل: {inv['customer_name']}\n"
        receipt_str += "---------------------------------\n"
        receipt_str += f"{'المنتج':<15} {'الكمية':<5} {'السعر':<8}\n"
        receipt_str += "---------------------------------\n"
        for it in items:
            receipt_str += f"{it['product_name'][:14]:<15} {it['quantity']:<5} {it['subtotal']:<8.2f}\n"
        receipt_str += "---------------------------------\n"
        receipt_str += f"الإجمالي: {inv['total_amount']:.2f} ج.م\n"
        receipt_str += f"الخصم: {inv['discount']:.2f} ج.م\n"
        receipt_str += f"الصافي: {inv['final_amount']:.2f} ج.م\n"
        receipt_str += f"المدفوع: {inv['paid_amount']:.2f} ج.م\n"
        receipt_str += f"الباقي: {inv['change_amount']:.2f} ج.م\n"
        receipt_str += "=================================\n"
        receipt_str += "    شكراً لزيارتكم متجر ابن عز    \n"
        receipt_str += "=================================\n"

        txt.insert(tk.END, receipt_str)
        txt.config(state=tk.DISABLED)

    # ------------------------------------------
    # TAB 2: PRODUCTS MANAGEMENT
    # ------------------------------------------
    def build_products_tab(self):
        form_frame = tk.Frame(self.tab_products, bg=COLOR_CARD)
        form_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        # Form Inputs
        tk.Label(form_frame, text="الباركود:", bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=0, column=5, padx=5, pady=5)
        self.p_barcode = tk.Entry(form_frame, bg=COLOR_INPUT_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT)
        self.p_barcode.grid(row=0, column=4, padx=5, pady=5)

        tk.Label(form_frame, text="اسم المنتج:", bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=0, column=3, padx=5, pady=5)
        self.p_name = tk.Entry(form_frame, bg=COLOR_INPUT_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT)
        self.p_name.grid(row=0, column=2, padx=5, pady=5)

        tk.Label(form_frame, text="التصنيف:", bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=0, column=1, padx=5, pady=5)
        self.p_cat = tk.Entry(form_frame, bg=COLOR_INPUT_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT)
        self.p_cat.insert(0, "عام")
        self.p_cat.grid(row=0, column=0, padx=5, pady=5)

        tk.Label(form_frame, text="سعر الشراء:", bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=1, column=5, padx=5, pady=5)
        self.p_buy = tk.Entry(form_frame, bg=COLOR_INPUT_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT)
        self.p_buy.grid(row=1, column=4, padx=5, pady=5)

        tk.Label(form_frame, text="سعر البيع:", bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=1, column=3, padx=5, pady=5)
        self.p_sell = tk.Entry(form_frame, bg=COLOR_INPUT_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT)
        self.p_sell.grid(row=1, column=2, padx=5, pady=5)

        tk.Label(form_frame, text="الكمية:", bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=1, column=1, padx=5, pady=5)
        self.p_qty = tk.Entry(form_frame, bg=COLOR_INPUT_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT)
        self.p_qty.grid(row=1, column=0, padx=5, pady=5)

        # Action Buttons
        btn_frame = tk.Frame(form_frame, bg=COLOR_CARD)
        btn_frame.grid(row=2, column=0, columnspan=6, pady=10)

        tk.Button(btn_frame, text="إضافة منتج ➕", bg=COLOR_SUCCESS, fg="#000", font=("Segoe UI", 9, "bold"), command=self.save_product).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="تحديث المنتج ✏️", bg=COLOR_ACCENT, fg="#000", font=("Segoe UI", 9, "bold"), command=self.update_product).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="حذف المنتج 🗑️", bg=COLOR_DANGER, fg="#FFF", font=("Segoe UI", 9, "bold"), command=self.delete_product).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="تفريغ الحقول 🔄", bg=COLOR_WARNING, fg="#000", font=("Segoe UI", 9), command=self.clear_prod_form).pack(side=tk.RIGHT, padx=5)

        # Products Table
        self.prod_tree = ttk.Treeview(self.tab_products, columns=("id", "barcode", "name", "cat", "buy", "sell", "qty"), show="headings")
        self.prod_tree.heading("id", text="ID")
        self.prod_tree.heading("barcode", text="الباركود")
        self.prod_tree.heading("name", text="اسم المنتج")
        self.prod_tree.heading("cat", text="التصنيف")
        self.prod_tree.heading("buy", text="شراء")
        self.prod_tree.heading("sell", text="بيع")
        self.prod_tree.heading("qty", text="الكمية")

        for col in ("id", "barcode", "name", "cat", "buy", "sell", "qty"):
            self.prod_tree.column(col, anchor="center")

        self.prod_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.prod_tree.bind("<<TreeviewSelect>>", self.on_product_select)

        self.selected_prod_id = None
        self.load_products_table()

    def load_products_table(self):
        for row in self.prod_tree.get_children():
            self.prod_tree.delete(row)
        for p in self.db.get_all_products():
            self.prod_tree.insert("", tk.END, values=(p['id'], p['barcode'], p['name'], p['category'], f"{p['buy_price']:.2f}", f"{p['sell_price']:.2f}", p['quantity']))

    def on_product_select(self, event):
        selected = self.prod_tree.selection()
        if not selected:
            return
        vals = self.prod_tree.item(selected[0])['values']
        self.selected_prod_id = vals[0]
        
        self.p_barcode.delete(0, tk.END)
        self.p_barcode.insert(0, vals[1])
        
        self.p_name.delete(0, tk.END)
        self.p_name.insert(0, vals[2])

        self.p_cat.delete(0, tk.END)
        self.p_cat.insert(0, vals[3])

        self.p_buy.delete(0, tk.END)
        self.p_buy.insert(0, vals[4])

        self.p_sell.delete(0, tk.END)
        self.p_sell.insert(0, vals[5])

        self.p_qty.delete(0, tk.END)
        self.p_qty.insert(0, vals[6])

    def clear_prod_form(self):
        self.selected_prod_id = None
        for entry in (self.p_barcode, self.p_name, self.p_buy, self.p_sell, self.p_qty):
            entry.delete(0, tk.END)
        self.p_cat.delete(0, tk.END)
        self.p_cat.insert(0, "عام")

    def save_product(self):
        try:
            b = self.p_barcode.get().strip()
            n = self.p_name.get().strip()
            c = self.p_cat.get().strip() or "عام"
            bp = float(self.p_buy.get().strip())
            sp = float(self.p_sell.get().strip())
            q = int(self.p_qty.get().strip())

            if not b or not n:
                messagebox.showerror("خطأ", "الباركود والاسم حقول مطلوبة!")
                return

            self.db.add_product(b, n, bp, sp, q, c)
            messagebox.showinfo("نجاح", "تمت إضافة المنتج بنجاح")
            self.clear_prod_form()
            self.load_products_table()
            self.load_pos_products()
        except sqlite3.IntegrityError:
            messagebox.showerror("خطأ", "الباركود مستخدم بالفعل لمنتج آخر!")
        except Exception as e:
            messagebox.showerror("خطأ", f"تعذر إضافة المنتج: {str(e)}")

    def update_product(self):
        if not self.selected_prod_id:
            messagebox.showwarning("تنبيه", "اختر منتجاً للتعديل!")
            return
        try:
            b = self.p_barcode.get().strip()
            n = self.p_name.get().strip()
            c = self.p_cat.get().strip() or "عام"
            bp = float(self.p_buy.get().strip())
            sp = float(self.p_sell.get().strip())
            q = int(self.p_qty.get().strip())

            self.db.update_product(self.selected_prod_id, b, n, bp, sp, q, c)
            messagebox.showinfo("نجاح", "تم تحديث المنتج بنجاح")
            self.clear_prod_form()
            self.load_products_table()
            self.load_pos_products()
        except Exception as e:
            messagebox.showerror("خطأ", f"تعذر تحديث المنتج: {str(e)}")

    def delete_product(self):
        if not self.selected_prod_id:
            messagebox.showwarning("تنبيه", "اختر منتجاً للحذف!")
            return
        if messagebox.askyesno("تأكيد", "هل أنت تأكد من حذف هذا المنتج؟"):
            try:
                self.db.delete_product(self.selected_prod_id)
                messagebox.showinfo("نجاح", "تم حذف المنتج بنجاح")
                self.clear_prod_form()
                self.load_products_table()
                self.load_pos_products()
            except Exception as e:
                messagebox.showerror("خطأ", f"تعذر الحذف: {str(e)}")

    # ------------------------------------------
    # TAB 3: INVOICES HISTORY
    # ------------------------------------------
    def build_invoices_tab(self):
        self.inv_tree = ttk.Treeview(self.tab_invoices, columns=("id", "date", "customer", "total", "discount", "final", "paid", "change"), show="headings")
        self.inv_tree.heading("id", text="رقم الفاتورة")
        self.inv_tree.heading("date", text="التاريخ والوقت")
        self.inv_tree.heading("customer", text="العميل")
        self.inv_tree.heading("total", text="الإجمالي")
        self.inv_tree.heading("discount", text="الخصم")
        self.inv_tree.heading("final", text="الصافي")
        self.inv_tree.heading("paid", text="المدفوع")
        self.inv_tree.heading("change", text="الباقي")

        for c in ("id", "date", "customer", "total", "discount", "final", "paid", "change"):
            self.inv_tree.column(c, anchor="center")

        self.inv_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.inv_tree.bind("<Double-1>", self.on_invoice_double_click)

        self.load_invoices_table()

    def load_invoices_table(self):
        for row in self.inv_tree.get_children():
            self.inv_tree.delete(row)
        invoices = self.db.get_invoices()
        for inv in invoices:
            self.inv_tree.insert("", tk.END, values=(
                inv['id'], inv['invoice_date'], inv['customer_name'],
                f"{inv['total_amount']:.2f}", f"{inv['discount']:.2f}",
                f"{inv['final_amount']:.2f}", f"{inv['paid_amount']:.2f}",
                f"{inv['change_amount']:.2f}"
            ))

    def on_invoice_double_click(self, event):
        selected = self.inv_tree.selection()
        if not selected:
            return
        inv_id = self.inv_tree.item(selected[0])['values'][0]
        self.show_receipt_preview(inv_id)

    # ------------------------------------------
    # TAB 4: REPORTS & DASHBOARD
    # ------------------------------------------
    def build_reports_tab(self):
        container = tk.Frame(self.tab_reports, bg=COLOR_BG_DARK)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Card 1: Total Sales
        self.card_sales = self.create_dashboard_card(container, "إجمالي المبيعات", "0.00 ج.م", COLOR_ACCENT)
        self.card_sales.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Card 2: Total Invoices
        self.card_invoices = self.create_dashboard_card(container, "عدد الفواتير", "0", COLOR_SUCCESS)
        self.card_invoices.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # Card 3: Total Products
        self.card_products = self.create_dashboard_card(container, "عدد الاصناف", "0", COLOR_WARNING)
        self.card_products.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # Card 4: Low Stock Alert
        self.card_stock = self.create_dashboard_card(container, "نواقص المخزون", "0", COLOR_DANGER)
        self.card_stock.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)

        btn_refresh = tk.Button(self.tab_reports, text="تحديث البيانات 🔄", bg=COLOR_ACCENT, fg="#000", font=("Segoe UI", 11, "bold"), command=self.load_reports_data)
        btn_refresh.pack(pady=10)

        self.load_reports_data()

    def create_dashboard_card(self, parent, title, val, color):
        frame = tk.Frame(parent, bg=COLOR_CARD, highlightbackground=color, highlightthickness=2)
        lbl_t = tk.Label(frame, text=title, font=("Segoe UI", 12), bg=COLOR_CARD, fg=COLOR_TEXT_MUTED)
        lbl_t.pack(pady=10)
        lbl_v = tk.Label(frame, text=val, font=("Segoe UI", 20, "bold"), bg=COLOR_CARD, fg=color)
        lbl_v.pack(pady=10)
        frame.val_label = lbl_v
        return frame

    def load_reports_data(self):
        summary = self.db.get_reports_summary()
        self.card_sales.val_label.config(text=f"{summary['sales']:.2f} ج.م")
        self.card_invoices.val_label.config(text=str(summary['invoices']))
        self.card_products.val_label.config(text=str(summary['products']))
        self.card_stock.val_label.config(text=str(summary['low_stock']))

    # ------------------------------------------
    # TAB 5: SYSTEM MAINTENANCE & BACKUP
    # ------------------------------------------
    def build_settings_tab(self):
        box = tk.Frame(self.tab_settings, bg=COLOR_CARD, padx=20, pady=20)
        box.pack(expand=True, pady=30)

        tk.Label(box, text="⚙️ أدوات الصيانة والنسخ الاحتياطي", font=("Segoe UI", 14, "bold"), bg=COLOR_CARD, fg=COLOR_ACCENT).pack(pady=10)

        tk.Button(box, text="إنشاء نسخة احتياطية للقاعدة (Backup) 💾", font=("Segoe UI", 11), bg=COLOR_SUCCESS, fg="#000", width=35, command=self.backup_database).pack(pady=10)
        tk.Button(box, text="استعادة نسخة احتياطية (Restore) 📂", font=("Segoe UI", 11), bg=COLOR_WARNING, fg="#000", width=35, command=self.restore_database).pack(pady=10)
        
        tk.Frame(box, height=2, bg=COLOR_BG_DARK).pack(fill=tk.X, pady=15)

        tk.Button(box, text="إعادة تهيئة النظام بالكامل (Reset System) ⚠️", font=("Segoe UI", 11, "bold"), bg=COLOR_DANGER, fg="#FFF", width=35, command=self.reset_system).pack(pady=10)

    def backup_database(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("Database Files", "*.db")], title="حفظ النسخة الاحتياطية", initialfile=f"ibn_ezz_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        if file_path:
            try:
                shutil.copy2(DB_NAME, file_path)
                messagebox.showinfo("تم", "تم حفظ النسخة الاحتياطية بنجاح!")
            except Exception as e:
                messagebox.showerror("خطأ", f"تعذر الحفظ: {str(e)}")

    def restore_database(self):
        file_path = filedialog.askopenfilename(filetypes=[("Database Files", "*.db")], title="اختر ملف النسخة الاحتياطية")
        if file_path:
            if messagebox.askyesno("تحذير شديد", "استعادة النسخة ستستبدل البيانات الحالية بالكامل، هل تريد الاستمرار؟"):
                try:
                    shutil.copy2(file_path, DB_NAME)
                    messagebox.showinfo("تم", "تمت استعادة قاعدة البيانات بنجاح! سيتم تحديث الشاشات.")
                    self.load_products_table()
                    self.load_pos_products()
                    self.load_invoices_table()
                    self.load_reports_data()
                except Exception as e:
                    messagebox.showerror("خطأ", f"تعذرت الاستعادة: {str(e)}")

    def reset_system(self):
        if messagebox.askyesno("تأكيد خطير جداً", "هل أنت متأكد تماماً من إزالة كافة المنتجات والمبيعات وإعادة النظام لضبط المصنع؟"):
            try:
                self.db.reset_database()
                messagebox.showinfo("تم", "تمت إعادة تهيئة النظام بنجاح!")
                self.clear_cart()
                self.load_products_table()
                self.load_pos_products()
                self.load_invoices_table()
                self.load_reports_data()
            except Exception as e:
                messagebox.showerror("خطأ", f"تعذرت العملية: {str(e)}")


# ==========================================
# 4. ENTRY POINT
# ==========================================
if __name__ == "__main__":
    app = IbnEzzApp()
    app.mainloop()