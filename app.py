from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from datetime import datetime
import sqlite3
import os


# =========================================================
# KONFIGURASI APLIKASI
# =========================================================

app = Flask(__name__)

# Digunakan untuk session login
app.secret_key = os.environ.get("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError(
        "SECRET_KEY belum diatur. "
        "Atur environment variable SECRET_KEY sebelum menjalankan aplikasi."
    )

# Format mata uang Rupiah untuk tampilan HTML
@app.template_filter("rupiah")
def format_rupiah(value):
    try:
        return f"Rp {int(value):,}".replace(",", ".")
    except (ValueError, TypeError, OverflowError):
        return "Rp 0"
# Nama toko
STORE_NAME = "Jelita Kosmetik"

# Lokasi folder project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Lokasi database
DATABASE = os.path.join(BASE_DIR, "pos_inventory.db")


# =========================================================
# KONEKSI DATABASE
# =========================================================

def get_db_connection():
    conn = sqlite3.connect(DATABASE)

    # Supaya hasil query bisa dipanggil seperti dictionary
    # Contoh: user["username"]
    conn.row_factory = sqlite3.Row

    # Mengaktifkan foreign key SQLite
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def admin_only():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") != "admin":

        flash(
            "Halaman ini hanya dapat diakses oleh Admin."
        )

        return redirect(
            url_for("cashier")
        )

    return None


# =========================================================
# HALAMAN LOGIN
# =========================================================

@app.route("/", methods=["GET", "POST"])
def login():

    # Kalau user sudah login, langsung ke dashboard
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_db_connection()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        conn.close()

        # Cek username dan password
        if user and check_password_hash(user["password"], password):

            # Simpan data user ke session
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            flash("Login berhasil.")

            if user["role"] == "admin":

                return redirect(
                     url_for("dashboard")
                )

            else:

                return redirect(
                    url_for("cashier")
                )

        else:

            flash("Username atau password salah.")

    return render_template(
        "login.html",
        store_name=STORE_NAME
    )


# =========================================================
# HALAMAN DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    # Hanya Admin yang boleh mengakses Dashboard
    access = admin_only()

    if access:
        return access

    conn = get_db_connection()

    # Menghitung jumlah produk
    total_products = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM products
        """
    ).fetchone()["total"]

    # Menghitung produk dengan stok rendah
    # Untuk sementara stok <= 5 dianggap rendah
    low_stock = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM products
        WHERE stock <= 5
        """
    ).fetchone()["total"]

    # Menghitung jumlah seluruh transaksi
    total_transactions = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM transactions
        """
    ).fetchone()["total"]

    # Menghitung total penjualan
    total_sales = conn.execute(
        """
        SELECT COALESCE(SUM(total), 0) AS total
        FROM transactions
        """
    ).fetchone()["total"]

    conn.close()

    return render_template(
        "dashboard.html",
        store_name=STORE_NAME,
        username=session["username"],
        role=session["role"],
        total_products=total_products,
        low_stock=low_stock,
        total_transactions=total_transactions,
        total_sales=total_sales
    )

# =========================================================
# PRODUCTS
# =========================================================

@app.route("/products")
def products():

    # Hanya Admin yang boleh mengakses Products
    access = admin_only()

    if access:
        return access

    # Ambil kata pencarian dari URL
    search = request.args.get("search", "").strip()

    conn = get_db_connection()

    if search:

        products_data = conn.execute(
            """
            SELECT *
            FROM products
            WHERE product_code LIKE ?
               OR barcode LIKE ?
               OR product_name LIKE ?
               OR category LIKE ?
            ORDER BY id DESC
            """,
            (
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            )
        ).fetchall()

    else:

        products_data = conn.execute(
            """
            SELECT *
            FROM products
            ORDER BY id DESC
            """
        ).fetchall()

    conn.close()

    return render_template(
        "products.html",
        store_name=STORE_NAME,
        products=products_data,
        search=search,
        username=session["username"]
    )


# =========================================================
# ADD PRODUCT
# =========================================================

@app.route("/products/add", methods=["POST"])
def add_product():

    # Hanya Admin yang boleh menambah produk
    access = admin_only()

    if access:
        return access

    product_code = request.form["product_code"].strip()
    barcode = request.form["barcode"].strip()
    product_name = request.form["product_name"].strip()
    category = request.form["category"].strip()
    price = request.form["price"]
    stock = request.form["stock"]

    if not product_code or not product_name or not price:
        flash("Product Code, Product Name, dan Price wajib diisi.")
        return redirect(url_for("products"))

    conn = get_db_connection()

    try:

        conn.execute(
            """
            INSERT INTO products
            (
                product_code,
                product_name,
                category,
                price,
                stock,
                barcode
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                product_code,
                product_name,
                category,
                float(price),
                int(stock),
                barcode
            )
        )

        conn.commit()

        flash("Produk berhasil ditambahkan!")

    except sqlite3.IntegrityError:

        flash("Product Code sudah digunakan.")

    finally:

        conn.close()

    return redirect(url_for("products"))


