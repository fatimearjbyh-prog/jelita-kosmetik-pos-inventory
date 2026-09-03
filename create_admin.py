import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect("pos_inventory.db")
cursor = conn.cursor()

username = "admin"
password = "admin123"

hashed_password = generate_password_hash(password)

try:
    cursor.execute("""
        INSERT INTO users (username, password, role)
        VALUES (?, ?, ?)
    """, (username, hashed_password, "admin"))

    conn.commit()
    print("Akun admin berhasil dibuat!")

except sqlite3.IntegrityError:
    print("Username admin sudah ada.")

finally:
    conn.close()