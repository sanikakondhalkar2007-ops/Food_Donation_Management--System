from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "food_donation_secret_key"

DATABASE = "database.db"


# Connect to database
def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# Create database tables
def init_db():
    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_id INTEGER NOT NULL,
            food_name TEXT NOT NULL,
            quantity TEXT NOT NULL,
            description TEXT,
            location TEXT NOT NULL,
            status TEXT DEFAULT 'Available',
            receiver_id INTEGER,
            FOREIGN KEY (donor_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
    """)

    # Create default admin account
    admin = connection.execute(
        "SELECT * FROM users WHERE email = ?",
        ("admin@gmail.com",)
    ).fetchone()

    if not admin:
        connection.execute(
            """
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
            """,
            (
                "Administrator",
                "admin@gmail.com",
                generate_password_hash("admin123"),
                "admin"
            )
        )

    connection.commit()
    connection.close()


# Home page
@app.route("/")
def index():
    return render_template("index.html")


# Register
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        connection = get_db()

        existing_user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:
            connection.close()
            flash("Email already registered.")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        connection.execute(
            """
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
            """,
            (name, email, hashed_password, role)
        )

        connection.commit()
        connection.close()

        flash("Registration successful. Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_db()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]

            if user["role"] == "donor":
                return redirect(url_for("donor_dashboard"))

            elif user["role"] == "receiver":
                return redirect(url_for("receiver_dashboard"))

            elif user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))

        flash("Invalid email or password.")

    return render_template("login.html")


# Logout
@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.")

    return redirect(url_for("index"))


# Donor dashboard
@app.route("/donor_dashboard")
def donor_dashboard():

    if "user_id" not in session or session["role"] != "donor":
        return redirect(url_for("login"))

    connection = get_db()

    donations = connection.execute(
        """
        SELECT * FROM donations
        WHERE donor_id = ?
        ORDER BY id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    connection.close()

    return render_template(
        "donor_dashboard.html",
        donations=donations
    )


# Donate food
@app.route("/donate_food", methods=["GET", "POST"])
def donate_food():

    if "user_id" not in session or session["role"] != "donor":
        return redirect(url_for("login"))

    if request.method == "POST":

        food_name = request.form["food_name"]
        quantity = request.form["quantity"]
        description = request.form["description"]
        location = request.form["location"]

        connection = get_db()

        connection.execute(
            """
            INSERT INTO donations
            (donor_id, food_name, quantity, description, location)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                food_name,
                quantity,
                description,
                location
            )
        )

        connection.commit()
        connection.close()

        flash("Food donation added successfully.")

        return redirect(url_for("donor_dashboard"))

    return render_template("donate_food.html")


# All available donations
@app.route("/donations")
def donations():

    connection = get_db()

    donations = connection.execute(
        """
        SELECT donations.*, users.name AS donor_name
        FROM donations
        JOIN users ON donations.donor_id = users.id
        WHERE donations.status = 'Available'
        ORDER BY donations.id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "donations.html",
        donations=donations
    )


# Receiver dashboard
@app.route("/receiver_dashboard")
def receiver_dashboard():

    if "user_id" not in session or session["role"] != "receiver":
        return redirect(url_for("login"))

    connection = get_db()

    donations = connection.execute(
        """
        SELECT donations.*, users.name AS donor_name
        FROM donations
        JOIN users ON donations.donor_id = users.id
        WHERE donations.status = 'Available'
        ORDER BY donations.id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "receiver_dashboard.html",
        donations=donations
    )


# Receiver claims food
@app.route("/claim/<int:donation_id>")
def claim_donation(donation_id):

    if "user_id" not in session or session["role"] != "receiver":
        return redirect(url_for("login"))

    connection = get_db()

    connection.execute(
        """
        UPDATE donations
        SET status = 'Claimed',
            receiver_id = ?
        WHERE id = ?
        AND status = 'Available'
        """,
        (session["user_id"], donation_id)
    )

    connection.commit()
    connection.close()

    flash("Food donation claimed successfully.")

    return redirect(url_for("receiver_dashboard"))


# Admin dashboard
@app.route("/admin_dashboard")
def admin_dashboard():

    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    connection = get_db()

    users = connection.execute(
        "SELECT * FROM users ORDER BY id DESC"
    ).fetchall()

    donations = connection.execute(
        """
        SELECT donations.*,
               donor.name AS donor_name,
               receiver.name AS receiver_name
        FROM donations
        LEFT JOIN users AS donor
        ON donations.donor_id = donor.id
        LEFT JOIN users AS receiver
        ON donations.receiver_id = receiver.id
        ORDER BY donations.id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "admin_dashboard.html",
        users=users,
        donations=donations
    )


# Run application
if __name__ == "__main__":
    init_db()
    app.run(debug=True)