# =========================================================
# EDIT PRODUCT
# =========================================================

@app.route("/products/edit/<int:id>", methods=["POST"])
def edit_product(id):

    # Hanya Admin yang boleh mengedit produk
    access = admin_only()

    if access:
        return access

    product_code = request.form["product_code"].strip()
    barcode = request.form["barcode"].strip()
    product_name = request.form["product_name"].strip()
    category = request.form["category"].strip()
    price = request.form["price"]
    stock = request.form["stock"]

    conn = get_db_connection()

    try:

        conn.execute(
            """
            UPDATE products

            SET
                product_code = ?,
                barcode = ?,
                product_name = ?,
                category = ?,
                price = ?,
                stock = ?

            WHERE id = ?
            """,
            (
                product_code,
                barcode,
                product_name,
                category,
                float(price),
                int(stock),
                id
            )
        )

        conn.commit()

        flash("Produk berhasil diperbarui!")

    except sqlite3.IntegrityError:

        flash("Product Code sudah digunakan produk lain.")

    finally:

        conn.close()

    return redirect(url_for("products"))


# =========================================================
# DELETE PRODUCT
# =========================================================

@app.route("/products/delete/<int:id>", methods=["POST"])
def delete_product(id):

    # Hanya Admin yang boleh menghapus produk
    access = admin_only()

    if access:
        return access

    conn = get_db_connection()

    conn.execute(
        """
        DELETE FROM products
        WHERE id = ?
        """,
        (id,)
    )

    conn.commit()
    conn.close()

    flash("Produk berhasil dihapus!")

    return redirect(url_for("products"))

# =========================================================
# INVENTORY
# =========================================================

@app.route("/inventory")
def inventory():

    # Hanya Admin yang boleh mengakses Inventory
    access = admin_only()

    if access:
        return access

    # Ambil pencarian
    search = request.args.get("search", "").strip()

    conn = get_db_connection()

    # =========================
    # AMBIL DATA PRODUK
    # =========================

    if search:

        products_data = conn.execute(
            """
            SELECT *
            FROM products
            WHERE product_code LIKE ?
               OR barcode LIKE ?
               OR product_name LIKE ?
               OR category LIKE ?
            ORDER BY product_name ASC
            """,
            (
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            )
        ).fetchall()

    else:

        products_data = conn.execute(
            """
            SELECT *
            FROM products
            ORDER BY product_name ASC
            """
        ).fetchall()


    # =========================
    # STATISTIK INVENTORY
    # =========================

    total_stock = conn.execute(
        """
        SELECT COALESCE(SUM(stock), 0) AS total
        FROM products
        """
    ).fetchone()["total"]


    low_stock = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM products
        WHERE stock > 0
          AND stock <= 5
        """
    ).fetchone()["total"]


    out_of_stock = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM products
        WHERE stock = 0
        """
    ).fetchone()["total"]


    # =========================
    # RIWAYAT STOK TERBARU
    # =========================

    inventory_logs = conn.execute(
        """
        SELECT
            inventory_logs.*,
            products.product_name,
            users.username
        FROM inventory_logs

        JOIN products
            ON inventory_logs.product_id = products.id

        LEFT JOIN users
            ON inventory_logs.user_id = users.id

        ORDER BY inventory_logs.id DESC
        LIMIT 10
        """
    ).fetchall()


    conn.close()


    return render_template(
        "inventory.html",
        store_name=STORE_NAME,
        products=products_data,
        inventory_logs=inventory_logs,
        total_stock=total_stock,
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        search=search
    )


# =========================================================
# STOCK IN
# =========================================================

