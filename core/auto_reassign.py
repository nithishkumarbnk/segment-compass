import pandas as pd
import joblib
from datetime import datetime, timedelta

# =============================
# PATHS
# =============================
EVENT_LOG_PATH = "data/processed/event_log.csv"
LRFMS_PATH = "data/processed/customer_lrfms.csv"
TIERS_PATH = "data/processed/customer_tiers.csv"
INTEL_PATH = "data/processed/customer_intelligence.csv"
TRANSITION_LOG_PATH = "data/processed/tier_transition_log.csv"

# =============================
# TIER DEFINITIONS
# =============================
TIER_ORDER = ["New", "Bronze", "Silver", "Gold", "Platinum"]
TIER_RANK = {tier: idx for idx, tier in enumerate(TIER_ORDER)}

# =============================
# LOAD MODEL
# =============================
rf = joblib.load("models/rf_model.pkl")

# =============================
# LOAD DATA
# =============================
events = pd.read_csv(EVENT_LOG_PATH)
lrfms = pd.read_csv(LRFMS_PATH)
tiers = pd.read_csv(TIERS_PATH)
intel = pd.read_csv(INTEL_PATH)

# =============================
# LOAD / INIT TRANSITION LOG
# =============================
try:
    transition_log = pd.read_csv(TRANSITION_LOG_PATH)
    transition_log["transition_time"] = pd.to_datetime(
        transition_log["transition_time"]
    )
except FileNotFoundError:
    transition_log = pd.DataFrame(columns=[
        "customer_id",
        "old_tier",
        "new_tier",
        "trigger_reason",
        "transition_time"
    ])

# =============================
# FILTER PURCHASE EVENTS
# =============================
purchase_events = events[events["event_type"] == "purchase"]
if purchase_events.empty:
    print("No purchase events found.")
    exit()

# =============================
# PROCESS PER CUSTOMER (SINGLE LOOP)
# =============================
for customer_id, group in purchase_events.groupby("customer_id"):

    event_count = len(group)
    monetary_sum = group["price"].sum()

    # -------------------------
    # AUTO TRIGGER
    # -------------------------
    if not (
        event_count == 1 or
        event_count % 5 == 0 or
        monetary_sum >= 10000
    ):
        continue

    # -------------------------
    # FETCH LRFMS
    # -------------------------
    idx = lrfms[lrfms["Customer ID"] == customer_id].index
    if len(idx) == 0:
        continue

    # -------------------------
    # UPDATE LRFMS
    # -------------------------
    lrfms.loc[idx, "F"] += event_count
    lrfms.loc[idx, "M"] += monetary_sum
    lrfms.loc[idx, "R"] = 0

    # -------------------------
    # PREDICT TIER + CONFIDENCE
    # -------------------------
    X = lrfms.loc[idx, ["L", "R", "F", "M", "S"]]
    new_tier = rf.predict(X)[0]
    confidence = rf.predict_proba(X).max()

    if confidence < 0.7:
        continue

    # -------------------------
    # GET OLD TIER
    # -------------------------
    old_tier = tiers.loc[
        tiers["Customer ID"] == customer_id, "tier"
    ].values[0]

    old_rank = TIER_RANK[old_tier]
    new_rank = TIER_RANK.get(new_tier, old_rank)

    # =============================
    # GUARDRAILS
    # =============================

    # Cold start rule
    if old_tier == "New":
        new_tier = "Bronze"
        new_rank = TIER_RANK["Bronze"]

    # Max one-tier jump
    if new_rank - old_rank > 1:
        new_tier = TIER_ORDER[old_rank + 1]
        new_rank = old_rank + 1

    # =============================
    # CONTROLLED DOWNGRADING LOGIC
    # =============================
    if new_rank < old_rank:
        inactivity = lrfms.loc[idx, "R"].values[0]

        last_upgrade = transition_log[
            (transition_log["customer_id"] == customer_id) &
            (transition_log["new_tier"].isin(["Silver", "Gold", "Platinum"]))
        ]

        downgrade_allowed = (
            inactivity > 60 and
            confidence >= 0.7 and
            (
                last_upgrade.empty or
                (datetime.now() - last_upgrade["transition_time"].max()).days > 30
            )
        )

        if not downgrade_allowed:
            continue

        # Allow only one-tier downgrade
        new_tier = TIER_ORDER[old_rank - 1]
        new_rank = old_rank - 1

    # -------------------------
    # APPLY TIER UPDATE
    # -------------------------
    if new_tier == old_tier:
        continue

    tiers.loc[tiers["Customer ID"] == customer_id, "tier"] = new_tier

    # -------------------------
    # UPDATE INTELLIGENCE
    # -------------------------
    intel_idx = intel[intel["Customer ID"] == customer_id].index
    if len(intel_idx) > 0:
        intel.loc[intel_idx, "tier"] = new_tier

        if new_tier in ["Gold", "Platinum"]:
            intel.loc[intel_idx, "risk_flag"] = "Low Risk"
            intel.loc[intel_idx, "stability_score"] = 0.8
        elif new_tier == "Silver":
            intel.loc[intel_idx, "risk_flag"] = "Medium Risk"
            intel.loc[intel_idx, "stability_score"] = 0.5
        else:
            intel.loc[intel_idx, "risk_flag"] = "High Risk"
            intel.loc[intel_idx, "stability_score"] = 0.3

    # -------------------------
    # TRANSITION LOG
    # -------------------------
    transition_log = pd.concat(
        [transition_log, pd.DataFrame([{
            "customer_id": customer_id,
            "old_tier": old_tier,
            "new_tier": new_tier,
            "trigger_reason": (
                f"events={event_count}, monetary={monetary_sum}, "
                f"confidence={confidence:.2f}"
            ),
            "transition_time": datetime.now()
        }])],
        ignore_index=True
    )

# =============================
# SAVE
# =============================
lrfms.to_csv(LRFMS_PATH, index=False)
tiers.to_csv(TIERS_PATH, index=False)
intel.to_csv(INTEL_PATH, index=False)
transition_log.to_csv(TRANSITION_LOG_PATH, index=False)

print("✅ Automatic tier reassignment with controlled downgrading completed.")
