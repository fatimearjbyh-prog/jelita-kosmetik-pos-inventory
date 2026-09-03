import sqlite3

# Membuat / membuka database
conn = sqlite3.connect("pos_inventory.db")

# Mengaktifkan foreign key
conn.execute("PRAGMA foreign_keys = ON")

cursor = conn.cursor()

# =========================
# TABEL USERS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'cashier'))
)
""")

# =========================
# TABEL PRODUCTS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    category TEXT,
    price REAL NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0
)
""")

# =========================
# TABEL TRANSACTIONS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_code TEXT NOT NULL UNIQUE,
    transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    total REAL NOT NULL,
    payment REAL NOT NULL,
    change_amount REAL NOT NULL,
    cashier_id INTEGER NOT NULL,

    FOREIGN KEY (cashier_id)
        REFERENCES users(id)
)
""")

# =========================
# TABEL TRANSACTION DETAILS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS transaction_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    subtotal REAL NOT NULL,

    FOREIGN KEY (transaction_id)
        REFERENCES transactions(id)
        ON DELETE CASCADE,

    FOREIGN KEY (product_id)
        REFERENCES products(id)
)
""")

# Simpan perubahan
conn.commit()

# Tutup database
conn.close()

print("Database berhasil dibuat!")