@app.route("/inventory/stock-in/<int:product_id>", methods=["POST"])
def stock_in(product_id):

    # Hanya Admin yang boleh menambah stok
    access = admin_only()

    if access:
        return access

    quantity = request.form.get("quantity", "").strip()
    note = request.form.get("note", "").strip()

    # Validasi jumlah
    try:

        quantity = int(quantity)

        if quantity <= 0:
            raise ValueError

    except ValueError:

        flash("Jumlah stok harus lebih dari 0.")
        return redirect(url_for("inventory"))


    conn = get_db_connection()

    try:

        # Pastikan produk ada
        product = conn.execute(
            """
            SELECT *
            FROM products
            WHERE id = ?
            """,
            (product_id,)
        ).fetchone()


        if product is None:

            flash("Produk tidak ditemukan.")

            return redirect(
                url_for("inventory")
            )


        # Tambahkan stok produk
        conn.execute(
            """
            UPDATE products
            SET stock = stock + ?
            WHERE id = ?
            """,
            (
                quantity,
                product_id
            )
        )


        # Simpan riwayat stok
        conn.execute(
            """
            INSERT INTO inventory_logs
            (
                product_id,
                movement_type,
                quantity,
                note,
                user_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                product_id,
                "IN",
                quantity,
                note,
                session["user_id"]
            )
        )


        conn.commit()

        flash(
            f"Stok {product['product_name']} "
            f"berhasil ditambahkan sebanyak {quantity}."
        )


    except Exception as error:

        conn.rollback()

        print("ERROR STOCK IN:", error)

        flash(
            "Terjadi kesalahan saat menambahkan stok."
        )


    finally:

        conn.close()


    return redirect(
        url_for("inventory")
    )

# =========================================================
# CASHIER
# =========================================================

@app.route("/cashier")
def cashier():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    products_data = conn.execute(
        """
        SELECT *
        FROM products
        WHERE stock > 0
        ORDER BY product_name ASC
        """
    ).fetchall()


    # =========================
    # AMBIL CART DARI SESSION
    # =========================

    cart = session.get("cart", {})

    cart_items = []

    total = 0


    for product_id, quantity in cart.items():

        product = conn.execute(
            """
            SELECT *
            FROM products
            WHERE id = ?
            """,
            (int(product_id),)
        ).fetchone()


        if product:

            quantity = int(quantity)

            subtotal = (
                product["price"] * quantity
            )

            total += subtotal


            cart_items.append({
                "id": product["id"],
                "product_code": product["product_code"],
                "product_name": product["product_name"],
                "price": product["price"],
                "stock": product["stock"],
                "quantity": quantity,
                "subtotal": subtotal
            })


    conn.close()


    return render_template(
        "cashier.html",
        store_name=STORE_NAME,
        products=products_data,
        cart_items=cart_items,
        total=total
    )


# =========================================================
# ADD PRODUCT USING BARCODE
# =========================================================

@app.route(
    "/cashier/scan",
    methods=["POST"]
)
def cashier_scan():

    if "user_id" not in session:
        return redirect(url_for("login"))

    barcode = request.form.get(
        "barcode",
        ""
    ).strip()


    if not barcode:

        flash("Masukkan atau scan barcode produk.")

        return redirect(
            url_for("cashier")
        )


    conn = get_db_connection()


    product = conn.execute(
        """
        SELECT *
        FROM products
        WHERE barcode = ?
        """,
        (barcode,)
    ).fetchone()


    conn.close()


    if product is None:

        flash("Barcode produk tidak ditemukan.")

        return redirect(
            url_for("cashier")
        )


    if product["stock"] <= 0:

        flash("Stok produk habis.")

        return redirect(
            url_for("cashier")
        )


    cart = session.get(
        "cart",
        {}
    )


    product_key = str(
        product["id"]
    )


    current_quantity = int(
        cart.get(
            product_key,
            0
        )
    )


    if current_quantity >= product["stock"]:

        flash(
            "Jumlah di keranjang sudah mencapai stok tersedia."
        )

        return redirect(
            url_for("cashier")
        )


    cart[product_key] = (
        current_quantity + 1
    )


    session["cart"] = cart

    session.modified = True


    flash(
        f"{product['product_name']} ditambahkan ke keranjang."
    )


    return redirect(
        url_for("cashier")
    )


# =========================================================
# ADD PRODUCT MANUALLY
# =========================================================

@app.route(
    "/cashier/add/<int:product_id>",
    methods=["POST"]
)
def cashier_add(product_id):

    if "user_id" not in session:
        return redirect(url_for("login"))


    conn = get_db_connection()


    product = conn.execute(
        """
        SELECT *
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    ).fetchone()


    conn.close()


    if product is None:

        flash("Produk tidak ditemukan.")

        return redirect(
            url_for("cashier")
        )


    if product["stock"] <= 0:

        flash("Stok produk habis.")

        return redirect(
            url_for("cashier")
        )


    cart = session.get(
        "cart",
        {}
    )


    product_key = str(
        product_id
    )


    current_quantity = int(
        cart.get(
            product_key,
            0
        )
    )


    if current_quantity >= product["stock"]:

        flash(
            "Jumlah di keranjang sudah mencapai stok tersedia."
        )

        return redirect(
            url_for("cashier")
        )


    cart[product_key] = (
        current_quantity + 1
    )


    session["cart"] = cart

    session.modified = True


    return redirect(
        url_for("cashier")
    )


