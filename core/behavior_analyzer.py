import pandas as pd
import joblib
import numpy as np

# -----------------------------
# Load data and trained model
# -----------------------------
df = pd.read_csv("data/processed/customer_tiers.csv")

# Load trained Random Forest model
rf = joblib.load("models/rf_model.pkl") if False else None
# NOTE: model loading will be formalized later

# -----------------------------
# Risk & Stability Rules
# -----------------------------
df["risk_flag"] = np.where(
    (df["R"] > 90) | (df["S"] < 0.3),
    "High Risk",
    "Low Risk"
)

# -----------------------------
# Stability Score
# -----------------------------
df["stability_score"] = (
    1 - (df["R"] / df["R"].max())
) * df["S"]

# -----------------------------
# Save intelligence-enhanced data
# -----------------------------
df.to_csv(
    "data/processed/customer_intelligence.csv",
    index=False
)

print("✅ Phase 5 completed: Risk & stability analysis added")
print(df[["Customer ID", "tier", "risk_flag", "stability_score"]].head())
