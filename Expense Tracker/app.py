from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from flask_mail import Mail, Message
from flask import url_for
import uuid
import datetime

app = Flask(__name__)

# Load Config FIRST
app.config.from_object(Config)

# Gmail Configuration
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "chaitanyanandoskar@gmail.com"
app.config["MAIL_PASSWORD"] = "nvrjrmdjrjavjhyk"
app.config["MAIL_DEFAULT_SENDER"] = "chaitanyanandoskar@gmail.com"

mail = Mail(app)

mysql = MySQL(app)

# ---------------- HOME ----------------
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Check password match
        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        cur = mysql.connection.cursor()

        # Check existing email
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        if user:
            cur.close()
            flash("Email already exists!", "danger")
            return redirect(url_for("register"))

        # Insert new user
        cur.execute(
            "INSERT INTO users(fullname, email, password) VALUES(%s, %s, %s)",
            (fullname, email, hashed_password)
        )

        mysql.connection.commit()
        cur.close()

        flash("Registration Successful!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["fullname"] = user["fullname"]
            return redirect(url_for("dashboard"))

        flash("Invalid email or password", "danger")

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- FORGOT PASSWORD ONLY ----------------
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form["email"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("forgot_password"))

        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )

        user = cur.fetchone()

        if user:

            hashed_password = generate_password_hash(new_password)

            cur.execute(
                """
                UPDATE users
                SET password=%s
                WHERE email=%s
                """,
                (hashed_password, email)
            )

            mysql.connection.commit()
            cur.close()

            flash(
                "Password reset successfully. Please login.",
                "success"
            )

            return redirect(url_for("login"))

        else:

            cur.close()

            flash(
                "Email not found.",
                "danger"
            )

            return redirect(url_for("forgot_password"))

    return render_template("forgot_password.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    uid = session["user_id"]
    cur = mysql.connection.cursor()

    cur.execute("SELECT IFNULL(SUM(amount),0) AS total_income FROM income WHERE user_id=%s", (uid,))
    income = cur.fetchone()["total_income"]

    cur.execute("SELECT IFNULL(SUM(amount),0) AS total_expense FROM expenses WHERE user_id=%s", (uid,))
    expense = cur.fetchone()["total_expense"]

    balance = float(income) - float(expense)

    cur.close()

    return render_template(
        "dashboard.html",
        income=income,
        expense=expense,
        balance=balance
    )


# ---------------- INCOME LIST ----------------
@app.route("/income")
def income():
    if "user_id" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()
    
    cur.execute(
        "SELECT * FROM income WHERE user_id=%s ORDER BY id ASC",
        (session["user_id"],)
    )
    
    data = cur.fetchall()
    cur.close()

    return render_template("income.html", incomes=data)


# ---------------- ADD INCOME ----------------
@app.route("/add_income", methods=["GET", "POST"])
def add_income():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        source = request.form["source"]
        amount = request.form["amount"]
        date = request.form["date"]

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO income(user_id, source, amount, income_date) VALUES(%s,%s,%s,%s)",
            (session["user_id"], source, amount, date)
        )
        mysql.connection.commit()
        cur.close()

        flash("Income added successfully")
        return redirect(url_for("income"))

    return render_template("add_income.html")


# ---------------- EXPENSE LIST ----------------
@app.route("/expenses")
def expenses():
    if "user_id" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT * FROM expenses WHERE user_id=%s ORDER BY expense_date DESC",
        (session["user_id"],)
    )
    data = cur.fetchall()
    cur.close()

    return render_template("expenses.html", expenses=data)


# ---------------- ADD EXPENSE ----------------
@app.route("/add_expense", methods=["GET", "POST"])
def add_expense():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        category = request.form["category"]
        description = request.form["description"]
        amount = request.form["amount"]
        date = request.form["date"]

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO expenses(user_id, category, description, amount, expense_date) VALUES(%s,%s,%s,%s,%s)",
            (session["user_id"], category, description, amount, date)
        )
        mysql.connection.commit()
        cur.close()

        flash("Expense added successfully")
        return redirect(url_for("expenses"))

    return render_template("add_expense.html")


# ---------------- REPORT ----------------
@app.route("/report")
def report():
    if "user_id" not in session:
        return redirect(url_for("login"))

    uid = session["user_id"]
    cur = mysql.connection.cursor()

    cur.execute("SELECT IFNULL(SUM(amount),0) AS total_income FROM income WHERE user_id=%s", (uid,))
    total_income = cur.fetchone()["total_income"]

    cur.execute("SELECT IFNULL(SUM(amount),0) AS total_expense FROM expenses WHERE user_id=%s", (uid,))
    total_expense = cur.fetchone()["total_expense"]

    balance = float(total_income) - float(total_expense)

    cur.execute("""
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE user_id=%s
        GROUP BY category
    """, (uid,))

    data = cur.fetchall()
    cur.close()

    return render_template(
        "report.html",
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        report=data
    )


# ---------------- PROFILE ----------------
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    uid = session["user_id"]
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM users WHERE id=%s", (uid,))
    user = cur.fetchone()

    cur.execute("SELECT IFNULL(SUM(amount),0) AS total_income FROM income WHERE user_id=%s", (uid,))
    total_income = cur.fetchone()["total_income"]

    cur.execute("SELECT IFNULL(SUM(amount),0) AS total_expense FROM expenses WHERE user_id=%s", (uid,))
    total_expense = cur.fetchone()["total_expense"]

    balance = float(total_income) - float(total_expense)

    cur.close()

    return render_template(
        "profile.html",
        user=user,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance
    )


# ---------------- DELETE INCOME ----------------
@app.route("/delete_income/<int:id>")
def delete_income(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()
    cur.execute(
        "DELETE FROM income WHERE id=%s AND user_id=%s",
        (id, session["user_id"])
    )
    mysql.connection.commit()
    cur.close()

    return redirect(url_for("income"))


# ---------------- DELETE EXPENSE ----------------
@app.route("/delete_expense/<int:id>")
def delete_expense(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()
    cur.execute(
        "DELETE FROM expenses WHERE id=%s AND user_id=%s",
        (id, session["user_id"])
    )
    mysql.connection.commit()
    cur.close()

    return redirect(url_for("expenses"))


# ---------------- TEST DB ----------------
@app.route("/test")
def test():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT DATABASE()")
        db = cur.fetchone()
        cur.close()
        return f"Connected successfully! Database: {db}"
    except Exception as e:
        return f"Connection failed: {e}"


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)