import sqlite3

from werkzeug.security import generate_password_hash


# ==========================================
# DATABASE
# ==========================================

conn = sqlite3.connect("pos_inventory.db")

cursor = conn.cursor()


# ==========================================
# CASHIER ACCOUNT
# ==========================================

username = "cashier01"

password = "cashier123"

role = "cashier"


hashed_password = generate_password_hash(password)


# ==========================================
# INSERT USER
# ==========================================

try:

    cursor.execute(
        """
        INSERT INTO users
        (
            username,
            password,
            role
        )
        VALUES (?, ?, ?)
        """,
        (
            username,
            hashed_password,
            role
        )
    )


    conn.commit()


    print("==============================")

    print("Akun Cashier berhasil dibuat!")

    print("==============================")

    print("Username :", username)

    print("Password :", password)

    print("Role     :", role)

    print("==============================")


except sqlite3.IntegrityError:

    print("Username cashier01 sudah terdaftar.")


finally:

    conn.close()