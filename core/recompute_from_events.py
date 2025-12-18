import pandas as pd
import joblib
from datetime import datetime

# -----------------------------
# Load base data
# -----------------------------
lrfms = pd.read_csv("data/processed/customer_lrfms.csv")
events = pd.read_csv("data/processed/event_log.csv")
tiers = pd.read_csv("data/processed/customer_tiers.csv")

rf = joblib.load("models/rf_model.pkl")

# -----------------------------
# Filter purchase events only
# -----------------------------
purchase_events = events[events["event_type"] == "purchase"]

if purchase_events.empty:
    print("No purchase events to process.")
    exit()

# -----------------------------
# Aggregate event impact
# -----------------------------
event_agg = purchase_events.groupby("customer_id").agg(
    event_frequency=("event_id", "count"),
    event_monetary=("price", "sum"),
    last_event_time=("event_time", "max")
).reset_index()

event_agg["last_event_time"] = pd.to_datetime(event_agg["last_event_time"])

# -----------------------------
# Update LRFMS
# -----------------------------
for _, row in event_agg.iterrows():
    cid = row["customer_id"]

    idx = lrfms[lrfms["Customer ID"] == cid].index
    if len(idx) == 0:
        continue

    lrfms.loc[idx, "F"] += row["event_frequency"]
    lrfms.loc[idx, "M"] += row["event_monetary"]

    # Update Recency
    ref_date = pd.to_datetime(lrfms["R"].max(), errors="ignore")
    lrfms.loc[idx, "R"] = 0  # reset recency after activity

# -----------------------------
# Recompute tier
# -----------------------------
X = lrfms[["L", "R", "F", "M", "S"]]
tiers["tier"] = rf.predict(X)

# -----------------------------
# Save updated data
# -----------------------------
lrfms.to_csv("data/processed/customer_lrfms.csv", index=False)
tiers.to_csv("data/processed/customer_tiers.csv", index=False)

print("✅ Tier recomputation completed based on events.")
