import os
from datetime import datetime

import joblib
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

# =========================================================
# MONGO CONNECTION
# =========================================================
client = MongoClient(os.environ["MONGO_URI"])
db = client["segment_compass"]

events_col = db["events"]
lrfms_col = db["lrfms"]
tiers_col = db["tiers"]
customers_col = db["customers"]
transition_col = db["transitions"]

# =========================================================
# MODEL + CONSTANTS
# =========================================================
FEATURES = ["L", "R", "F", "M", "S"]

TIER_ORDER = ["New", "Bronze", "Silver", "Gold", "Platinum"]
TIER_RANK = {tier: idx for idx, tier in enumerate(TIER_ORDER)}

rf = joblib.load("models/rf_model.pkl")


# =========================================================
# RECOMPUTE CUSTOMER (AUTHORITATIVE)
# =========================================================
def recompute_customer(customer_id: int):
    """
    Recomputes:
    - LRFMS metrics (ALWAYS)
    - Tier transitions (GUARDED)
    """

    # -----------------------------------------------------
    # FETCH PURCHASE EVENTS
    # -----------------------------------------------------
    purchases = list(
        events_col.find(
            {"customer_id": customer_id, "event_type": "purchase"}, {"_id": 0}
        ).sort("event_time", 1)
    )

    if not purchases:
        return  # no events, nothing to compute

    # -----------------------------------------------------
    # AGGREGATES
    # -----------------------------------------------------
    event_count = len(purchases)
    monetary_sum = float(sum(e["price"] for e in purchases))

    last_purchase_time = purchases[-1]["event_time"]
    recency_days = max(0, (datetime.utcnow() - last_purchase_time).days)

    # -----------------------------------------------------
    # FETCH EXISTING LRFMS (OR INIT)
    # -----------------------------------------------------
    lrfms = lrfms_col.find_one({"customer_id": customer_id}) or {
        "L": 0,
        "S": 0.2,
    }

    # -----------------------------------------------------
    # UPDATE LRFMS (🔥 ALWAYS 🔥)
    # -----------------------------------------------------
    updated_lrfms = {
        "customer_id": customer_id,
        "L": int(lrfms.get("L", 0)),
        "R": int(recency_days),
        "F": int(event_count),
        "M": float(monetary_sum),
        "S": float(lrfms.get("S", 0.2)),
        "updated_at": datetime.utcnow(),
    }

    lrfms_col.update_one(
        {"customer_id": customer_id},
        {"$set": updated_lrfms},
        upsert=True,
    )

    # -----------------------------------------------------
    # 🔐 TIER TRIGGER CONDITIONS (ONLY FOR TIER)
    # -----------------------------------------------------
    if not (event_count == 1 or event_count % 5 == 0 or monetary_sum >= 10000):
        return  # metrics updated, tier unchanged

    # -----------------------------------------------------
    # CURRENT TIER
    # -----------------------------------------------------
    tier_doc = tiers_col.find_one({"customer_id": customer_id})
    old_tier = tier_doc["tier"] if tier_doc else "New"

    # -----------------------------------------------------
    # COLD START HANDLING
    # -----------------------------------------------------
    if old_tier == "New":
        new_tier = "Bronze"
        confidence = 1.0
    else:
        X = pd.DataFrame([[updated_lrfms[f] for f in FEATURES]], columns=FEATURES)
        new_tier = rf.predict(X)[0]
        confidence = float(rf.predict_proba(X).max())

        if confidence < 0.7:
            return  # model unsure → no tier change

    # -----------------------------------------------------
    # TIER GUARDS
    # -----------------------------------------------------
    old_rank = TIER_RANK[old_tier]
    new_rank = TIER_RANK[new_tier]

    # Max one-tier jump
    if new_rank - old_rank > 1:
        new_tier = TIER_ORDER[old_rank + 1]
        new_rank = old_rank + 1

    # Downgrade protection (30 days)
    if new_rank < old_rank:
        last_transition = transition_col.find_one(
            {"customer_id": customer_id},
            sort=[("transition_time", -1)],
        )
        if last_transition:
            days_since = (datetime.utcnow() - last_transition["transition_time"]).days
            if days_since < 30:
                return
        new_tier = TIER_ORDER[old_rank - 1]

    if new_tier == old_tier:
        return

    # -----------------------------------------------------
    # APPLY TIER UPDATES
    # -----------------------------------------------------
    tiers_col.update_one(
        {"customer_id": customer_id},
        {"$set": {"tier": new_tier}},
        upsert=True,
    )

    customers_col.update_one(
        {"customer_id": customer_id},
        {
            "$set": {
                "tier": new_tier,
                "risk_flag": (
                    "Low Risk"
                    if new_tier in ["Gold", "Platinum"]
                    else "Medium Risk" if new_tier == "Silver" else "High Risk"
                ),
                "stability_score": (
                    0.8
                    if new_tier in ["Gold", "Platinum"]
                    else 0.5 if new_tier == "Silver" else 0.3
                ),
                "updated_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )

    # -----------------------------------------------------
    # RECORD TRANSITION
    # -----------------------------------------------------
    transition_col.insert_one(
        {
            "customer_id": customer_id,
            "old_tier": old_tier,
            "new_tier": new_tier,
            "confidence": confidence,
            "event_count": event_count,
            "monetary_sum": monetary_sum,
            "transition_time": datetime.utcnow(),
        }
    )
