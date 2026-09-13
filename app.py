#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║                    🛍️  ابـــن عـــز  |  EbnEzz                            ║
║                                                                          ║
║                 نظام إدارة المبيعات الاحترافي  v5.0                       ║
║                Professional Sales Management System                      ║
║                                                                          ║
║                        ━━━━━━━━━━━━━━━━━━━━                              ║
║                                                                          ║
║                   Developed by:  Team MY  © 2026                         ║
║                   Pro Max Edition · Enterprise Security                  ║
║                                                                          ║
║                   جميع الحقوق محفوظة — All Rights Reserved                ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sqlite3, hashlib, base64, os, shutil, csv, secrets, sys, traceback
from datetime import datetime, timedelta
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
#  🏷️  هوية التطبيق — Team MY
# ═══════════════════════════════════════════════════════════════════════════
APP_NAME       = "ابن عز"
APP_NAME_EN    = "EbnEzz"
APP_SUBTITLE   = "نظام إدارة المبيعات الاحترافي"
APP_VERSION    = "5.0.0"
APP_EDITION    = "Pro Max"
APP_BUILD      = "2026.01"
DEVELOPER      = "Team MY"
DEVELOPER_FULL = "فريق MY للبرمجيات"
COPYRIGHT      = "© 2026 ابن عز — جميع الحقوق محفوظة"

# ═══════════════════════════════════════════════════════════════════════════
#  🎨 الألوان
# ═══════════════════════════════════════════════════════════════════════════
CLR = {
    'primary':       '#10b981',   'primary_dark':  '#059669',
    'primary_light': '#34d399',   'secondary':     '#06b6d4',
    'secondary_dark':'#0891b2',   'accent':        '#8b5cf6',
    'gold':          '#fbbf24',   'danger':        '#ef4444',
    'danger_dark':   '#dc2626',   'warning':       '#f59e0b',
    'info':          '#3b82f6',   'success':       '#10b981',
    'dark':          '#1f2937',   'darker':        '#111827',
    'darkest':       '#0f172a',   'light':         '#f9fafb',
    'lighter':       '#f3f4f6',   'white':         '#ffffff',
    'border':        '#e5e7eb',   'border_dark':   '#d1d5db',
    'text':          '#374151',   'text_light':    '#6b7280',
    'text_dark':     '#111827',   'text_muted':    '#9ca3af',
    'sidebar':       '#0f172a',   'sidebar_hover': '#1e293b',
    'sidebar_active':'#10b981',   'sidebar_text':  '#cbd5e1',
}

# ═══════════════════════════════════════════════════════════════════════════
#  🔐 محرك التشفير — صيغة .ebz
# ═══════════════════════════════════════════════════════════════════════════
MAGIC       = b"EBZ\x05\x00\x01\xEB"
APP_SECRET  = b"EbnEzz_ProMax_2026_TeamMY_Secret_v5_!@#$%^&*"
BACKUP_EXT  = ".ebz"

def _pbkdf(pw: str, salt: bytes, n: int = 64) -> bytes:
    return hashlib.pbkdf2_hmac('sha512', pw.encode('utf-8'), salt, 400_000, dklen=n)

def _stream(data: bytes, key: bytes) -> bytes:
    out = bytearray(len(data)); ctr = 0; buf = b""; idx = 0
    while idx < len(data):
        if len(buf) < len(data) - idx:
            buf += hashlib.sha512(key + ctr.to_bytes(8,'big')).digest(); ctr += 1
        n = min(len(buf), len(data)-idx)
        for i in range(n): out[idx+i] = data[idx+i] ^ buf[i]
        buf = buf[n:]; idx += n
    return bytes(out)

def encrypt_bytes(raw: bytes, user_pass: str = "") -> bytes:
    salt = secrets.token_bytes(48)
    fk = hashlib.sha512(APP_SECRET + user_pass.encode()).digest()
    key = _pbkdf(fk.hex(), salt, 64)
    enc = _stream(_stream(raw, key), key[::-1])
    mac = hashlib.sha512(key + raw + salt).digest()
    return MAGIC + salt + mac + enc

def decrypt_bytes(blob: bytes, user_pass: str = "") -> bytes:
    if not blob.startswith(MAGIC):
        raise ValueError("صيغة الملف غير معروفة — ليس ملف ابن عز")
    salt = blob[len(MAGIC):len(MAGIC)+48]
    mac  = blob[len(MAGIC)+48:len(MAGIC)+48+64]
    enc  = blob[len(MAGIC)+48+64:]
    fk = hashlib.sha512(APP_SECRET + user_pass.encode()).digest()
    key = _pbkdf(fk.hex(), salt, 64)
    dec = _stream(_stream(enc, key[::-1]), key)
    if hashlib.sha512(key + dec + salt).digest() != mac:
        raise ValueError("كلمة المرور خاطئة أو الملف تالف!")
    return dec

# ═══════════════════════════════════════════════════════════════════════════
#  🛠️ دوال مساعدة
# ═══════════════════════════════════════════════════════════════════════════
def money(v, cur="ج.م"):
    try: return f"{float(v):,.2f} {cur}"
    except: return f"0.00 {cur}"

def fmt_dt(dt, fmt="%Y-%m-%d %H:%M"):
    if isinstance(dt, str):
        try: dt = datetime.strptime(dt[:19], "%Y-%m-%d %H:%M:%S")
        except: return dt[:10]
    return dt.strftime(fmt) if hasattr(dt,'strftime') else str(dt)

def today(): return datetime.now().strftime('%Y-%m-%d')

def gen_barcode(): return "EB" + secrets.token_hex(6).upper()