# =========================================================
# UPDATE CART
# =========================================================

@app.route(
    "/cashier/update/<int:product_id>",
    methods=["POST"]
)
def cashier_update(product_id):

    if "user_id" not in session:
        return redirect(url_for("login"))


    try:

        quantity = int(
            request.form["quantity"]
        )

    except ValueError:

        quantity = 1


    conn = get_db_connection()


    product = conn.execute(
        """
        SELECT *
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    ).fetchone()


    conn.close()


    if product is None:

        flash("Produk tidak ditemukan.")

        return redirect(
            url_for("cashier")
        )


    cart = session.get(
        "cart",
        {}
    )


    product_key = str(
        product_id
    )


    if quantity <= 0:

        cart.pop(
            product_key,
            None
        )

    elif quantity > product["stock"]:

        flash(
            f"Stok hanya tersedia {product['stock']}."
        )

        return redirect(
            url_for("cashier")
        )

    else:

        cart[product_key] = quantity


    session["cart"] = cart

    session.modified = True


    return redirect(
        url_for("cashier")
    )


# =========================================================
# REMOVE FROM CART
# =========================================================

@app.route(
    "/cashier/remove/<int:product_id>",
    methods=["POST"]
)
def cashier_remove(product_id):

    if "user_id" not in session:
        return redirect(url_for("login"))


    cart = session.get(
        "cart",
        {}
    )


    cart.pop(
        str(product_id),
        None
    )


    session["cart"] = cart

    session.modified = True


    return redirect(
        url_for("cashier")
    )


# =========================================================
# CHECKOUT
# =========================================================

@app.route("/cashier/checkout", methods=["POST"])
def cashier_checkout():

    if "user_id" not in session:
        return redirect(url_for("login"))

    # Ambil isi keranjang
    cart = session.get("cart", {})

    if not cart:
        flash("Keranjang masih kosong.")
        return redirect(url_for("cashier"))

    # Ambil metode pembayaran
    payment_method = request.form.get(
        "payment_method",
        "Cash"
    )

    conn = get_db_connection()

    try:

        total = 0
        checkout_items = []

        # ==================================
        # VALIDASI CART
        # ==================================

        for product_id, quantity in cart.items():

            product = conn.execute(
                """
                SELECT *
                FROM products
                WHERE id = ?
                """,
                (int(product_id),)
            ).fetchone()

            if product is None:
                raise Exception(
                    "Produk tidak ditemukan."
                )

            quantity = int(quantity)

            if quantity <= 0:
                raise Exception(
                    "Jumlah produk tidak valid."
                )

            if quantity > product["stock"]:
                raise Exception(
                    f"Stok {product['product_name']} tidak mencukupi."
                )

            subtotal = (
                product["price"] * quantity
            )

            total += subtotal

            checkout_items.append({
                "product": product,
                "quantity": quantity,
                "subtotal": subtotal
            })


        # ==================================
        # PROSES PEMBAYARAN
        # ==================================

        if payment_method == "Cash":

            try:

                payment = float(
                    request.form.get(
                        "payment",
                        0
                    )
                )

            except (ValueError, TypeError):

                flash(
                    "Nominal pembayaran tidak valid."
                )

                return redirect(
                    url_for("cashier")
                )


            if payment < total:

                flash(
                    "Uang pembayaran kurang."
                )

                return redirect(
                    url_for("cashier")
                )


            change_amount = (
                payment - total
            )


        elif payment_method in ["QRIS", "Debit Card"]:

            # Pembayaran non-tunai dianggap pas
            payment = total
            change_amount = 0


        else:

            raise Exception(
                "Metode pembayaran tidak valid."
            )


        # ==================================
        # GENERATE KODE TRANSAKSI
        # ==================================

        transaction_code = (
            "TRX"
            + datetime.now().strftime(
                "%Y%m%d%H%M%S%f"
            )
        )


        # ==================================
        # SIMPAN TRANSAKSI UTAMA
        # ==================================

        cursor = conn.execute(
            """
            INSERT INTO transactions
            (
                transaction_code,
                total,
                payment,
                change_amount,
                payment_method,
                cashier_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                transaction_code,
                total,
                payment,
                change_amount,
                payment_method,
                session["user_id"]
            )
        )

        transaction_id = (
            cursor.lastrowid
        )


        # ==================================
        # DETAIL TRANSAKSI
        # + KURANGI STOK
        # + INVENTORY LOG
        # ==================================

        for item in checkout_items:

            product = item["product"]
            quantity = item["quantity"]
            subtotal = item["subtotal"]


            # ------------------------------
            # SIMPAN DETAIL TRANSAKSI
            # ------------------------------

            conn.execute(
                """
                INSERT INTO transaction_details
                (
                    transaction_id,
                    product_id,
                    quantity,
                    price,
                    subtotal
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    transaction_id,
                    product["id"],
                    quantity,
                    product["price"],
                    subtotal
                )
            )


            # ------------------------------
            # KURANGI STOK PRODUK
            # ------------------------------

            conn.execute(
                """
                UPDATE products
                SET stock = stock - ?
                WHERE id = ?
                """,
                (
                    quantity,
                    product["id"]
                )
            )


            # ------------------------------
            # CATAT STOCK OUT
            # ------------------------------

            conn.execute(
                """
                INSERT INTO inventory_logs
                (
                    product_id,
                    movement_type,
                    quantity,
                    note,
                    user_id
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    product["id"],
                    "OUT",
                    quantity,
                    f"Sale {transaction_code}",
                    session["user_id"]
                )
            )


        # ==================================
        # SIMPAN DATABASE
        # ==================================

        conn.commit()


        # ==================================
        # KOSONGKAN KERANJANG
        # ==================================

        session["cart"] = {}
        session.modified = True


        # ==================================
        # BUKA HALAMAN STRUK
        # ==================================

        return redirect(
            url_for(
                "receipt",
        transaction_id=transaction_id
    )
)


    except Exception as error:

        conn.rollback()

        print(
            "CHECKOUT ERROR:",
            error
        )

        flash(
            str(error)
        )


    finally:

        conn.close()


    return redirect(
        url_for("cashier")
    )

