import os
import uuid
import joblib
import pandas as pd
import numpy as np
import math
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for, flash
from pymongo import MongoClient
from dotenv import load_dotenv

# Import recompute logic
try:
    from core.recompute_mongo import recompute_customer
except ImportError:

    def recompute_customer(user_id):
        pass


load_dotenv()

app = Flask(__name__)
app.secret_key = "change_this_to_a_random_secret_key"

# =========================================================
# 1. DATABASE & MODEL
# =========================================================
try:
    client = MongoClient(os.environ["MONGO_URI"])
    db = client["segment_compass"]
    customers_col = db["customers"]
    products_col = db["products"]
    events_col = db["events"]
    tiers_col = db["tiers"]
    lrfms_col = db["lrfms"]
    transitions_col = db["transitions"]
except Exception as e:
    print(f"❌ Database connection failed: {e}")

try:
    rf_model = joblib.load("models/rf_model.pkl")
    print("✅ ML Model loaded successfully")
except:
    rf_model = None

FEATURES = ["L", "R", "F", "M", "S"]


# =========================================================
# 2. ROUTES
# =========================================================
@app.route("/")
def index():
    return render_template("landing.html")


# ✅ UPDATED: Uses ADMIN_PASS from .env
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        pwd = request.form.get("password")
        # Secure password check
        if pwd == os.environ.get("ADMIN_PASS"):
            session["role"] = "admin"
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid Password", "error")
    return render_template("admin_login.html")


