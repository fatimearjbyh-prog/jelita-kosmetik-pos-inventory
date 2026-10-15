
import sqlite3
import os
import getpass
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "pos_inventory.db")


def create_user():
    print("\n=== CREATE USER - JELITA KOSMETIK ===")

    if not os.path.exists(DATABASE):
        print("Database belum ada.")
        print("Jalankan python init_db.py terlebih dahulu.")
        return

    username = input("Username: ").strip()

    if not username:
        print("Username tidak boleh kosong.")
        return

    role = input("Role (admin/cashier): ").strip().lower()

    if role not in ("admin", "cashier"):
        print("Role harus admin atau cashier.")
        return

    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Konfirmasi password: ")

    if len(password) < 8:
        print("Password minimal 8 karakter.")
        return

    if password != confirm:
        print("Konfirmasi password tidak cocok.")
        return

    hashed_password = generate_password_hash(password)

    conn = sqlite3.connect(DATABASE)

    try:
        conn.execute(
            """
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
            """,
            (username, hashed_password, role)
        )

        conn.commit()
        print(f"Akun {role} berhasil dibuat!")

    except sqlite3.IntegrityError:
        print("Username sudah digunakan.")

    finally:
        conn.close()


if __name__ == "__main__":
    create_user()
