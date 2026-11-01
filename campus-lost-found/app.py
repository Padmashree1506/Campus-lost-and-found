# app.py - Campus Lost & Found System
# This is the main Flask file. It connects the website with the SQLite database.

from flask import Flask, render_template, request
import sqlite3
import csv
import os

app = Flask(__name__)

# Find the folder where app.py is saved, so the files are always found
# (this avoids problems when VS Code runs from a different folder)
BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_FOLDER, "database.db")
ITEMS_CSV = os.path.join(BASE_FOLDER, "items.csv")
CLAIMS_CSV = os.path.join(BASE_FOLDER, "claims.csv")

# Categories shown in the dropdown of the report forms
CATEGORIES = ["ID Card", "Book", "Electronics", "Bag", "Stationery",
              "Accessories", "Bottle/Lunch Box", "Other"]


# ---------------------------------------------------------
# DATABASE FUNCTIONS
# ---------------------------------------------------------

def get_connection():
    # Open a connection to the SQLite database file
    conn = sqlite3.connect(DATABASE)
    # This lets us use column names like item["item_name"] in the HTML
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    # Create the two tables if they do not exist yet
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            contact_name TEXT NOT NULL,
            contact_email TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            claimant_name TEXT NOT NULL,
            claimant_email TEXT NOT NULL,
            explanation TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def import_csv_data():
    # Load items.csv and claims.csv into the database.
    # INSERT OR IGNORE skips a row if its id already exists,
    # so restarting the app does not create duplicate records.
    conn = get_connection()

    if os.path.exists(ITEMS_CSV):
        # utf-8-sig also works if the file was saved by Excel
        file = open(ITEMS_CSV, newline="", encoding="utf-8-sig")
        reader = csv.DictReader(file)
        for row in reader:
            conn.execute(
                """INSERT OR IGNORE INTO items
                   (item_id, item_name, category, description, location,
                    date, status, contact_name, contact_email)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (row["item_id"], row["item_name"], row["category"],
                 row["description"], row["location"], row["date"],
                 row["status"], row["contact_name"], row["contact_email"])
            )
        file.close()

    if os.path.exists(CLAIMS_CSV):
        file = open(CLAIMS_CSV, newline="", encoding="utf-8-sig")
        reader = csv.DictReader(file)
        for row in reader:
            conn.execute(
                """INSERT OR IGNORE INTO claims
                   (claim_id, item_id, claimant_name, claimant_email, explanation)
                   VALUES (?, ?, ?, ?, ?)""",
                (row["claim_id"], row["item_id"], row["claimant_name"],
                 row["claimant_email"], row["explanation"])
            )
        file.close()

    conn.commit()
    conn.close()


# ---------------------------------------------------------
# HELPER FUNCTION FOR THE LOST AND FOUND FORMS
# (both forms are almost the same, so one function handles both)
# ---------------------------------------------------------

def handle_report(status, template_name):
    error = ""     # error text shown on the page
    message = ""   # success text shown on the page

    if request.method == "POST":
        # Read the form values and remove extra spaces
        item_name = request.form.get("item_name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        date = request.form.get("date", "").strip()
        contact_name = request.form.get("contact_name", "").strip()
        contact_email = request.form.get("contact_email", "").strip()

        # Validate: every field must be filled
        if (item_name == "" or category == "" or description == ""
                or location == "" or date == "" or contact_name == ""
                or contact_email == ""):
            error = "Please fill in all the fields."
        elif "@" not in contact_email:
            error = "Please enter a valid email address."
        elif category not in CATEGORIES:
            error = "Please choose a category from the list."
        else:
            # Save the item. The ? marks keep the SQL safe from SQL injection.
            conn = get_connection()
            conn.execute(
                """INSERT INTO items
                   (item_name, category, description, location, date,
                    status, contact_name, contact_email)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_name, category, description, location, date,
                 status, contact_name, contact_email)
            )
            conn.commit()
            conn.close()
            message = status + " item reported successfully!"

    return render_template(template_name, categories=CATEGORIES,
                           error=error, message=message)


# ---------------------------------------------------------
# ROUTES (each route is one page of the website)
# ---------------------------------------------------------

@app.route("/")
def index():
    # Home page: show the 5 most recently reported items
    conn = get_connection()
    items = conn.execute(
        "SELECT * FROM items ORDER BY item_id DESC LIMIT 5"
    ).fetchall()
    conn.close()
    return render_template("index.html", items=items)


@app.route("/report_lost", methods=["GET", "POST"])
def report_lost():
    return handle_report("Lost", "report_lost.html")


@app.route("/report_found", methods=["GET", "POST"])
def report_found():
    return handle_report("Found", "report_found.html")


@app.route("/items")
def view_items():
    # Read the search text and the filter choice from the URL
    search = request.args.get("search", "").strip()
    filter_status = request.args.get("filter", "All")

    # Start with a basic query. "WHERE 1=1" is always true,
    # so we can add more conditions after it using AND.
    sql = "SELECT * FROM items WHERE 1=1"
    values = []

    # Filter by Lost or Found
    if filter_status == "Lost" or filter_status == "Found":
        sql = sql + " AND status = ?"
        values.append(filter_status)

    # Search by item name or category
    if search != "":
        sql = sql + " AND (item_name LIKE ? OR category LIKE ?)"
        values.append("%" + search + "%")
        values.append("%" + search + "%")

    sql = sql + " ORDER BY item_id DESC"

    conn = get_connection()
    items = conn.execute(sql, values).fetchall()
    conn.close()

    return render_template("items.html", items=items,
                           search=search, filter=filter_status)


@app.route("/claim/<int:item_id>", methods=["GET", "POST"])
def claim(item_id):
    # Find the item that the person wants to claim
    conn = get_connection()
    item = conn.execute(
        "SELECT * FROM items WHERE item_id = ?", (item_id,)
    ).fetchone()

    # Only found items can be claimed
    if item is None or item["status"] != "Found":
        conn.close()
        return render_template("claim.html", item=None,
                               error="This item cannot be claimed.", message="")

    error = ""
    message = ""

    if request.method == "POST":
        claimant_name = request.form.get("claimant_name", "").strip()
        claimant_email = request.form.get("claimant_email", "").strip()
        explanation = request.form.get("explanation", "").strip()

        if claimant_name == "" or claimant_email == "" or explanation == "":
            error = "Please fill in all the fields."
        elif "@" not in claimant_email:
            error = "Please enter a valid email address."
        else:
            # Save the claim. The item itself is NOT changed or marked returned.
            conn.execute(
                """INSERT INTO claims
                   (item_id, claimant_name, claimant_email, explanation)
                   VALUES (?, ?, ?, ?)""",
                (item_id, claimant_name, claimant_email, explanation)
            )
            conn.commit()
            message = "Your claim request was submitted successfully!"

    conn.close()
    return render_template("claim.html", item=item, error=error, message=message)


# ---------------------------------------------------------
# START THE APP
# ---------------------------------------------------------

if __name__ == "__main__":
    create_tables()      # make the tables if needed
    import_csv_data()    # load the sample data (no duplicates)
    app.run(debug=True)  # start the website at http://127.0.0.1:5000