# =========================================================
# TRANSACTIONS
# =========================================================

@app.route("/transactions")
def transactions():

    if "user_id" not in session:
        return redirect(url_for("login"))

    search = request.args.get(
        "search",
        ""
    ).strip()

    conn = get_db_connection()


    if search:

        transactions_data = conn.execute(
            """
            SELECT
                transactions.*,
                users.username AS cashier_name

            FROM transactions

            LEFT JOIN users
                ON transactions.cashier_id = users.id

            WHERE transactions.transaction_code LIKE ?
               OR users.username LIKE ?
               OR transactions.payment_method LIKE ?

            ORDER BY transactions.id DESC
            """,
            (
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            )
        ).fetchall()

    else:

        transactions_data = conn.execute(
            """
            SELECT
                transactions.*,
                users.username AS cashier_name

            FROM transactions

            LEFT JOIN users
                ON transactions.cashier_id = users.id

            ORDER BY transactions.id DESC
            """
        ).fetchall()


    total_transactions = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM transactions
        """
    ).fetchone()["total"]


    total_sales = conn.execute(
        """
        SELECT COALESCE(SUM(total), 0) AS total
        FROM transactions
        """
    ).fetchone()["total"]


    conn.close()


    return render_template(
        "transactions.html",
        store_name=STORE_NAME,
        transactions=transactions_data,
        total_transactions=total_transactions,
        total_sales=total_sales,
        search=search
    )


# =========================================================
# TRANSACTION DETAIL
# =========================================================

@app.route("/transactions/<int:transaction_id>")
def transaction_detail(transaction_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()


    transaction = conn.execute(
        """
        SELECT
            transactions.*,
            users.username AS cashier_name

        FROM transactions

        LEFT JOIN users
            ON transactions.cashier_id = users.id

        WHERE transactions.id = ?
        """,
        (transaction_id,)
    ).fetchone()


    if transaction is None:

        conn.close()

        flash("Transaksi tidak ditemukan.")

        return redirect(
            url_for("transactions")
        )


    details = conn.execute(
        """
        SELECT
            transaction_details.*,
            products.product_name,
            products.product_code

        FROM transaction_details

        JOIN products
            ON transaction_details.product_id = products.id

        WHERE transaction_details.transaction_id = ?

        ORDER BY transaction_details.id ASC
        """,
        (transaction_id,)
    ).fetchall()


    conn.close()


    return render_template(
        "transaction_detail.html",
        store_name=STORE_NAME,
        transaction=transaction,
        details=details
    )

# =========================================================
# RECEIPT
# =========================================================

@app.route("/receipt/<int:transaction_id>")
def receipt(transaction_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    # Ambil data transaksi
    transaction = conn.execute(
        """
        SELECT
            transactions.*,
            users.username AS cashier_name
        FROM transactions

        LEFT JOIN users
            ON transactions.cashier_id = users.id

        WHERE transactions.id = ?
        """,
        (transaction_id,)
    ).fetchone()


    if transaction is None:

        conn.close()

        flash("Transaksi tidak ditemukan.")

        return redirect(
            url_for("transactions")
        )


    # Ambil item transaksi
    details = conn.execute(
        """
        SELECT
            transaction_details.*,
            products.product_name,
            products.product_code

        FROM transaction_details

        JOIN products
            ON transaction_details.product_id = products.id

        WHERE transaction_details.transaction_id = ?

        ORDER BY transaction_details.id ASC
        """,
        (transaction_id,)
    ).fetchall()


    conn.close()


    return render_template(
        "receipt.html",
        transaction=transaction,
        details=details,
        store_name=STORE_NAME
    )

# =========================================================
# SALES REPORT
# =========================================================

@app.route("/reports")
def reports():

    # Hanya Admin yang boleh mengakses Sales Report
    access = admin_only()

    if access:
        return access

    conn = get_db_connection()


    # ==================================
    # TOTAL SALES
    # ==================================

    total_sales = conn.execute(
        """
        SELECT COALESCE(SUM(total), 0) AS total
        FROM transactions
        """
    ).fetchone()["total"]


    # ==================================
    # TOTAL TRANSACTIONS
    # ==================================

    total_transactions = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM transactions
        """
    ).fetchone()["total"]


    # ==================================
    # TOTAL PRODUCTS SOLD
    # ==================================

    total_products_sold = conn.execute(
        """
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM transaction_details
        """
    ).fetchone()["total"]


    # ==================================
    # AVERAGE TRANSACTION
    # ==================================

    average_transaction = conn.execute(
        """
        SELECT COALESCE(AVG(total), 0) AS average
        FROM transactions
        """
    ).fetchone()["average"]


    # ==================================
    # TOP SELLING PRODUCTS
    # ==================================

    top_products = conn.execute(
        """
        SELECT
            products.product_name,
            products.category,
            SUM(transaction_details.quantity) AS total_quantity,
            SUM(transaction_details.subtotal) AS total_revenue

        FROM transaction_details

        JOIN products
            ON transaction_details.product_id = products.id

        GROUP BY
            products.id,
            products.product_name,
            products.category

        ORDER BY total_quantity DESC

        LIMIT 5
        """
    ).fetchall()


    # ==================================
    # RECENT TRANSACTIONS
    # ==================================

    recent_transactions = conn.execute(
        """
        SELECT
            transactions.*,
            users.username AS cashier_name

        FROM transactions

        LEFT JOIN users
            ON transactions.cashier_id = users.id

        ORDER BY transactions.id DESC

        LIMIT 5
        """
    ).fetchall()


    conn.close()


    return render_template(
        "reports.html",
        store_name=STORE_NAME,
        total_sales=total_sales,
        total_transactions=total_transactions,
        total_products_sold=total_products_sold,
        average_transaction=average_transaction,
        top_products=top_products,
        recent_transactions=recent_transactions
    )

# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    # Menghapus semua session user
    session.clear()

    flash("Anda berhasil logout.")

    return redirect(url_for("login"))


# =========================================================
# MENJALANKAN APLIKASI
# =========================================================

if __name__ == "__main__":
    app.run(debug=False)