@app.route("/login_as_customer")
def login_as_customer():
    if "user_id" not in session:
        first = customers_col.find_one()
        if first:
            session["user_id"] = first["customer_id"]
            # Safe Name handling
            raw_name = first.get("name", "Guest")
            session["user_name"] = raw_name
            session["role"] = "customer"
    return redirect(url_for("customer_dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/shop")
def customer_dashboard():
    if session.get("role") != "customer":
        return redirect(url_for("index"))
    user_id = session.get("user_id")

    # 1. Fetch User
    user = customers_col.find_one({"customer_id": user_id})
    if not user:
        user = {"customer_id": user_id, "name": "Guest", "tier": "New"}

    # Name Logic
    raw_name = user.get("name")
    if not raw_name:
        user["name"] = "Guest"
    display_name = str(user["name"]).split()[0]

    # Tier Logic
    if "tier" not in user:
        user["tier"] = "New"

    cart_count = events_col.count_documents(
        {"customer_id": user_id, "event_type": "purchase"}
    )

    # 2. Filtering Logic
    cat_filter = request.args.get("category", "All")

    if cat_filter == "All":
        all_products = list(products_col.find({}))
    else:
        all_products = list(products_col.find({"category": cat_filter}))

    # 3. PAGINATION LOGIC (NEW)
    page = int(request.args.get("page", 1))
    per_page = 10
    total_products = len(all_products)
    total_pages = math.ceil(total_products / per_page)

    # Slice the list for the current page
    start = (page - 1) * per_page
    end = start + per_page
    display_products = all_products[start:end]

    # 4. Recommendations
    recs = [p for p in all_products if p.get("segment_target") == user["tier"]][:4]

    # 5. Categories List
    raw_cats = products_col.distinct("category")
    categories = ["All"] + sorted([c for c in raw_cats if c])

    return render_template(
        "customer_dashboard.html",
        user=user,
        display_name=display_name,
        products=display_products,
        recommendations=recs,
        cart_count=cart_count,
        current_category=cat_filter,
        categories=categories,
        # Pagination Data
        current_page=page,
        total_pages=total_pages,
        total_products=total_products,
        per_page=per_page,
    )


@app.route("/switch_user", methods=["POST"])
def switch_user():
    try:
        new_id = int(request.form.get("customer_id"))
        cust = customers_col.find_one({"customer_id": new_id})

        if cust:
            session["user_id"] = new_id
            session["user_name"] = cust.get("name", "Guest")
            session["role"] = "customer"
            flash(f"Switched to user {new_id}")
        else:
            flash(f"User ID {new_id} not found.", "error")

    except ValueError:
        flash("Invalid ID format.", "error")

    return redirect(request.referrer or url_for("customer_dashboard"))


@app.route("/add_to_cart/<product_id>")
def add_to_cart(product_id):
    if session.get("role") != "customer":
        return redirect(url_for("index"))
    user_id = session.get("user_id")
    user = customers_col.find_one({"customer_id": user_id})
    product = products_col.find_one({"product_id": product_id})

    if product:
        current_tier = user.get("tier", "New") if user else "New"
        events_col.insert_one(
            {
                "event_id": str(uuid.uuid4()),
                "customer_id": user_id,
                "event_type": "purchase",
                "product_id": product_id,
                "event_time": datetime.utcnow(),
                "price": float(product["price"]),
                "quantity": 1,
                "tier_at_event": current_tier,
            }
        )
        recompute_customer(user_id)
        flash(f"Added {product['product_name']} to cart!")

    return redirect(
        url_for("customer_dashboard", category=request.args.get("current_cat", "All"))
    )


@app.route("/cart")
def view_cart():
    if session.get("role") != "customer":
        return redirect(url_for("index"))
    user_id = session.get("user_id")
    user = customers_col.find_one({"customer_id": user_id}) or {"name": "Guest"}
    display_name = str(user.get("name", "Guest")).split()[0]

    purchases = list(
        events_col.find({"customer_id": user_id, "event_type": "purchase"}).sort(
            "event_time", -1
        )
    )
    cart_items = []
    total = 0
    for p in purchases:
        prod = products_col.find_one({"product_id": p["product_id"]})
        if prod:
            cart_items.append(
                {
                    "name": prod["product_name"],
                    "price": p["price"],
                    "image": prod["image_url"],
                    "date": p["event_time"].strftime("%Y-%m-%d"),
                }
            )
            total += p["price"]

    return render_template(
        "cart.html",
        user=user,
        display_name=display_name,
        cart_items=cart_items,
        total=total,
    )


# --- ADMIN ROUTES ---


@app.route("/admin")
def admin_dashboard():
    # 1. Fetch & Sanitize List
    all_cust = list(
        customers_col.find({}, {"customer_id": 1, "name": 1, "email": 1}).sort(
            "customer_id", 1
        )
    )
    for c in all_cust:
        if not c.get("name"):
            c["name"] = "Guest"

    sel_id = request.args.get("customer_id")
    if not sel_id and all_cust:
        sel_id = all_cust[0]["customer_id"]
    if not sel_id:
        return render_template(
            "admin_dashboard.html", customers=[], cust={"name": "No Data"}, data={}
        )

    sel_id = int(sel_id)
    cust = customers_col.find_one({"customer_id": sel_id})
    if not cust:
        cust = {"customer_id": sel_id, "name": "Guest", "email": "N/A"}
    if not cust.get("name"):
        cust["name"] = "Guest"

    # 2. Metrics
    tier_doc = tiers_col.find_one({"customer_id": sel_id})
    lrfms_doc = lrfms_col.find_one({"customer_id": sel_id}) or {
        "L": 0,
        "R": 0,
        "F": 0,
        "M": 0,
        "S": 0,
    }
    for k in FEATURES:
        if k not in lrfms_doc:
            lrfms_doc[k] = 0

    data = {
        "tier": tier_doc["tier"] if tier_doc else "New",
        "lrfms": lrfms_doc,
        "risk": cust.get("risk_flag", "Unknown"),
        "stability": cust.get("stability_score", 0.0),
    }

    # 3. PAGINATION LOGIC FOR EVENTS
    page = int(request.args.get("page", 1))
    per_page = 10

    # Count total events for this user
    total_events = events_col.count_documents({"customer_id": sel_id})
    total_pages = math.ceil(total_events / per_page)

    # Fetch slice
    events = list(
        events_col.find({"customer_id": sel_id})
        .sort("event_time", -1)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )

    transitions = list(
        transitions_col.find({"customer_id": sel_id}).sort("transition_time", 1)
    )

    section = request.args.get("section", "Snapshot")
    sim_res = None

    # Simulation Logic
    if section == "Simulation" and rf_model:
        dF, dM, dR = (
            int(request.args.get("dF", 0)),
            float(request.args.get("dM", 0)),
            int(request.args.get("dR", 0)),
        )
        sim_vals = {
            "L": lrfms_doc["L"],
            "R": max(0, lrfms_doc["R"] + dR),
            "F": max(0, lrfms_doc["F"] + dF),
            "M": max(0, lrfms_doc["M"] + dM),
            "S": lrfms_doc["S"],
        }
        X = pd.DataFrame([[sim_vals[f] for f in FEATURES]], columns=FEATURES)
        sim_res = {
            "tier": rf_model.predict(X)[0],
            "conf": round(np.max(rf_model.predict_proba(X)) * 100, 1),
            "inputs": {"dF": dF, "dM": dM, "dR": dR},
        }

    return render_template(
        "admin_dashboard.html",
        customers=all_cust,
        current_id=sel_id,
        cust=cust,
        data=data,
        events=events,
        transitions=transitions,
        section=section,
        sim_result=sim_res,
        # Pagination Data
        current_page=page,
        total_pages=total_pages,
        total_events=total_events,
        per_page=per_page,
    )


@app.route("/admin/recompute/<int:user_id>")
def force_recompute(user_id):
    recompute_customer(user_id)
    flash(f"Metrics recalculated for User {user_id}")
    return redirect(url_for("admin_dashboard", customer_id=user_id, section="LRFMS"))


@app.route("/admin/add_customer", methods=["POST"])
def add_customer():
    name, email = request.form.get("name"), request.form.get("email")
    last = customers_col.find_one(sort=[("customer_id", -1)])
    new_id = (last["customer_id"] + 1) if last else 1000

    customers_col.insert_one(
        {
            "customer_id": new_id,
            "name": name,
            "email": email,
            "tier": "New",
            "risk_flag": "High Risk",
            "stability_score": 0.2,
            "created_at": datetime.utcnow(),
        }
    )
    lrfms_col.insert_one(
        {"customer_id": new_id, "L": 0, "R": 999, "F": 0, "M": 0, "S": 0.2}
    )
    tiers_col.insert_one({"customer_id": new_id, "tier": "New"})

    return redirect(url_for("admin_dashboard", customer_id=new_id))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
