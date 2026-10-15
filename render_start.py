
import os
import sqlite3

from werkzeug.security import generate_password_hash
from init_db import init_database, DATABASE


def setup_demo():
    # Ambil akun demo dari pengaturan Render
    username = os.environ.get("DEMO_USERNAME", "").strip()
    password = os.environ.get("DEMO_PASSWORD", "")

    if not username or len(password) < 8:
        raise RuntimeError(
            "Atur DEMO_USERNAME dan DEMO_PASSWORD "
            "(minimal 8 karakter) di Render."
        )

    # Buat database jika belum tersedia
    init_database()

    conn = sqlite3.connect(DATABASE)

    try:
        cursor = conn.cursor()

        # Periksa apakah akun demo sudah ada
        cursor.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        )

        if cursor.fetchone():
            print("Akun demo sudah tersedia.")
            return

        # Buat akun demo dengan password yang di-hash
        cursor.execute(
            """
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
            """,
            (
                username,
                generate_password_hash(password),
                "admin"
            )
        )

        conn.commit()
        print("Akun demo berhasil dibuat.")

    finally:
        conn.close()


if __name__ == "__main__":
    setup_demo()
