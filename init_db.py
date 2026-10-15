
import sqlite3
import os

# Lokasi database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "pos_inventory.db")


def init_database():
    # Jangan menimpa database yang sudah ada
    if os.path.exists(DATABASE):
        print("Database sudah ada.")
        print("Inisialisasi dibatalkan.")
        return

    conn = sqlite3.connect(DATABASE)

    try:
        conn.execute("PRAGMA foreign_keys = ON")

        cursor = conn.cursor()

        # USERS
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL
                    CHECK(role IN ('admin', 'cashier'))
            )
        """)

        # PRODUCTS
        cursor.execute("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_code TEXT NOT NULL UNIQUE,
                product_name TEXT NOT NULL,
                category TEXT,
                price REAL NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                barcode TEXT
            )
        """)

        # TRANSACTIONS
        cursor.execute("""
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_code TEXT NOT NULL UNIQUE,
                transaction_date DATETIME
                    DEFAULT CURRENT_TIMESTAMP,
                total REAL NOT NULL,
                payment REAL NOT NULL,
                change_amount REAL NOT NULL,
                cashier_id INTEGER NOT NULL,
                payment_method TEXT DEFAULT 'Cash',

                FOREIGN KEY (cashier_id)
                    REFERENCES users(id)
            )
        """)

        # TRANSACTION DETAILS
        cursor.execute("""
            CREATE TABLE transaction_details (
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

        # INVENTORY LOGS
        cursor.execute("""
            CREATE TABLE inventory_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL
                    CHECK(movement_type IN ('IN', 'OUT')),
                quantity INTEGER NOT NULL,
                note TEXT,
                created_at DATETIME
                    DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,

                FOREIGN KEY (product_id)
                    REFERENCES products(id),

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
            )
        """)

        conn.commit()
        print("Database berhasil dibuat!")
        print("Semua tabel berhasil dibuat.")

    except Exception:
        conn.rollback()
        if os.path.exists(DATABASE):
            conn.close()
            os.remove(DATABASE)
        raise

    finally:
        # Aman dipanggil meskipun koneksi sudah ditutup
        conn.close()


if __name__ == "__main__":
    init_database()