# ═══════════════════════════════════════════════════════════════════════════
#  🗄️ قاعدة البيانات
# ═══════════════════════════════════════════════════════════════════════════
class Database:
    def __init__(self, path="ebnezz_data.db"):
        self.path = path
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        self._init()

    def connect(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        return c

    def _init(self):
        c = sqlite3.connect(self.path)
        c.executescript('''
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT DEFAULT '',
                role TEXT DEFAULT 'cashier',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

            CREATE TABLE IF NOT EXISTS products(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT UNIQUE, name TEXT NOT NULL,
                category TEXT DEFAULT 'عام', supplier_id INTEGER,
                price REAL NOT NULL, cost REAL DEFAULT 0,
                quantity INTEGER DEFAULT 0, min_stock INTEGER DEFAULT 5,
                unit TEXT DEFAULT 'قطعة', description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

            CREATE TABLE IF NOT EXISTS customers(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, phone TEXT UNIQUE,
                email TEXT, address TEXT,
                loyalty_points INTEGER DEFAULT 0,
                total_purchases REAL DEFAULT 0, orders_count INTEGER DEFAULT 0,
                last_purchase TIMESTAMP, notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

            CREATE TABLE IF NOT EXISTS orders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE NOT NULL,
                customer_id INTEGER, customer_name TEXT, customer_phone TEXT,
                subtotal REAL DEFAULT 0, discount REAL DEFAULT 0,
                tax REAL DEFAULT 0, final_amount REAL DEFAULT 0,
                paid REAL DEFAULT 0, change_due REAL DEFAULT 0,
                status TEXT DEFAULT 'مكتمل', payment_method TEXT DEFAULT 'كاش',
                notes TEXT, cashier TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

            CREATE TABLE IF NOT EXISTS order_items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL, product_id INTEGER,
                product_name TEXT, barcode TEXT,
                quantity INTEGER NOT NULL, price REAL NOT NULL,
                cost REAL DEFAULT 0, subtotal REAL NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE);

            CREATE TABLE IF NOT EXISTS stock_moves(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER, product_name TEXT, move_type TEXT,
                quantity INTEGER, before_qty INTEGER, after_qty INTEGER,
                reference TEXT, username TEXT, notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT, amount REAL, description TEXT,
                username TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);

            CREATE TABLE IF NOT EXISTS logs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT, details TEXT, username TEXT,
                level TEXT DEFAULT 'info',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

            CREATE INDEX IF NOT EXISTS idx_pname ON products(name);
            CREATE INDEX IF NOT EXISTS idx_pbcode ON products(barcode);
            CREATE INDEX IF NOT EXISTS idx_odate ON orders(created_at);
            CREATE INDEX IF NOT EXISTS idx_cphone ON customers(phone);
            CREATE INDEX IF NOT EXISTS idx_ldate ON logs(created_at);
        ''')
        cur = c.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO users(username,password_hash,full_name,role) VALUES(?,?,?,?)",
                        ("admin", self.hash_pw("admin"), "المدير العام", "admin"))
        defaults = {
            'shop_name': APP_NAME, 'shop_name_en': APP_NAME_EN,
            'shop_phone': '', 'shop_address': '', 'shop_email': '',
            'shop_tax_id': '', 'currency': 'ج.م', 'tax_rate': '0',
            'receipt_footer': f'شكراً لتعاملكم معنا — {APP_NAME}',
            'backup_password': 'ebnezz_default',
            'auto_backup': '1', 'backup_days': '7',
            'loyalty_rate': '0.01', 'theme': 'light',
        }
        for k,v in defaults.items():
            cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(k,v))
        c.commit(); c.close()

    # ── كلمات المرور ──
    @staticmethod
    def hash_pw(pw, salt=None):
        salt = salt or secrets.token_bytes(32)
        h = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt, 250_000)
        return base64.b64encode(salt + h).decode()

    @staticmethod
    def verify_pw(pw, stored):
        try:
            raw = base64.b64decode(stored)
            salt, h = raw[:32], raw[32:]
            return h == hashlib.pbkdf2_hmac('sha256', pw.encode(), salt, 250_000)
        except: return False

    def log(self, action, details="", user="system", level="info"):
        try:
            c = self.connect()
            c.execute("INSERT INTO logs(action,details,username,level) VALUES(?,?,?,?)",
                      (action, details, user, level))
            c.commit(); c.close()
        except: pass

    # ── المستخدمون ──
    def login(self, u, p):
        c = self.connect()
        r = c.execute("SELECT * FROM users WHERE username=? AND is_active=1",(u,)).fetchone()
        c.close()
        return dict(r) if r and self.verify_pw(p, r['password_hash']) else None

    def add_user(self, u, p, name="", role="cashier"):
        try:
            c = self.connect()
            c.execute("INSERT INTO users(username,password_hash,full_name,role) VALUES(?,?,?,?)",
                      (u, self.hash_pw(p), name, role))
            c.commit(); c.close()
            return True, "✅ تم إنشاء المستخدم"
        except sqlite3.IntegrityError:
            return False, "❌ اسم المستخدم موجود"

    def users(self):
        c = self.connect()
        r = [dict(x) for x in c.execute("SELECT * FROM users ORDER BY id").fetchall()]
        c.close(); return r

    def del_user(self, uid):
        c = self.connect()
        c.execute("DELETE FROM users WHERE id=? AND username!='admin'",(uid,))
        c.commit(); c.close()

    def change_pw(self, u, old, new):
        c = self.connect()
        r = c.execute("SELECT password_hash FROM users WHERE username=?",(u,)).fetchone()
        c.close()
        if not r or not self.verify_pw(old, r['password_hash']):
            return False, "كلمة المرور القديمة غير صحيحة"
        c = self.connect()
        c.execute("UPDATE users SET password_hash=? WHERE username=?",(self.hash_pw(new), u))
        c.commit(); c.close()
        self.log("تغيير كلمة المرور", u, u)
        return True, "✅ تم التغيير"

    # ── الإعدادات ──
    def get(self, k, d=""):
        try:
            c = self.connect()
            r = c.execute("SELECT value FROM settings WHERE key=?",(k,)).fetchone()
            c.close()
            return r['value'] if r else d
        except: return d

    def set(self, k, v):
        c = self.connect()
        c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",(k,str(v)))
        c.commit(); c.close()

    def all_settings(self):
        c = self.connect()
        r = {x['key']: x['value'] for x in c.execute("SELECT key,value FROM settings").fetchall()}
        c.close(); return r

    # ── المنتجات ──
    def add_product(self, barcode, name, cat, sup, price, cost, qty, minq, unit):
        try:
            c = self.connect()
            c.execute('''INSERT INTO products(barcode,name,category,supplier_id,price,cost,quantity,min_stock,unit)
                        VALUES(?,?,?,?,?,?,?,?,?)''',
                      (barcode or None, name, cat, sup, price, cost, qty, minq, unit))
            pid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            c.commit(); c.close()
            self.log_move(pid, name, "إضافة", qty, 0, qty, "new")
            return True, pid
        except sqlite3.IntegrityError:
            return False, "الباركود مستخدم"
        except Exception as e:
            return False, str(e)

    def update_product(self, pid, **kw):
        if not kw: return
        cols = ", ".join(f"{k}=?" for k in kw)
        vals = list(kw.values()) + [pid]
        c = self.connect()
        c.execute(f"UPDATE products SET {cols},updated_at=CURRENT_TIMESTAMP WHERE id=?", vals)
        c.commit(); c.close()

    def del_product(self, pid):
        c = self.connect()
        c.execute("DELETE FROM products WHERE id=?",(pid,))
        c.commit(); c.close()

    def product(self, pid):
        c = self.connect()
        r = c.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
        c.close(); return dict(r) if r else None

    def by_barcode(self, b):
        c = self.connect()
        r = c.execute("SELECT * FROM products WHERE barcode=?",(b,)).fetchone()
        c.close(); return dict(r) if r else None

    def products(self, term="", only_active=True):
        c = self.connect()
        q = "SELECT * FROM products WHERE 1=1"
        p = []
        if only_active: q += " AND is_active=1"
        if term:
            q += " AND (name LIKE ? OR barcode LIKE ? OR category LIKE ?)"
            t = f"%{term}%"; p = [t,t,t]
        q += " ORDER BY name"
        r = [dict(x) for x in c.execute(q,p).fetchall()]
        c.close(); return r

    def low_stock(self):
        c = self.connect()
        r = [dict(x) for x in c.execute(
            "SELECT * FROM products WHERE quantity<=min_stock AND is_active=1 ORDER BY quantity").fetchall()]
        c.close(); return r

    def log_move(self, pid, name, mtype, qty, before, after, ref="", user="", notes=""):
        try:
            c = self.connect()
            c.execute('''INSERT INTO stock_moves(product_id,product_name,move_type,quantity,
                        before_qty,after_qty,reference,username,notes) VALUES(?,?,?,?,?,?,?,?,?)''',
                      (pid,name,mtype,qty,before,after,ref,user,notes))
            c.commit(); c.close()
        except: pass

    # ── العملاء ──
    def add_customer(self, name, phone="", email="", addr="", notes=""):
        c = self.connect()
        try:
            c.execute("INSERT INTO customers(name,phone,email,address,notes) VALUES(?,?,?,?,?)",
                      (name, phone or None, email, addr, notes))
            cid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            c.commit(); c.close()
            return True, cid
        except sqlite3.IntegrityError:
            c.close(); return False, "رقم الهاتف مستخدم"

    def customer_by_phone(self, p):
        c = self.connect()
        r = c.execute("SELECT * FROM customers WHERE phone=?",(p,)).fetchone()
        c.close(); return dict(r) if r else None

    def customers(self, term=""):
        c = self.connect()
        if term:
            t = f"%{term}%"
            r = [dict(x) for x in c.execute("SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY name",(t,t)).fetchall()]
        else:
            r = [dict(x) for x in c.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()]
        c.close(); return r

    # ── الأوامر ──
    def next_order_number(self):
        c = self.connect()
        n = c.execute("SELECT COUNT(*) FROM orders").fetchone()[0] + 1
        c.close()
        return f"EBN-{datetime.now():%Y%m%d}-{n:05d}"

    def create_order(self, cid, cname, cphone, items, sub, disc, tax, final, paid, pm, notes, cashier):
        c = self.connect()
        try:
            onum = self.next_order_number()
            change = max(0, paid - final)
            c.execute('''INSERT INTO orders(order_number,customer_id,customer_name,customer_phone,
                        subtotal,discount,tax,final_amount,paid,change_due,status,payment_method,notes,cashier)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                      (onum,cid,cname,cphone,sub,disc,tax,final,paid,change,'مكتمل',pm,notes,cashier))
            oid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            for it in items:
                c.execute('''INSERT INTO order_items(order_id,product_id,product_name,barcode,
                            quantity,price,cost,subtotal) VALUES(?,?,?,?,?,?,?,?)''',
                          (oid,it['product_id'],it['name'],it.get('barcode',''),
                           it['quantity'],it['price'],it.get('cost',0),it['subtotal']))
                c.execute("UPDATE products SET quantity=quantity-? WHERE id=?",
                          (it['quantity'], it['product_id']))
                row = c.execute("SELECT quantity FROM products WHERE id=?",(it['product_id'],)).fetchone()
                if row:
                    self.log_move(it['product_id'], it['name'], "بيع", it['quantity'],
                                  row['quantity']+it['quantity'], row['quantity'], onum, cashier)
            if cid:
                rate = float(self.get('loyalty_rate','0.01'))
                pts = int(final * rate)
                c.execute('''UPDATE customers SET total_purchases=total_purchases+?,
                            orders_count=orders_count+1,loyalty_points=loyalty_points+?,
                            last_purchase=CURRENT_TIMESTAMP WHERE id=?''',(final, pts, cid))
            c.commit(); c.close()
            self.log("فاتورة", f"{onum} | {final:.2f}", cashier)
            return True, onum, change
        except Exception as e:
            c.rollback(); c.close()
            return False, str(e), 0

    def orders(self, limit=500, search=""):
        c = self.connect()
        if search:
            t = f"%{search}%"
            r = [dict(x) for x in c.execute('''SELECT * FROM orders WHERE order_number LIKE ?
                OR customer_name LIKE ? OR customer_phone LIKE ? ORDER BY id DESC LIMIT ?''',
                (t,t,t,limit)).fetchall()]
        else:
            r = [dict(x) for x in c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?",(limit,)).fetchall()]
        c.close(); return r

    def order_items(self, oid):
        c = self.connect()
        r = [dict(x) for x in c.execute("SELECT * FROM order_items WHERE order_id=?",(oid,)).fetchall()]
        c.close(); return r

    def del_order(self, oid):
        c = self.connect()
        for it in c.execute("SELECT * FROM order_items WHERE order_id=?",(oid,)).fetchall():
            c.execute("UPDATE products SET quantity=quantity+? WHERE id=?",
                      (it['quantity'], it['product_id']))
        c.execute("DELETE FROM orders WHERE id=?",(oid,))
        c.commit(); c.close()

    # ── التقارير ──
    def summary(self):
        c = self.connect()
        r = {}
        r['total_sales']   = c.execute("SELECT COALESCE(SUM(final_amount),0) FROM orders").fetchone()[0]
        r['total_orders']  = c.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        r['total_custs']   = c.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        r['total_prods']   = c.execute("SELECT COUNT(*) FROM products WHERE is_active=1").fetchone()[0]
        r['low_stock']     = c.execute("SELECT COUNT(*) FROM products WHERE quantity<=min_stock AND is_active=1").fetchone()[0]
        td, mo = today(), datetime.now().strftime('%Y-%m')
        r['today_sales']   = c.execute("SELECT COALESCE(SUM(final_amount),0) FROM orders WHERE date(created_at)=?",(td,)).fetchone()[0]
        r['today_orders']  = c.execute("SELECT COUNT(*) FROM orders WHERE date(created_at)=?",(td,)).fetchone()[0]
        r['month_sales']   = c.execute("SELECT COALESCE(SUM(final_amount),0) FROM orders WHERE strftime('%Y-%m',created_at)=?",(mo,)).fetchone()[0]
        r['total_items']   = c.execute("SELECT COALESCE(SUM(quantity),0) FROM order_items").fetchone()[0]
        r['total_cost']    = c.execute("SELECT COALESCE(SUM(cost*quantity),0) FROM order_items").fetchone()[0]
        r['profit']        = r['total_sales'] - r['total_cost']
        r['expenses']      = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
        c.close(); return r

    def top_products(self, n=10):
        c = self.connect()
        r = [dict(x) for x in c.execute('''SELECT product_name, SUM(quantity) as qty,
            SUM(subtotal) as total FROM order_items GROUP BY product_name
            ORDER BY qty DESC LIMIT ?''',(n,)).fetchall()]
        c.close(); return r

    def top_customers(self, n=10):
        c = self.connect()
        r = [dict(x) for x in c.execute('''SELECT name,phone,total_purchases,orders_count,
            loyalty_points FROM customers ORDER BY total_purchases DESC LIMIT ?''',(n,)).fetchall()]
        c.close(); return r

    def sales_by_day(self, days=30):
        c = self.connect()
        r = [dict(x) for x in c.execute('''SELECT date(created_at) as d, COUNT(*) as cnt,
            COALESCE(SUM(final_amount),0) as total FROM orders
            WHERE created_at >= date('now',?) GROUP BY d ORDER BY d''',
            (f'-{days} days',)).fetchall()]
        c.close(); return r

    # ── النسخ الاحتياطية ──
    def backup(self, pw="", tag=""):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        sfx = f"_{tag}" if tag else ""
        out = self.backup_dir / f"ebnezz_{ts}{sfx}{BACKUP_EXT}"
        try:
            c = self.connect(); c.commit(); c.close()
            with open(self.path,'rb') as f: raw = f.read()
            enc = encrypt_bytes(raw, pw)
            with open(out,'wb') as f: f.write(enc)
            self.log("نسخة احتياطية", out.name)
            kb = out.stat().st_size / 1024
            return True, f"✅ {out.name}  ({kb:.1f} KB)"
        except Exception as e:
            return False, f"❌ {e}"

    def restore(self, src, pw=""):
        try:
            with open(src,'rb') as f: blob = f.read()
            raw = decrypt_bytes(blob, pw)
            if os.path.exists(self.path):
                shutil.copy2(self.path, self.backup_dir / f"pre_restore_{datetime.now():%Y%m%d_%H%M%S}.db")
            with open(self.path,'wb') as f: f.write(raw)
            self.log("استعادة", Path(src).name)
            return True, "✅ تم الاسترجاع"
        except ValueError as e:
            return False, f"❌ {e}"
        except Exception as e:
            return False, f"❌ {e}"

    def export_enc(self, path, pw=""):
        try:
            c = self.connect(); c.commit(); c.close()
            with open(self.path,'rb') as f: raw = f.read()
            enc = encrypt_bytes(raw, pw)
            with open(path,'wb') as f: f.write(enc)
            return True, f"✅ تم التصدير:\n{path}"
        except Exception as e:
            return False, f"❌ {e}"

    def list_backups(self):
        return [{'name':f.name,'size':f.stat().st_size,'path':str(f),'mtime':f.stat().st_mtime}
                for f in sorted(self.backup_dir.glob(f"*{BACKUP_EXT}"), reverse=True)]

    def cleanup_backups(self, days=7):
        cut = datetime.now() - timedelta(days=days)
        n = 0
        for f in self.backup_dir.glob(f"*{BACKUP_EXT}"):
            if datetime.fromtimestamp(f.stat().st_mtime) < cut:
                f.unlink(); n += 1
        return n

    def reset(self):
        try:
            c = self.connect()
            for t in ['order_items','orders','products','customers','stock_moves','expenses','logs']:
                c.execute(f"DELETE FROM {t}")
            c.execute("DELETE FROM sqlite_sequence WHERE name NOT IN ('users','settings')")
            c.commit(); c.close()
            self.log("إعادة ضبط","حذف كامل")
            return True, "✅ تم إعادة الضبط"
        except Exception as e: return False, str(e)

    # ── المصاريف ──
    def add_expense(self, cat, amt, desc, user=""):
        c = self.connect()
        c.execute("INSERT INTO expenses(category,amount,description,username) VALUES(?,?,?,?)",
                  (cat,amt,desc,user))
        c.commit(); c.close()

    def expenses_list(self):
        c = self.connect()
        r = [dict(x) for x in c.execute("SELECT * FROM expenses ORDER BY id DESC LIMIT 500").fetchall()]
        c.close(); return r

    # ── السجلات ──
    def logs(self, limit=500):
        c = self.connect()
        r = [dict(x) for x in c.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?",(limit,)).fetchall()]
        c.close(); return r

    def clear_logs(self):
        c = self.connect()
        c.execute("DELETE FROM logs")
        c.commit(); c.close()

    # ── تصدير ──
    def export_orders_csv(self, p):
        rows = self.orders(limit=999999)
        with open(p,'w',newline='',encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['رقم الفاتورة','العميل','الهاتف','الإجمالي','الخصم','الضريبة','الصافي','الدفع','التاريخ'])
            for r in rows:
                w.writerow([r['order_number'],r['customer_name'],r['customer_phone'],
                            r['subtotal'],r['discount'],r['tax'],r['final_amount'],
                            r['payment_method'],r['created_at']])

    def export_products_csv(self, p):
        rows = self.products(only_active=False)
        with open(p,'w',newline='',encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['ID','الباركود','الاسم','الفئة','السعر','التكلفة','المخزون'])
            for r in rows:
                w.writerow([r['id'],r['barcode'],r['name'],r['category'],
                            r['price'],r['cost'],r['quantity']])


# ═══════════════════════════════════════════════════════════════════════════
#  🎬 شاشة البداية (Splash)
# ═══════════════════════════════════════════════════════════════════════════
class Splash:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg=CLR['darkest'])
        w, h = 520, 380
        x = (self.root.winfo_screenwidth()//2) - w//2
        y = (self.root.winfo_screenheight()//2) - h//2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(self.root, text="🛍️", font=('Arial', 68),
                 bg=CLR['darkest'], fg=CLR['primary']).pack(pady=(35,5))
        tk.Label(self.root, text=APP_NAME, font=('Arial', 34, 'bold'),
                 bg=CLR['darkest'], fg='white').pack()
        tk.Label(self.root, text=APP_SUBTITLE, font=('Arial', 12),
                 bg=CLR['darkest'], fg=CLR['text_muted']).pack(pady=(0,20))
        tk.Label(self.root, text=f"v{APP_VERSION}  ·  {APP_EDITION}",
                 font=('Arial', 10), bg=CLR['darkest'], fg=CLR['primary_light']).pack()

        self.bar = ttk.Progressbar(self.root, length=340, mode='indeterminate')
        self.bar.pack(pady=25)
        self.bar.start(12)

        tk.Label(self.root, text=f"Developed by {DEVELOPER}",
                 font=('Arial', 9, 'italic'), bg=CLR['darkest'],
                 fg=CLR['text_muted']).pack(side='bottom', pady=15)

    def show(self, ms=2200):
        self.root.after(ms, self.root.destroy)
        self.root.mainloop()


# ═══════════════════════════════════════════════════════════════════════════
#  🔓 شاشة الدخول
# ═══════════════════════════════════════════════════════════════════════════
class LoginWindow:
    def __init__(self):
        self.db = Database()
        self.user = None
        self.root = tk.Tk()
        self.root.title(f"تسجيل الدخول — {APP_NAME}")
        self.root.geometry("500x680")
        self.root.configure(bg=CLR['darkest'])
        self.root.resizable(False, False)
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth()//2) - 250
        y = (self.root.winfo_screenheight()//2) - 340
        self.root.geometry(f"500x680+{x}+{y}")
        self._build()

    def _build(self):
        tk.Label(self.root, text="🛍️", font=('Arial', 72),
                 bg=CLR['darkest'], fg=CLR['primary']).pack(pady=(45,5))
        tk.Label(self.root, text=self.db.get('shop_name', APP_NAME),
                 font=('Arial', 32, 'bold'), bg=CLR['darkest'], fg='white').pack()
        tk.Label(self.root, text=APP_SUBTITLE, font=('Arial', 12),
                 bg=CLR['darkest'], fg=CLR['text_muted']).pack(pady=(0,30))

        card = tk.Frame(self.root, bg=CLR['dark'], padx=38, pady=32)
        card.pack(padx=55, fill='x')

        tk.Label(card, text="👤  اسم المستخدم", font=('Arial', 11, 'bold'),
                 bg=CLR['dark'], fg='white').pack(anchor='e')
        self.u = tk.Entry(card, font=('Arial', 13), relief=tk.FLAT,
                          bg=CLR['darkest'], fg='white', insertbackground='white',
                          justify='right')
        self.u.pack(fill='x', pady=(6,18), ipady=11)
        self.u.insert(0, "admin")

        tk.Label(card, text="🔑  كلمة المرور", font=('Arial', 11, 'bold'),
                 bg=CLR['dark'], fg='white').pack(anchor='e')
        self.p = tk.Entry(card, font=('Arial', 13), relief=tk.FLAT,
                          bg=CLR['darkest'], fg='white', insertbackground='white',
                          show='●', justify='right')
        self.p.pack(fill='x', pady=(6,24), ipady=11)
        self.p.bind('<Return>', lambda e: self._login())

        tk.Button(card, text="🔓   تسجيل الدخول", bg=CLR['primary'], fg='white',
                  font=('Arial', 14, 'bold'), relief=tk.FLAT, cursor='hand2',
                  activebackground=CLR['primary_dark'],
                  command=self._login).pack(fill='x', ipady=13)

        tk.Label(self.root, text="الافتراضي: admin / admin", font=('Arial', 9),
                 bg=CLR['darkest'], fg=CLR['text_muted']).pack(pady=14)
        tk.Label(self.root, text=f"Developed by {DEVELOPER}  ·  {COPYRIGHT}",
                 font=('Arial', 9), bg=CLR['darkest'], fg=CLR['text_muted']).pack(side='bottom', pady=15)
        self.p.focus()

    def _login(self):
        u, p = self.u.get().strip(), self.p.get()
        if not u or not p:
            return messagebox.showwarning("تحذير", "أكمل البيانات!")
        usr = self.db.login(u, p)
        if usr:
            self.user = usr
            self.db.log("دخول", "", u)
            self.root.destroy()
        else:
            messagebox.showerror("خطأ", "❌ بيانات دخول خاطئة!")
            self.p.delete(0, tk.END)

    def run(self):
        self.root.mainloop()
        return self.user


# ═══════════════════════════════════════════════════════════════════════════
#  🏠 التطبيق الرئيسي — Sidebar + Pages
# ═══════════════════════════════════════════════════════════════════════════
class MainApp:
    def __init__(self, root, user, db):
        self.root = root
        self.user = user
        self.db = db
        self.cart = []
        self._pmap = {}
        self.pages = {}
        self.active = None
        self.cur = db.get('currency','ج.م')

        self.root.title(f"{db.get('shop_name', APP_NAME)} — نظام إدارة المبيعات v{APP_VERSION}")
        self.root.geometry("1480x900")
        self.root.configure(bg=CLR['light'])
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._style()
        self._layout()
        self._show('dashboard')
        self.root.after(1500, self._auto_backup_check)

    # ── Styles ──
    def _style(self):
        s = ttk.Style(); s.theme_use('clam')
        s.configure('TCombobox', padding=6, font=('Arial',10))
        s.configure('Treeview', font=('Arial',10), rowheight=30, background='white',
                    fieldbackground='white', borderwidth=0)
        s.configure('Treeview.Heading', font=('Arial',10,'bold'),
                    background=CLR['dark'], foreground='white', relief='flat')
        s.map('Treeview.Heading', background=[('active', CLR['primary'])])
        s.map('Treeview', background=[('selected', CLR['primary_light'])],
              foreground=[('selected', 'white')])
        s.configure('TNotebook', background=CLR['light'], borderwidth=0)
        s.configure('TNotebook.Tab', font=('Arial',11,'bold'), padding=[18,10])

    # ── Layout ──
    def _layout(self):
        # Sidebar
        self.sb = tk.Frame(self.root, bg=CLR['sidebar'], width=230)
        self.sb.pack(side='right', fill='y')
        self.sb.pack_propagate(False)

        # Logo
        logo = tk.Frame(self.sb, bg=CLR['sidebar'], height=110)
        logo.pack(fill='x'); logo.pack_propagate(False)
        tk.Label(logo, text="🛍️", font=('Arial',26), bg=CLR['sidebar'], fg=CLR['primary']).pack(pady=(15,2))
        tk.Label(logo, text=self.db.get('shop_name', APP_NAME),
                 font=('Arial',15,'bold'), bg=CLR['sidebar'], fg='white').pack()
        tk.Label(logo, text=f"v{APP_VERSION} · {APP_EDITION}",
                 font=('Arial',8), bg=CLR['sidebar'], fg=CLR['text_muted']).pack()

        # Separator
        tk.Frame(self.sb, bg='#1e293b', height=1).pack(fill='x', padx=15, pady=8)

        # Nav items
        self.nav_items = [
            ('dashboard',  '🏠', 'لوحة التحكم'),
            ('pos',        '🛒', 'نقطة البيع'),
            ('orders',     '📋', 'الفواتير'),
            ('products',   '📦', 'المنتجات'),
            ('customers',  '👥', 'العملاء'),
            ('reports',    '📊', 'التقارير'),
            ('logs',       '📜', 'السجلات'),
            ('users',      '🔐', 'المستخدمون'),
            ('settings',   '⚙️', 'الإعدادات'),
        ]
        self.nav_btns = {}
        for key, icon, label in self.nav_items:
            b = tk.Button(self.sb, text=f"  {icon}   {label}",
                          bg=CLR['sidebar'], fg=CLR['sidebar_text'],
                          font=('Arial',11,'bold'), relief=tk.FLAT,
                          anchor='e', padx=18, pady=12, cursor='hand2',
                          activebackground=CLR['sidebar_hover'],
                          activeforeground='white',
                          command=lambda k=key: self._show(k))
            b.pack(fill='x', padx=8, pady=1)
            self.nav_btns[key] = b

        # Bottom user info
        bottom = tk.Frame(self.sb, bg=CLR['sidebar'])
        bottom.pack(side='bottom', fill='x', pady=10)
        tk.Frame(bottom, bg='#1e293b', height=1).pack(fill='x', padx=15, pady=8)
        tk.Label(bottom, text=f"👤 {self.user.get('full_name') or self.user['username']}",
                 font=('Arial',10,'bold'), bg=CLR['sidebar'], fg='white').pack()
        tk.Label(bottom, text=f"🎭 {self.user['role']}",
                 font=('Arial',9), bg=CLR['sidebar'], fg=CLR['text_muted']).pack(pady=(2,8))
        tk.Button(bottom, text="🚪  تسجيل خروج", bg='#1e293b', fg='#f87171',
                  font=('Arial',10,'bold'), relief=tk.FLAT, cursor='hand2',
                  command=self._close).pack(fill='x', padx=15, pady=(0,8), ipady=6)

        # Main container
        self.main = tk.Frame(self.root, bg=CLR['light'])
        self.main.pack(side='left', fill='both', expand=True)

        # Topbar
        self.top = tk.Frame(self.main, bg='white', height=60)
        self.top.pack(fill='x'); self.top.pack_propagate(False)
        self.top_title = tk.Label(self.top, text="", font=('Arial',15,'bold'),
                                   bg='white', fg=CLR['text_dark'])
        self.top_title.pack(side='right', padx=25, pady=15)
        self.clock = tk.Label(self.top, text="", font=('Arial',10),
                               bg='white', fg=CLR['text_light'])
        self.clock.pack(side='left', padx=20)
        self._tick()
        tk.Frame(self.main, bg=CLR['border'], height=1).pack(fill='x')

        # Content area
        self.content = tk.Frame(self.main, bg=CLR['light'])
        self.content.pack(fill='both', expand=True, padx=15, pady=15)

        # Status bar
        self.status = tk.Frame(self.main, bg=CLR['dark'], height=28)
        self.status.pack(fill='x', side='bottom'); self.status.pack_propagate(False)
        self.status_lbl = tk.Label(self.status, text="🟢 جاهز",
                                    font=('Arial',9), bg=CLR['dark'], fg='white')
        self.status_lbl.pack(side='right', padx=15)
        tk.Label(self.status, text=f"Developed by {DEVELOPER}",
                 font=('Arial',9,'italic'), bg=CLR['dark'], fg=CLR['text_muted']).pack(side='left', padx=15)

    def _tick(self):
        self.clock.config(text=f"📅  {datetime.now():%Y-%m-%d   ⏰  %H:%M:%S}")
        self.root.after(1000, self._tick)

    def say(self, msg, ms=4000):
        self.status_lbl.config(text=f"✅ {msg}")
        self.root.after(ms, lambda: self.status_lbl.config(text="🟢 جاهز"))

    def _show(self, key):
        if self.active == key: return
        for k, b in self.nav_btns.items():
            if k == key:
                b.config(bg=CLR['sidebar_active'], fg='white')
            else:
                b.config(bg=CLR['sidebar'], fg=CLR['sidebar_text'])
        # clear
        for w in self.content.winfo_children(): w.destroy()
        # title
        titles = {k:(i,l) for k,i,l in self.nav_items}
        self.top_title.config(text=f"{titles[key][0]}  {titles[key][1]}")
        # build page
        builder = getattr(self, f"_page_{key}", None)
        if builder: builder()
        self.active = key

    # ═══════════════════════════════════════════════════════════════
    #  🏠 لوحة التحكم
    # ═══════════════════════════════════════════════════════════════
    def _page_dashboard(self):
        f = self.content
        s = self.db.summary()

        # Top cards
        cards_frame = tk.Frame(f, bg=CLR['light'])
        cards_frame.pack(fill='x', pady=(0,12))
        cards = [
            ("💰 إجمالي المبيعات", money(s['total_sales'], self.cur), CLR['primary']),
            ("📅 مبيعات اليوم",   money(s['today_sales'], self.cur), CLR['secondary']),
            ("📋 الفواتير",       f"{s['total_orders']:,}", CLR['warning']),
            ("👥 العملاء",        f"{s['total_custs']:,}", CLR['accent']),
            ("📦 المنتجات",       f"{s['total_prods']:,}", CLR['info']),
            ("⚠️ مخزون قليل",     f"{s['low_stock']:,}", CLR['danger']),
        ]
        for i,(t, v, c) in enumerate(cards):
            card = tk.Frame(cards_frame, bg=c, height=120)
            card.grid(row=0, column=i, padx=4, sticky='nsew')
            cards_frame.columnconfigure(i, weight=1)
            tk.Label(card, text=t, font=('Arial',10,'bold'),
                     bg=c, fg='white').pack(pady=(16,4))
            tk.Label(card, text=v, font=('Arial',17,'bold'),
                     bg=c, fg='white').pack(pady=5)

        # Second row: profit + chart
        row2 = tk.Frame(f, bg=CLR['light'])
        row2.pack(fill='both', expand=True)

        # Profit card
        prof = tk.Frame(row2, bg='white', highlightthickness=1,
                        highlightbackground=CLR['border'])
        prof.pack(side='right', fill='both', expand=True, padx=(0,6))
        tk.Label(prof, text="📈 تحليل الأرباح", font=('Arial',13,'bold'),
                 bg='white', fg=CLR['text_dark']).pack(pady=(15,10))
        for lbl, val, col in [
            ("إجمالي المبيعات", money(s['total_sales'], self.cur), CLR['primary']),
            ("تكلفة البضاعة",  money(s['total_cost'], self.cur), CLR['text_light']),
            ("المصاريف",       money(s['expenses'], self.cur), CLR['warning']),
            ("صافي الربح",     money(s['profit'], self.cur), CLR['success']),
        ]:
            r = tk.Frame(prof, bg='white')
            r.pack(fill='x', padx=25, pady=5)
            tk.Label(r, text=lbl, font=('Arial',11), bg='white',
                     fg=CLR['text']).pack(side='right')
            tk.Label(r, text=val, font=('Arial',13,'bold'), bg='white',
                     fg=col).pack(side='left')

        # Chart
        chart = tk.Frame(row2, bg='white', highlightthickness=1,
                         highlightbackground=CLR['border'])
        chart.pack(side='left', fill='both', expand=True, padx=(6,0))
        tk.Label(chart, text="📊 مبيعات آخر 7 أيام", font=('Arial',13,'bold'),
                 bg='white', fg=CLR['text_dark']).pack(pady=(15,5))
        self._draw_chart(chart, self.db.sales_by_day(7))

        # Top products
        top_frame = tk.Frame(f, bg='white', highlightthickness=1,
                             highlightbackground=CLR['border'])
        top_frame.pack(fill='both', expand=True, pady=(12,0))
        tk.Label(top_frame, text="🏆 أفضل 5 منتجات مبيعاً", font=('Arial',12,'bold'),
                 bg='white', fg=CLR['text_dark']).pack(pady=10, anchor='e', padx=20)
        cols = ('المنتج','الكمية','الإيرادات')
        tree = ttk.Treeview(top_frame, columns=cols, show='headings', height=5)
        for c,w in zip(cols,[400,150,200]):
            tree.heading(c,text=c); tree.column(c,width=w,anchor='center')
        tree.pack(fill='x', padx=20, pady=(0,15))
        for p in self.db.top_products(5):
            tree.insert('', 'end', values=(p['product_name'], p['qty'],
                                            money(p['total'], self.cur)))

    def _draw_chart(self, parent, data):
        cv = tk.Canvas(parent, bg='white', height=200, highlightthickness=0)
        cv.pack(fill='both', expand=True, padx=20, pady=(0,15))
        cv.update_idletasks()
        W = cv.winfo_reqwidth() or 500
        H = 200
        if not data:
            cv.create_text(W//2, H//2, text="لا توجد بيانات", fill=CLR['text_muted'],
                           font=('Arial',11))
            return
        maxv = max(d['total'] for d in data) or 1
        n = len(data)
        bw = max(20, (W - 60) // max(n,1) - 8)
        pad = 30
        for i, d in enumerate(data):
            x0 = pad + i * (bw + 8)
            x1 = x0 + bw
            h = int((d['total'] / maxv) * (H - 60))
            y0 = H - 30 - h
            y1 = H - 30
            cv.create_rectangle(x0, y0, x1, y1, fill=CLR['primary'], outline='')
            cv.create_text((x0+x1)//2, y0-8, text=f"{d['total']:.0f}",
                           font=('Arial',8), fill=CLR['text_dark'])
            lbl = d['d'][5:]
            cv.create_text((x0+x1)//2, H-15, text=lbl,
                           font=('Arial',8), fill=CLR['text_light'])

    # ═══════════════════════════════════════════════════════════════
    #  🛒 نقطة البيع (POS)
    # ═══════════════════════════════════════════════════════════════
    def _page_pos(self):
        f = self.content
        # Two columns: right = cart, left = search + products
        right = tk.Frame(f, bg='white', highlightthickness=1,
                         highlightbackground=CLR['border'])
        right.pack(side='right', fill='both', expand=True, padx=(0,6))
        left = tk.Frame(f, bg='white', highlightthickness=1,
                        highlightbackground=CLR['border'])
        left.pack(side='left', fill='both', expand=True, padx=(6,0))

        # ── Right: cart
        tk.Label(right, text="🛒  سلة المشتريات", font=('Arial',14,'bold'),
                 bg='white', fg=CLR['text_dark']).pack(pady=(12,6), anchor='e', padx=20)

        # Customer row
        cust_row = tk.Frame(right, bg='white')
        cust_row.pack(fill='x', padx=20, pady=6)
        tk.Label(cust_row, text="👤 العميل:", bg='white',
                 font=('Arial',10,'bold')).pack(side='right')
        self.pos_cust = tk.Entry(cust_row, font=('Arial',11), justify='right', width=22)
        self.pos_cust.pack(side='right', padx=6, ipady=5)
        tk.Label(cust_row, text="📞 الهاتف:", bg='white',
                 font=('Arial',10,'bold')).pack(side='right', padx=(15,0))
        self.pos_phone = tk.Entry(cust_row, font=('Arial',11), justify='right', width=15)
        self.pos_phone.pack(side='right', padx=6, ipady=5)

        # Cart tree
        cols = ('الإجمالي','الكمية','السعر','المنتج')
        self.pos_tree = ttk.Treeview(right, columns=cols, show='headings', height=10)
        for c,w in zip(cols,[130,70,100,300]):
            self.pos_tree.heading(c,text=c); self.pos_tree.column(c,width=w,anchor='center')
        self.pos_tree.pack(fill='both', expand=True, padx=20, pady=8)
        self.pos_tree.bind('<Double-1>', lambda e: self._pos_remove())

        # Totals
        tot = tk.Frame(right, bg=CLR['darkest'])
        tot.pack(fill='x', padx=20, pady=(0,8))

        def totrow(lbl, key, color='white'):
            r = tk.Frame(tot, bg=CLR['darkest'])
            r.pack(fill='x', padx=15, pady=3)
            tk.Label(r, text=lbl, font=('Arial',11), bg=CLR['darkest'],
                     fg=CLR['text_muted']).pack(side='right')
            v = tk.Label(r, text="0.00", font=('Arial',12,'bold'),
                         bg=CLR['darkest'], fg=color)
            v.pack(side='left')
            setattr(self, f"_pos_{key}", v)

        totrow("المجموع:", "sub")
        totrow("الخصم:", "disc", CLR['warning'])
        totrow("الضريبة:", "tax", CLR['info'])
        totrow("الصافي:", "final", CLR['primary_light'])

        # Actions
        act = tk.Frame(right, bg='white')
        act.pack(fill='x', padx=20, pady=(0,15))
        self._btn(act, "💾 حفظ وطباعة", CLR['primary'], self._pos_save, 16).pack(side='right', fill='x', expand=True, padx=3)
        self._btn(act, "🗑️ إلغاء", CLR['danger'], self._pos_clear, 12).pack(side='right', padx=3)

        # ── Left: search + product list
        tk.Label(left, text="🔍  البحث عن منتج", font=('Arial',14,'bold'),
                 bg='white', fg=CLR['text_dark']).pack(pady=(12,6), anchor='e', padx=20)

        search_row = tk.Frame(left, bg='white')
        search_row.pack(fill='x', padx=20, pady=6)
        self.pos_bc = tk.Entry(search_row, font=('Arial',14), justify='right')
        self.pos_bc.pack(side='right', fill='x', expand=True, ipady=8)
        self.pos_bc.bind('<Return>', lambda e: self._pos_barcode_add())
        self._btn(search_row, "➕", CLR['primary'], self._pos_barcode_add, 10).pack(side='left', padx=4)

        tk.Label(left, text="أو امسح الباركود واضغط Enter", font=('Arial',9,'italic'),
                 bg='white', fg=CLR['text_muted']).pack(anchor='e', padx=22)

        # Products grid
        pcols = ('السعر','المخزون','المنتج')
        self.pos_prod = ttk.Treeview(left, columns=pcols, show='headings', height=16)
        for c,w in zip(pcols,[100,90,260]):
            self.pos_prod.heading(c,text=c); self.pos_prod.column(c,width=w,anchor='center')
        self.pos_prod.pack(fill='both', expand=True, padx=20, pady=10)
        self.pos_prod.bind('<Double-1>', lambda e: self._pos_add_from_list())

        # Search filter
        self.pos_filter = tk.Entry(left, font=('Arial',10), justify='right')
        self.pos_filter.pack(fill='x', padx=20, pady=(0,10), ipady=5)
        self.pos_filter.bind('<KeyRelease>', lambda e: self._pos_reload_products())
        self.pos_filter.insert(0, "اكتب للبحث هنا...")
        self.pos_filter.bind('<FocusIn>', lambda e: self.pos_filter.delete(0,'end') if self.pos_filter.get()=="اكتب للبحث هنا..." else None)

        self.pos_bc.focus()
        self._pos_reload_products()

    def _pos_reload_products(self, term=None):
        t = self.pos_filter.get() if term is None else term
        if t == "اكتب للبحث هنا...": t = ""
        for i in self.pos_prod.get_children(): self.pos_prod.delete(i)
        for p in self.db.products(t):
            self.pos_prod.insert('', 'end',
                values=(money(p['price'], ''), p['quantity'], p['name']),
                tags=(str(p['id']),))

    def _pos_barcode_add(self):
        bc = self.pos_bc.get().strip()
        if not bc: return
        p = self.db.by_barcode(bc)
        if not p:
            # try by name
            prods = self.db.products(bc)
            if len(prods) == 1: p = prods[0]
            else:
                messagebox.showwarning("غير موجود", f"لا يوجد منتج بالباركود: {bc}")
                self.pos_bc.delete(0,'end'); return
        if p['quantity'] <= 0:
            messagebox.showerror("خطأ", f"⚠️ {p['name']} غير متوفر!")
            self.pos_bc.delete(0,'end'); return
        # add
        for i, it in enumerate(self.cart):
            if it['product_id'] == p['id']:
                if it['quantity'] + 1 > p['quantity']:
                    messagebox.showerror("خطأ","الكمية غير متوفرة"); self.pos_bc.delete(0,'end'); return
                it['quantity'] += 1
                it['subtotal'] = it['quantity'] * it['price']
                break
        else:
            self.cart.append({'product_id':p['id'],'name':p['name'],'barcode':p['barcode'],
                              'price':p['price'],'cost':p['cost'],'quantity':1,
                              'subtotal':p['price']})
        self.pos_bc.delete(0,'end')
        self._pos_refresh()

    def _pos_add_from_list(self):
        s = self.pos_prod.selection()
        if not s: return
        pid = int(self.pos_prod.item(s[0])['tags'][0])
        p = self.db.product(pid)
        if not p: return
        if p['quantity'] <= 0:
            return messagebox.showerror("خطأ", f"⚠️ {p['name']} غير متوفر!")
        for it in self.cart:
            if it['product_id'] == p['id']:
                if it['quantity'] + 1 > p['quantity']:
                    return messagebox.showerror("خطأ","الكمية غير متوفرة")
                it['quantity'] += 1
                it['subtotal'] = it['quantity'] * it['price']
                break
        else:
            self.cart.append({'product_id':p['id'],'name':p['name'],'barcode':p['barcode'],
                              'price':p['price'],'cost':p['cost'],'quantity':1,
                              'subtotal':p['price']})
        self._pos_refresh()

    def _pos_remove(self):
        s = self.pos_tree.selection()
        if not s: return
        idx = self.pos_tree.index(s[0])
        self.cart.pop(idx)
        self._pos_refresh()

    def _pos_refresh(self):
        for i in self.pos_tree.get_children(): self.pos_tree.delete(i)
        sub = 0
        for it in self.cart:
            sub += it['subtotal']
            self.pos_tree.insert('', 'end',
                values=(money(it['subtotal'],''), it['quantity'],
                        money(it['price'],''), it['name']))
        tax_rate = float(self.db.get('tax_rate','0'))
        tax = sub * tax_rate / 100
        # Auto discount = 0 for now
        disc = 0
        final = sub - disc + tax
        self._pos_sub.config(text=money(sub, self.cur))
        self._pos_disc.config(text=money(disc, self.cur))
        self._pos_tax.config(text=money(tax, self.cur))
        self._pos_final.config(text=money(final, self.cur))

    def _pos_clear(self):
        if self.cart and not messagebox.askyesno("تأكيد","إلغاء الفاتورة؟"): return
        self.cart = []
        self.pos_cust.delete(0,'end'); self.pos_phone.delete(0,'end')
        self._pos_refresh()

    def _pos_save(self):
        if not self.cart:
            return messagebox.showwarning("تحذير","السلة فاضية!")
        cname = self.pos_cust.get().strip() or "عميل نقدي"
        cphone = self.pos_phone.get().strip()
        sub = sum(i['subtotal'] for i in self.cart)
        tax_rate = float(self.db.get('tax_rate','0'))
        tax = sub * tax_rate / 100
        disc = 0
        final = sub - disc + tax

        # Ask for paid amount
        paid = simpledialog.askfloat("الدفع", f"المطلوب: {money(final, self.cur)}\nالمدفوع:",
                                      initialvalue=final, parent=self.root)
        if paid is None: return
        if paid < final:
            return messagebox.showerror("خطأ", "المدفوع أقل من المطلوب!")

        # Customer
        cid = None
        if cphone:
            existing = self.db.customer_by_phone(cphone)
            if existing: cid = existing['id']
            else:
                ok, cid = self.db.add_customer(cname, cphone)
                if not ok: cid = None

        # Payment method
        pm = simpledialog.askstring("طريقة الدفع","كاش / فيزا / محفظة:",
                                     initialvalue="كاش", parent=self.root) or "كاش"

        ok, onum, change = self.db.create_order(
            cid, cname, cphone, self.cart, sub, disc, tax, final, paid, pm, "",
            self.user['username'])
        if not ok:
            return messagebox.showerror("خطأ", str(onum))

        # Show receipt
        order = {'order_number':onum, 'customer_name':cname, 'customer_phone':cphone,
                 'subtotal':sub, 'discount':disc, 'tax':tax, 'final_amount':final,
                 'paid':paid, 'change_due':change, 'payment_method':pm,
                 'created_at':datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        self._show_receipt(order, self.cart)

        self.cart = []
        self.pos_cust.delete(0,'end'); self.pos_phone.delete(0,'end')
        self._pos_refresh(); self._pos_reload_products()
        self.say(f"✅ فاتورة {onum} — الباقي {money(change, self.cur)}")

    def _show_receipt(self, order, items):
        win = tk.Toplevel(self.root)
        win.title(f"فاتورة {order['order_number']}")
        win.geometry("440x620")
        win.configure(bg='white')
        win.transient(self.root)

        settings = self.db.all_settings()
        txt = tk.Text(win, font=('Courier New', 10), bg='white',
                      relief=tk.FLAT, padx=15, pady=15)
        txt.pack(fill='both', expand=True)
        txt.insert('1.0', self._build_receipt(order, items, settings))
        txt.config(state='disabled')

        btns = tk.Frame(win, bg='white')
        btns.pack(fill='x', padx=15, pady=10)

        def save():
            p = filedialog.asksaveasfilename(defaultextension=".txt",
                initialfile=f"{order['order_number']}.txt",
                filetypes=[("نص","*.txt")])
            if p:
                with open(p,'w',encoding='utf-8') as f:
                    f.write(txt.get('1.0','end'))
                messagebox.showinfo("تم", f"✅ {p}")

        self._btn(btns, "🖨️ طباعة", CLR['primary'], lambda: win.destroy(), 12).pack(side='right', padx=3)
        self._btn(btns, "💾 حفظ", CLR['secondary'], save, 12).pack(side='right', padx=3)

    def _build_receipt(self, order, items, settings):
        W = 44
        line = lambda c='─': c*W
        cen = lambda t: t.center(W)
        L = []
        L.append(line('═'))
        L.append(cen(settings.get('shop_name', APP_NAME)))
        if settings.get('shop_phone'): L.append(cen(f"☎ {settings['shop_phone']}"))
        if settings.get('shop_address'): L.append(cen(settings['shop_address']))
        L.append(line('═'))
        L.append(f"رقم الفاتورة: {order['order_number']}")
        L.append(f"التاريخ: {fmt_dt(order['created_at'])}")
        L.append(f"العميل: {order.get('customer_name') or 'نقدي'}")
        if order.get('customer_phone'): L.append(f"الهاتف: {order['customer_phone']}")
        L.append(line())
        L.append(f"{'الإجمالي':<10}{'الكمية':<7}{'السعر':<9}{'المنتج'}")
        L.append(line())
        for it in items:
            name = (it['name'][:14] + '…') if len(it['name']) > 15 else it['name']
            L.append(f"{it['subtotal']:<10.2f}{it['quantity']:<7}{it['price']:<9.2f}{name}")
        L.append(line())
        L.append(f"{'المجموع:':<25}{order['subtotal']:>12.2f}")
        if order.get('discount'): L.append(f"{'الخصم:':<25}{order['discount']:>12.2f}")
        if order.get('tax'):      L.append(f"{'الضريبة:':<25}{order['tax']:>12.2f}")
        L.append(line('═'))
        L.append(f"{'الصافي:':<22}{order['final_amount']:>15.2f}")
        L.append(f"{'المدفوع:':<22}{order['paid']:>15.2f}")
        if order.get('change_due'): L.append(f"{'الباقي:':<22}{order['change_due']:>15.2f}")
        L.append(line('═'))
        L.append(cen(order.get('payment_method','كاش')))
        L.append(cen(settings.get('receipt_footer','شكراً لتعاملكم معنا')))
        L.append(line('═'))
        L.append(cen(f"برنامج {APP_NAME} — {DEVELOPER}"))
        return "\n".join(L)

    # ═══════════════════════════════════════════════════════════════
    #  📋 الفواتير
    # ═══════════════════════════════════════════════════════════════
    def _page_orders(self):
        f = self.content
        bar = tk.Frame(f, bg='white', highlightthickness=1,
                       highlightbackground=CLR['border'])
        bar.pack(fill='x', pady=(0,10))
        tk.Label(bar, text="🔍", bg='white', font=('Arial',14)).pack(side='right', padx=(15,5))
        self.ord_search = tk.Entry(bar, font=('Arial',11), justify='right', width=40)
        self.ord_search.pack(side='right', pady=10, ipady=5)
        self.ord_search.bind('<KeyRelease>', lambda e: self._load_orders())
        self._btn(bar, "🔄 تحديث", CLR['secondary'], self._load_orders, 10).pack(side='left', padx=10, pady=10)
        self._btn(bar, "📤 تصدير CSV", CLR['accent'], self._export_orders_csv, 10).pack(side='left', padx=5, pady=10)

        cols = ('ID','رقم الفاتورة','العميل','الهاتف','الإجمالي','الدفع','التاريخ','الكاشير')
        self.ord_tree = ttk.Treeview(f, columns=cols, show='headings', height=22)
        for c,w in zip(cols,[50,160,150,120,130,110,150,120]):
            self.ord_tree.heading(c,text=c); self.ord_tree.column(c,width=w,anchor='center')
        self.ord_tree.pack(fill='both', expand=True)
        self.ord_tree.bind('<Double-1>', lambda e: self._view_order())
        self.ord_tree.bind('<Delete>', lambda e: self._del_order())

        self._load_orders()

    def _load_orders(self):
        for i in self.ord_tree.get_children(): self.ord_tree.delete(i)
        for o in self.db.orders(search=self.ord_search.get().strip()):
            self.ord_tree.insert('', 'end', values=(
                o['id'], o['order_number'], o['customer_name'] or 'نقدي',
                o['customer_phone'] or '-', money(o['final_amount'],self.cur),
                o['payment_method'], fmt_dt(o['created_at']), o['cashier'] or '-'))

    def _view_order(self):
        s = self.ord_tree.selection()
        if not s: return
        oid = self.ord_tree.item(s[0])['values'][0]
        # find order
        order = None
        for o in self.db.orders(limit=9999):
            if o['id'] == oid: order = o; break
        if not order: return
        items = self.db.order_items(oid)
        items_fmt = [{'name':i['product_name'],'quantity':i['quantity'],
                      'price':i['price'],'subtotal':i['subtotal']} for i in items]
        self._show_receipt(order, items_fmt)

    def _del_order(self):
        s = self.ord_tree.selection()
        if not s: return
        oid = self.ord_tree.item(s[0])['values'][0]
        if messagebox.askyesno("تأكيد","حذف الفاتورة؟ (سيتم إرجاع المخزون)"):
            self.db.del_order(oid)
            self.db.log("حذف فاتورة", f"ID:{oid}", self.user['username'])
            self._load_orders()
            self.say("تم الحذف")

    def _export_orders_csv(self):
        p = filedialog.asksaveasfilename(defaultextension=".csv",
            initialfile=f"orders_{today()}.csv", filetypes=[("CSV","*.csv")])
        if p:
            self.db.export_orders_csv(p)
            messagebox.showinfo("تم", f"✅ {p}")

    # ═══════════════════════════════════════════════════════════════
    #  📦 المنتجات
    # ═══════════════════════════════════════════════════════════════
    def _page_products(self):
        f = self.content

        # Form
        form = tk.Frame(f, bg='white', highlightthickness=1,
                        highlightbackground=CLR['border'])
        form.pack(fill='x', pady=(0,10))
        tk.Label(form, text="➕  إضافة / تعديل منتج", font=('Arial',13,'bold'),
                 bg='white', fg=CLR['primary']).grid(row=0, column=0, columnspan=8,
                                                       pady=(12,8), sticky='e', padx=20)

        fields = [("الاسم",'name',22), ("الباركود",'barcode',18),
                  ("الفئة",'cat',15), ("سعر البيع",'price',12),
                  ("التكلفة",'cost',12), ("الكمية",'qty',10),
                  ("حد التنبيه",'minq',10), ("الوحدة",'unit',10)]
        self.prod_e = {}
        for i,(lbl, key, w) in enumerate(fields):
            col = i % 4
            row = 1 + i // 4
            tk.Label(form, text=f"{lbl}:", bg='white',
                     font=('Arial',10,'bold')).grid(row=row, column=col*2, padx=6, pady=8, sticky='e')
            e = tk.Entry(form, width=w, font=('Arial',11), justify='right')
            e.grid(row=row, column=col*2+1, padx=6, pady=8)
            self.prod_e[key] = e

        br = tk.Frame(form, bg='white')
        br.grid(row=3, column=0, columnspan=8, pady=12)
        self._btn(br, "➕ إضافة", CLR['primary'], self._add_product, 12).pack(side='right', padx=4)
        self._btn(br, "💾 حفظ التعديل", CLR['warning'], self._update_product, 12).pack(side='right', padx=4)
        self._btn(br, "🔄 مسح الفورم", CLR['secondary'], self._clear_prod_form, 12).pack(side='right', padx=4)
        self._btn(br, "🎲 باركود عشوائي", CLR['accent'], self._gen_bc, 12).pack(side='right', padx=4)

        self.prod_id = None  # current editing id

        # Search + list
        sbar = tk.Frame(f, bg='white', highlightthickness=1,
                        highlightbackground=CLR['border'])
        sbar.pack(fill='x', pady=(0,10))
        tk.Label(sbar, text="🔍", bg='white', font=('Arial',14)).pack(side='right', padx=(15,5))
        self.prod_search = tk.Entry(sbar, font=('Arial',11), justify='right', width=40)
        self.prod_search.pack(side='right', pady=10, ipady=5)
        self.prod_search.bind('<KeyRelease>', lambda e: self._load_products())
        self._btn(sbar, "🔄", CLR['secondary'], self._load_products, 8).pack(side='left', padx=8)
        self._btn(sbar, "📤 تصدير", CLR['accent'], self._export_products_csv, 10).pack(side='left', padx=4)

        cols = ('ID','الباركود','الاسم','الفئة','السعر','التكلفة','المخزون','الحالة')
        self.prod_tree = ttk.Treeview(f, columns=cols, show='headings', height=15)
        for c,w in zip(cols,[50,140,250,120,110,110,90,100]):
            self.prod_tree.heading(c,text=c); self.prod_tree.column(c,width=w,anchor='center')
        self.prod_tree.pack(fill='both', expand=True)
        self.prod_tree.bind('<Double-1>', lambda e: self._load_prod_to_form())
        self.prod_tree.bind('<Delete>', lambda e: self._del_product())

        self._load_products()

    def _gen_bc(self):
        self.prod_e['barcode'].delete(0,'end')
        self.prod_e['barcode'].insert(0, gen_barcode())

    def _clear_prod_form(self):
        for e in self.prod_e.values(): e.delete(0,'end')
        self.prod_e['unit'].insert(0, "قطعة")
        self.prod_e['minq'].insert(0, "5")
        self.prod_id = None

    def _add_product(self):
        try:
            name = self.prod_e['name'].get().strip()
            if not name: raise ValueError("الاسم مطلوب")
            price = float(self.prod_e['price'].get() or 0)
            cost  = float(self.prod_e['cost'].get() or 0)
            qty   = int(self.prod_e['qty'].get() or 0)
            minq  = int(self.prod_e['minq'].get() or 5)
            ok, res = self.db.add_product(
                self.prod_e['barcode'].get().strip(),
                name, self.prod_e['cat'].get().strip() or "عام",
                None, price, cost, qty, minq,
                self.prod_e['unit'].get().strip() or "قطعة")
            if ok:
                self.db.log("منتج جديد", name, self.user['username'])
                self._clear_prod_form(); self._load_products()
                self.say(f"تم إضافة {name}")
            else:
                messagebox.showerror("خطأ", res)
        except Exception as e:
            messagebox.showerror("خطأ", str(e))

    def _update_product(self):
        if not self.prod_id:
            return messagebox.showwarning("تحذير","اختر منتج من الجدول أولاً")
        try:
            kw = {
                'name': self.prod_e['name'].get().strip(),
                'barcode': self.prod_e['barcode'].get().strip() or None,
                'category': self.prod_e['cat'].get().strip() or "عام",
                'price': float(self.prod_e['price'].get() or 0),
                'cost': float(self.prod_e['cost'].get() or 0),
                'quantity': int(self.prod_e['qty'].get() or 0),
                'min_stock': int(self.prod_e['minq'].get() or 5),
                'unit': self.prod_e['unit'].get().strip() or "قطعة",
            }
            self.db.update_product(self.prod_id, **kw)
            self.db.log("تعديل منتج", kw['name'], self.user['username'])
            self._clear_prod_form(); self._load_products()
            self.say("تم التعديل")
        except Exception as e:
            messagebox.showerror("خطأ", str(e))

    def _load_prod_to_form(self):
        s = self.prod_tree.selection()
        if not s: return
        pid = int(self.prod_tree.item(s[0])['values'][0])
        p = self.db.product(pid)
        if not p: return
        self._clear_prod_form()
        self.prod_id = pid
        self.prod_e['name'].insert(0, p['name'])
        self.prod_e['barcode'].insert(0, p['barcode'] or '')
        self.prod_e['cat'].insert(0, p['category'])
        self.prod_e['price'].insert(0, str(p['price']))
        self.prod_e['cost'].insert(0, str(p['cost']))
        self.prod_e['qty'].insert(0, str(p['quantity']))
        self.prod_e['minq'].insert(0, str(p['min_stock']))
        self.prod_e['unit'].insert(0, p['unit'])

    def _del_product(self):
        s = self.prod_tree.selection()
        if not s: return
        v = self.prod_tree.item(s[0])['values']
        if messagebox.askyesno("تأكيد", f"حذف {v[2]}؟"):
            self.db.del_product(v[0])
            self.db.log("حذف منتج", v[2], self.user['username'])
            self._load_products(); self.say("تم الحذف")

    def _load_products(self):
        for i in self.prod_tree.get_children(): self.prod_tree.delete(i)
        for p in self.db.products(self.prod_search.get().strip(), only_active=False):
            status = "🟢" if p['quantity'] > p['min_stock'] else ("🟡" if p['quantity'] > 0 else "🔴")
            self.prod_tree.insert('', 'end', values=(
                p['id'], p['barcode'] or '-', p['name'], p['category'],
                money(p['price'], ''), money(p['cost'], ''),
                p['quantity'], f"{status} {'نشط' if p['is_active'] else 'موقوف'}"))

    def _export_products_csv(self):
        p = filedialog.asksaveasfilename(defaultextension=".csv",
            initialfile=f"products_{today()}.csv", filetypes=[("CSV","*.csv")])
        if p:
            self.db.export_products_csv(p)
            messagebox.showinfo("تم", f"✅ {p}")

    # ═══════════════════════════════════════════════════════════════
    #  👥 العملاء
    # ═══════════════════════════════════════════════════════════════
    def _page_customers(self):
        f = self.content
        bar = tk.Frame(f, bg='white', highlightthickness=1,
                       highlightbackground=CLR['border'])
        bar.pack(fill='x', pady=(0,10))
        tk.Label(bar, text="🔍", bg='white', font=('Arial',14)).pack(side='right', padx=(15,5))
        self.cust_search = tk.Entry(bar, font=('Arial',11), justify='right', width=40)
        self.cust_search.pack(side='right', pady=10, ipady=5)
        self.cust_search.bind('<KeyRelease>', lambda e: self._load_customers())
        self._btn(bar, "➕ إضافة عميل", CLR['primary'], self._add_customer_dialog, 12).pack(side='left', padx=10, pady=10)
        self._btn(bar, "🔄 تحديث", CLR['secondary'], self._load_customers, 10).pack(side='left', padx=4)

        cols = ('ID','الاسم','الهاتف','البريد','العنوان','إجمالي الشراء',
                'عدد الفواتير','نقاط الولاء','آخر شراء')
        self.cust_tree = ttk.Treeview(f, columns=cols, show='headings', height=22)
        for c,w in zip(cols,[50,160,120,180,180,140,90,110,150]):
            self.cust_tree.heading(c,text=c); self.cust_tree.column(c,width=w,anchor='center')
        self.cust_tree.pack(fill='both', expand=True)
        self._load_customers()

    def _add_customer_dialog(self):
        d = tk.Toplevel(self.root); d.title("إضافة عميل")
        d.geometry("440x420"); d.configure(bg='white'); d.transient(self.root); d.grab_set()
        d.update_idletasks()
        x = (d.winfo_screenwidth()//2) - 220; y = (d.winfo_screenheight()//2) - 210
        d.geometry(f"+{x}+{y}")

        tk.Label(d, text="👤  عميل جديد", font=('Arial',15,'bold'),
                 bg='white', fg=CLR['primary']).pack(pady=15)
        fields = [("الاسم *",'name'),("الهاتف",'phone'),
                  ("البريد",'email'),("العنوان",'addr'),("ملاحظات",'notes')]
        e = {}
        for lbl, key in fields:
            tk.Label(d, text=lbl, bg='white', font=('Arial',10,'bold')).pack(anchor='e', padx=30, pady=(5,0))
            ent = tk.Entry(d, font=('Arial',11), justify='right')
            ent.pack(fill='x', padx=30, ipady=5)
            e[key] = ent

        def save():
            if not e['name'].get().strip():
                return messagebox.showwarning("تحذير","الاسم مطلوب")
            ok, res = self.db.add_customer(e['name'].get().strip(), e['phone'].get().strip(),
                e['email'].get().strip(), e['addr'].get().strip(), e['notes'].get().strip())
            if ok:
                self.db.log("عميل جديد", e['name'].get(), self.user['username'])
                self._load_customers(); d.destroy(); self.say("تم إضافة العميل")
            else:
                messagebox.showerror("خطأ", res)

        self._btn(d, "💾 حفظ", CLR['primary'], save, 12).pack(pady=15, padx=30, fill='x')

    def _load_customers(self):
        for i in self.cust_tree.get_children(): self.cust_tree.delete(i)
        for c in self.db.customers(self.cust_search.get().strip()):
            self.cust_tree.insert('', 'end', values=(
                c['id'], c['name'], c['phone'] or '-', c['email'] or '-',
                c['address'] or '-', money(c['total_purchases'], self.cur),
                c['orders_count'], c['loyalty_points'],
                fmt_dt(c['last_purchase']) if c['last_purchase'] else '-'))

    # ═══════════════════════════════════════════════════════════════
    #  📊 التقارير
    # ═══════════════════════════════════════════════════════════════
    def _page_reports(self):
        f = self.content
        s = self.db.summary()

        # Cards
        cf = tk.Frame(f, bg=CLR['light']); cf.pack(fill='x', pady=(0,12))
        cards = [
            ("💰 المبيعات", money(s['total_sales'], self.cur), CLR['primary']),
            ("📈 الربح", money(s['profit'], self.cur), CLR['success']),
            ("📋 الفواتير", f"{s['total_orders']:,}", CLR['secondary']),
            ("📦 القطع المبيعة", f"{s['total_items']:,}", CLR['accent']),
        ]
        for i,(t,v,c) in enumerate(cards):
            box = tk.Frame(cf, bg=c, height=100)
            box.grid(row=0, column=i, padx=4, sticky='nsew')
            cf.columnconfigure(i, weight=1)
            tk.Label(box, text=t, font=('Arial',11,'bold'), bg=c, fg='white').pack(pady=(18,5))
            tk.Label(box, text=v, font=('Arial',15,'bold'), bg=c, fg='white').pack()

        # Buttons
        br = tk.Frame(f, bg=CLR['light']); br.pack(fill='x', pady=6)
        self._btn(br, "🖨️ طباعة تقرير", CLR['primary'], self._print_report, 12).pack(side='right', padx=4)
        self._btn(br, "📤 تصدير الفواتير", CLR['accent'], self._export_orders_csv, 12).pack(side='right', padx=4)

        # Text area
        txt = tk.Text(f, font=('Courier New', 10), bg='white', padx=20, pady=20,
                      relief=tk.FLAT)
        txt.pack(fill='both', expand=True)

        W = 68
        sep = "═"*W
        dash = "─"*W
        lines = [sep, f"📊 تقرير شامل — {self.db.get('shop_name',APP_NAME)}".center(W),
                 f"📅 {datetime.now():%Y-%m-%d %H:%M}".center(W), sep, ""]
        lines += [f"💰 إجمالي المبيعات:        {money(s['total_sales'], self.cur):>25}",
                  f"📅 مبيعات اليوم:            {money(s['today_sales'], self.cur):>25}",
                  f"🗓️ مبيعات الشهر:            {money(s['month_sales'], self.cur):>25}",
                  f"📈 إجمالي التكلفة:          {money(s['total_cost'], self.cur):>25}",
                  f"💵 إجمالي المصاريف:         {money(s['expenses'], self.cur):>25}",
                  f"✅ صافي الربح:              {money(s['profit'], self.cur):>25}",
                  "",
                  f"📋 عدد الفواتير:            {s['total_orders']:>25,}",
                  f"👥 عدد العملاء:             {s['total_custs']:>25,}",
                  f"📦 عدد المنتجات:            {s['total_prods']:>25,}",
                  f"🛒 القطع المبيعة:            {s['total_items']:>25,}",
                  f"⚠️ منتجات مخزون منخفض:      {s['low_stock']:>25,}",
                  "", dash, "🏆 أفضل 10 منتجات مبيعاً:", dash]

        for i, p in enumerate(self.db.top_products(10), 1):
            lines.append(f"  {i:>2}. {p['product_name']:<30} {p['qty']:>8} قطعة | {money(p['total'], self.cur):>15}")

        lines += ["", dash, "👥 أفضل 10 عملاء:", dash]
        for i, c in enumerate(self.db.top_customers(10), 1):
            lines.append(f"  {i:>2}. {c['name']:<25} {money(c['total_purchases'],self.cur):>15} ({c['orders_count']} فاتورة)")

        lines += ["", sep, f"تم بواسطة {DEVELOPER} — {APP_NAME}".center(W), sep]
        txt.insert('1.0', "\n".join(lines))
        txt.config(state='disabled')
        self._report_text = txt

    def _print_report(self):
        p = filedialog.asksaveasfilename(defaultextension=".txt",
            initialfile=f"report_{today()}.txt", filetypes=[("نص","*.txt")])
        if p:
            with open(p,'w',encoding='utf-8') as f:
                f.write(self._report_text.get('1.0','end'))
            messagebox.showinfo("تم", f"✅ {p}")

    # ═══════════════════════════════════════════════════════════════
    #  📜 السجلات
    # ═══════════════════════════════════════════════════════════════
    def _page_logs(self):
        f = self.content
        bar = tk.Frame(f, bg='white', highlightthickness=1,
                       highlightbackground=CLR['border'])
        bar.pack(fill='x', pady=(0,10))
        tk.Label(bar, text="📜  سجل النشاطات", font=('Arial',13,'bold'),
                 bg='white', fg=CLR['text_dark']).pack(side='right', padx=20, pady=12)
        self._btn(bar, "🔄 تحديث", CLR['secondary'], self._load_logs, 10).pack(side='left', padx=10, pady=10)
        self._btn(bar, "🗑️ مسح", CLR['danger'], self._clear_logs, 10).pack(side='left', padx=4, pady=10)

        cols = ('ID','الإجراء','التفاصيل','المستخدم','الوقت')
        self.log_tree = ttk.Treeview(f, columns=cols, show='headings', height=24)
        for c,w in zip(cols,[50,160,500,150,170]):
            self.log_tree.heading(c,text=c); self.log_tree.column(c,width=w,anchor='center')
        self.log_tree.pack(fill='both', expand=True)
        self._load_logs()

    def _load_logs(self):
        for i in self.log_tree.get_children(): self.log_tree.delete(i)
        for l in self.db.logs():
            self.log_tree.insert('', 'end', values=(
                l['id'], l['action'], l['details'] or '-', l['username'] or '-',
                fmt_dt(l['created_at'])))

    def _clear_logs(self):
        if messagebox.askyesno("تأكيد","مسح كل السجلات؟"):
            self.db.clear_logs()
            self._load_logs(); self.say("تم المسح")

    # ═══════════════════════════════════════════════════════════════
    #  🔐 المستخدمون
    # ═══════════════════════════════════════════════════════════════
    def _page_users(self):
        f = self.content
        bar = tk.Frame(f, bg='white', highlightthickness=1,
                       highlightbackground=CLR['border'])
        bar.pack(fill='x', pady=(0,10))
        tk.Label(bar, text="🔐  إدارة المستخدمين", font=('Arial',13,'bold'),
                 bg='white', fg=CLR['text_dark']).pack(side='right', padx=20, pady=12)
        self._btn(bar, "➕ مستخدم جديد", CLR['primary'], self._add_user_dialog, 12).pack(side='left', padx=10, pady=10)
        self._btn(bar, "🗑️ حذف", CLR['danger'], self._del_user, 10).pack(side='left', padx=4, pady=10)
        self._btn(bar, "🔑 تغيير كلمة المرور", CLR['warning'], self._change_own_pw, 12).pack(side='left', padx=4, pady=10)

        cols = ('ID','اسم المستخدم','الاسم الكامل','الدور','الحالة','تاريخ الإنشاء')
        self.users_tree = ttk.Treeview(f, columns=cols, show='headings', height=20)
        for c,w in zip(cols,[50,160,200,120,100,180]):
            self.users_tree.heading(c,text=c); self.users_tree.column(c,width=w,anchor='center')
        self.users_tree.pack(fill='both', expand=True)
        self._load_users()

    def _load_users(self):
        for i in self.users_tree.get_children(): self.users_tree.delete(i)
        for u in self.db.users():
            self.users_tree.insert('', 'end', values=(
                u['id'], u['username'], u['full_name'] or '-', u['role'],
                "🟢 نشط" if u['is_active'] else "🔴 موقوف",
                fmt_dt(u['created_at'])))

    def _add_user_dialog(self):
        d = tk.Toplevel(self.root); d.title("مستخدم جديد")
        d.geometry("400x480"); d.configure(bg='white'); d.transient(self.root); d.grab_set()

        tk.Label(d, text="➕  مستخدم جديد", font=('Arial',15,'bold'),
                 bg='white', fg=CLR['primary']).pack(pady=15)

        tk.Label(d, text="اسم المستخدم *", bg='white', font=('Arial',10,'bold')).pack(anchor='e', padx=30, pady=(8,2))
        u = tk.Entry(d, font=('Arial',11), justify='right'); u.pack(fill='x', padx=30, ipady=6)
        tk.Label(d, text="كلمة المرور *", bg='white', font=('Arial',10,'bold')).pack(anchor='e', padx=30, pady=(8,2))
        p = tk.Entry(d, font=('Arial',11), justify='right', show='●'); p.pack(fill='x', padx=30, ipady=6)
        tk.Label(d, text="الاسم الكامل", bg='white', font=('Arial',10,'bold')).pack(anchor='e', padx=30, pady=(8,2))
        n = tk.Entry(d, font=('Arial',11), justify='right'); n.pack(fill='x', padx=30, ipady=6)
        tk.Label(d, text="الدور", bg='white', font=('Arial',10,'bold')).pack(anchor='e', padx=30, pady=(8,2))
        r = ttk.Combobox(d, values=['admin','manager','cashier'], state='readonly')
        r.set('cashier'); r.pack(fill='x', padx=30, pady=2)

        def save():
            if not u.get().strip() or not p.get():
                return messagebox.showwarning("تحذير","أكمل البيانات")
            ok, msg = self.db.add_user(u.get().strip(), p.get(), n.get().strip(), r.get())
            if ok:
                self.db.log("مستخدم جديد", u.get(), self.user['username'])
                self._load_users(); d.destroy(); self.say("تم إضافة المستخدم")
            else:
                messagebox.showerror("خطأ", msg)

        self._btn(d, "💾 حفظ", CLR['primary'], save, 12).pack(pady=18, padx=30, fill='x')

    def _del_user(self):
        s = self.users_tree.selection()
        if not s: return
        v = self.users_tree.item(s[0])['values']
        if v[1] == 'admin':
            return messagebox.showwarning("تحذير","لا يمكن حذف admin")
        if messagebox.askyesno("تأكيد", f"حذف {v[1]}؟"):
            self.db.del_user(v[0])
            self._load_users(); self.say("تم الحذف")

    def _change_own_pw(self):
        d = tk.Toplevel(self.root); d.title("تغيير كلمة المرور")
        d.geometry("400x340"); d.configure(bg='white'); d.transient(self.root); d.grab_set()

        tk.Label(d, text="🔑  تغيير كلمة المرور", font=('Arial',15,'bold'),
                 bg='white', fg=CLR['primary']).pack(pady=15)

        tk.Label(d, text="الحالية", bg='white', font=('Arial',10,'bold')).pack(anchor='e', padx=30, pady=(8,2))
        o = tk.Entry(d, show='●', font=('Arial',11), justify='right'); o.pack(fill='x', padx=30, ipady=6)
        tk.Label(d, text="الجديدة", bg='white', font=('Arial',10,'bold')).pack(anchor='e', padx=30, pady=(8,2))
        n1 = tk.Entry(d, show='●', font=('Arial',11), justify='right'); n1.pack(fill='x', padx=30, ipady=6)
        tk.Label(d, text="تأكيد الجديدة", bg='white', font=('Arial',10,'bold')).pack(anchor='e', padx=30, pady=(8,2))
        n2 = tk.Entry(d, show='●', font=('Arial',11), justify='right'); n2.pack(fill='x', padx=30, ipady=6)

        def save():
            if not o.get() or not n1.get():
                return messagebox.showwarning("تحذير","أكمل البيانات")
            if n1.get() != n2.get():
                return messagebox.showerror("خطأ","كلمتا المرور غير متطابقتين")
            if len(n1.get()) < 4:
                return messagebox.showerror("خطأ","كلمة المرور قصيرة (4 أحرف)")
            ok, msg = self.db.change_pw(self.user['username'], o.get(), n1.get())
            if ok:
                messagebox.showinfo("تم", msg); d.destroy()
            else:
                messagebox.showerror("خطأ", msg)

        self._btn(d, "💾 حفظ", CLR['primary'], save, 12).pack(pady=18, padx=30, fill='x')

    # ═══════════════════════════════════════════════════════════════
    #  ⚙️ الإعدادات
    # ═══════════════════════════════════════════════════════════════
    def _page_settings(self):
        # Scrollable area
        f = tk.Frame(self.content, bg=CLR['light']); f.pack(fill='both', expand=True)
        cv = tk.Canvas(f, bg=CLR['light'], highlightthickness=0)
        sb = ttk.Scrollbar(f, orient='vertical', command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side='right', fill='both', expand=True)
        sb.pack(side='left', fill='y')
        inner = tk.Frame(cv, bg=CLR['light'])
        cv.create_window((0,0), window=inner, anchor='ne')

        def _onconf(e):
            cv.configure(scrollregion=cv.bbox('all'))
        inner.bind('<Configure>', _onconf)

        # Shop info
        self._settings_section(inner, "🏪  بيانات المحل", [
            ("اسم المحل", 'shop_name'), ("الاسم بالإنجليزية", 'shop_name_en'),
            ("رقم الهاتف", 'shop_phone'), ("العنوان", 'shop_address'),
            ("البريد", 'shop_email'), ("العملة", 'currency'),
            ("نسبة الضريبة %", 'tax_rate'), ("كلمة تذييل الفاتورة", 'receipt_footer'),
        ], self._save_shop_info)

        # Security
        sec = tk.LabelFrame(inner, text=" 🔐 الأمان ", bg='white',
                            font=('Arial',12,'bold'), fg=CLR['primary'],
                            padx=20, pady=15)
        sec.pack(fill='x', padx=10, pady=8)
        self._btn(sec, "🔑 تغيير كلمة مرور الدخول", CLR['warning'],
                  self._change_own_pw, 12).pack(fill='x', pady=4)
        self._btn(sec, "🔒 كلمة مرور النسخ الاحتياطية", CLR['secondary'],
                  self._change_backup_pw, 12).pack(fill='x', pady=4)

        # Backup
        bk = tk.LabelFrame(inner, text=f" 💾 النسخ الاحتياطية (صيغة {BACKUP_EXT} مشفرة) ",
                           bg='white', font=('Arial',12,'bold'), fg=CLR['primary'],
                           padx=20, pady=15)
        bk.pack(fill='x', padx=10, pady=8)
        self._btn(bk, "💾 إنشاء نسخة مشفرة الآن", CLR['primary'], self._do_backup, 12).pack(fill='x', pady=4)
        self._btn(bk, "♻️ استعادة من نسخة مشفرة", CLR['secondary'], self._do_restore, 12).pack(fill='x', pady=4)
        self._btn(bk, "📂 عرض النسخ المتاحة", CLR['info'], self._view_backups, 12).pack(fill='x', pady=4)
        self._btn(bk, "📤 تصدير نسخة لمكان آخر", CLR['accent'], self._export_backup, 12).pack(fill='x', pady=4)

        # Danger
        dg = tk.LabelFrame(inner, text=" ⚠️ منطقة الخطر ", bg='#fef2f2',
                           font=('Arial',12,'bold'), fg=CLR['danger'],
                           padx=20, pady=15)
        dg.pack(fill='x', padx=10, pady=8)
        self._btn(dg, "🗑️ إعادة ضبط المصنع", CLR['danger'], self._do_reset, 12).pack(fill='x', pady=4)
        self._btn(dg, "🚪 تسجيل خروج", CLR['dark'], self._close, 12).pack(fill='x', pady=4)

        # About
        ab = tk.LabelFrame(inner, text=" ℹ️ عن البرنامج ", bg='white',
                           font=('Arial',12,'bold'), fg=CLR['primary'],
                           padx=20, pady=15)
        ab.pack(fill='x', padx=10, pady=8)
        about = f"""
{APP_NAME} — {APP_SUBTITLE}
الإصدار: {APP_VERSION}  ·  الطبعة: {APP_EDITION}  ·  البناء: {APP_BUILD}

تطوير وصيانة:
  {DEVELOPER_FULL}  ({DEVELOPER})

سجل التغييرات v5.0:
  • نظام مستخدمين بالأدوار
  • نسخ احتياطية مشفرة بصيغة {BACKUP_EXT}
  • نقطة بيع سريعة (POS) بالباركود
  • تقارير احترافية ورسوم بيانية
  • نظام نقاط الولاء للعملاء
  • سجل نشاطات كامل

{COPYRIGHT}
"""
        tk.Label(ab, text=about, bg='white', justify='right',
                 font=('Courier New',10), fg=CLR['text']).pack(fill='x')

    def _settings_section(self, parent, title, fields, save_cmd):
        box = tk.LabelFrame(parent, text=f" {title} ", bg='white',
                            font=('Arial',12,'bold'), fg=CLR['primary'],
                            padx=20, pady=15)
        box.pack(fill='x', padx=10, pady=8)
        self._set_entries = getattr(self, '_set_entries', {})
        for i, (lbl, key) in enumerate(fields):
            r = tk.Frame(box, bg='white'); r.pack(fill='x', pady=4)
            tk.Label(r, text=f"{lbl}:", bg='white', width=22, anchor='e',
                     font=('Arial',10,'bold')).pack(side='right')
            e = tk.Entry(r, font=('Arial',11), justify='right')
            e.insert(0, self.db.get(key,''))
            e.pack(side='right', fill='x', expand=True, padx=10, ipady=4)
            self._set_entries[key] = e
        self._btn(box, "💾 حفظ", CLR['primary'], save_cmd, 12).pack(pady=10, fill='x')

    def _save_shop_info(self):
        for k, e in self._set_entries.items():
            self.db.set(k, e.get())
        self.cur = self.db.get('currency','ج.م')
        self.db.log("تعديل الإعدادات","", self.user['username'])
        messagebox.showinfo("تم", "✅ تم حفظ الإعدادات")
        self.say("تم الحفظ")

    def _change_backup_pw(self):
        pw = simpledialog.askstring("كلمة مرور النسخ","كلمة المرور الجديدة:",
                                     show='●', parent=self.root)
        if pw:
            self.db.set('backup_password', pw)
            self.db.log("تغيير كلمة مرور النسخ","", self.user['username'])
            messagebox.showinfo("تم","✅ تم التحديث")

    def _do_backup(self):
        pw = self.db.get('backup_password','ebnezz_default')
        ok, msg = self.db.backup(pw)
        messagebox.showinfo("نسخة احتياطية", msg)
        self.say(msg.split('\n')[0][:50])

    def _do_restore(self):
        p = filedialog.askopenfilename(
            title="اختر نسخة مشفرة",
            initialdir=str(self.db.backup_dir),
            filetypes=[("EbnEzz","*.ebz"),("الكل","*.*")])
        if not p: return
        pw = simpledialog.askstring("كلمة المرور","كلمة مرور النسخة:", show='●')
        if pw is None: return
        if not messagebox.askyesno("تأكيد","سيتم استبدال البيانات!"): return
        ok, msg = self.db.restore(p, pw)
        messagebox.showinfo("استعادة", msg)
        if ok:
            self._show('dashboard')
            self.say("تم الاستعادة")

    def _view_backups(self):
        items = self.db.list_backups()
        if not items:
            return messagebox.showinfo("نسخ","لا توجد نسخ")
        d = tk.Toplevel(self.root); d.title("النسخ الاحتياطية")
        d.geometry("600x500"); d.configure(bg='white'); d.transient(self.root)

        tk.Label(d, text="📂  النسخ المتاحة", font=('Arial',14,'bold'),
                 bg='white', fg=CLR['primary']).pack(pady=15)
        cols = ('الملف','الحجم (KB)','التاريخ')
        t = ttk.Treeview(d, columns=cols, show='headings', height=15)
        for c,w in zip(cols,[300,120,150]):
            t.heading(c,text=c); t.column(c,width=w,anchor='center')
        t.pack(fill='both', expand=True, padx=20, pady=10)
        for it in items:
            t.insert('', 'end', values=(it['name'], f"{it['size']/1024:.1f}",
                                        datetime.fromtimestamp(it['mtime']).strftime('%Y-%m-%d %H:%M')))

    def _export_backup(self):
        pw = self.db.get('backup_password','ebnezz_default')
        p = filedialog.asksaveasfilename(
            defaultextension=BACKUP_EXT,
            filetypes=[("EbnEzz", f"*{BACKUP_EXT}")],
            initialfile=f"{self.db.get('shop_name','ebnezz')}_{today()}{BACKUP_EXT}")
        if not p: return
        ok, msg = self.db.export_enc(p, pw)
        messagebox.showinfo("تصدير", msg)

    def _do_reset(self):
        if not messagebox.askyesno("⚠️ تحذير خطير","سيتم حذف كل البيانات نهائياً!\nمتابعة؟"):
            return
        t = simpledialog.askstring("تأكيد",'اكتب "حذف كل شيء" للمتابعة:')
        if t != "حذف كل شيء": return
        ok, msg = self.db.reset()
        messagebox.showinfo("إعادة ضبط", msg)
        if ok:
            self._show('dashboard')
            self.say("تم إعادة الضبط")

    # ═══════════════════════════════════════════════════════════════
    #  🛠️ أدوات
    # ═══════════════════════════════════════════════════════════════
    def _btn(self, parent, text, color, cmd, size=11):
        return tk.Button(parent, text=text, bg=color, fg='white',
                         font=('Arial', size, 'bold'), relief=tk.FLAT,
                         cursor='hand2', padx=15, pady=8, command=cmd,
                         activebackground=color)

    def _auto_backup_check(self):
        """نسخة تلقائية عند التشغيل"""
        try:
            if self.db.get('auto_backup','1') == '1':
                pw = self.db.get('backup_password','ebnezz_default')
                self.db.backup(pw, tag="auto")
                days = int(self.db.get('backup_days','7'))
                n = self.db.cleanup_backups(days)
                if n: self.say(f"تم حذف {n} نسخة قديمة")
        except: pass

    def _close(self):
        if messagebox.askyesno("خروج","هل تريد تسجيل الخروج؟"):
            try: self.db.log("خروج","", self.user['username'])
            except: pass
            self.root.destroy()


# ═══════════════════════════════════════════════════════════════════════════
#  🚀 نقطة الدخول
# ═══════════════════════════════════════════════════════════════════════════
def _excepthook(et, ev, tb):
    err = "".join(traceback.format_exception(et, ev, tb))
    try:
        with open("ebnezz_error.log", 'a', encoding='utf-8') as f:
            f.write(f"\n[{datetime.now()}] {err}\n")
    except: pass
    print(err)
    try:
        messagebox.showerror("خطأ", f"حدث خطأ:\n{ev}\n\nراجع ebnezz_error.log")
    except: pass

sys.excepthook = _excepthook


if __name__ == "__main__":
    try:
        Splash().show(2000)
        login = LoginWindow()
        user = login.run()
        if not user:
            sys.exit(0)
        root = tk.Tk()
        app = MainApp(root, user, login.db)
        root.mainloop()
    except Exception as e:
        traceback.print_exc()
        input("\nاضغط Enter للخروج...")