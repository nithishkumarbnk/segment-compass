import pandas as pd
from sklearn.preprocessing import MinMaxScaler

# -----------------------------
# Load cleaned transaction data
# -----------------------------
df = pd.read_csv("data/processed/transactions_clean.csv")
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])

# -----------------------------
# Reference date for Recency
# -----------------------------
reference_date = df["InvoiceDate"].max()

# -----------------------------
# Aggregate to customer level
# -----------------------------
lrfm = df.groupby("Customer ID").agg(
    first_purchase=("InvoiceDate", "min"),
    last_purchase=("InvoiceDate", "max"),
    frequency=("Invoice", "nunique"),
    monetary=("TotalAmount", "sum"),
).reset_index()

# -----------------------------
# Compute L, R, F, M
# -----------------------------
lrfm["L"] = (lrfm["last_purchase"] - lrfm["first_purchase"]).dt.days
lrfm["R"] = (reference_date - lrfm["last_purchase"]).dt.days
lrfm["F"] = lrfm["frequency"]
lrfm["M"] = lrfm["monetary"]

# -----------------------------
# Normalize F and R for Satisfaction
# -----------------------------
scaler = MinMaxScaler()
lrfm[["F_norm", "R_norm"]] = scaler.fit_transform(
    lrfm[["F", "R"]]
)

# -----------------------------
# Derived Satisfaction Score
# -----------------------------
lrfm["S"] = (0.6 * lrfm["F_norm"]) + (0.4 * (1 - lrfm["R_norm"]))

# -----------------------------
# Final LRFMS dataset
# -----------------------------
lrfms = lrfm[["Customer ID", "L", "R", "F", "M", "S"]]

# -----------------------------
# Save output
# -----------------------------
lrfms.to_csv("data/processed/customer_lrfms.csv", index=False)

print("✅ Phase 2 completed: LRFMS features generated")
print(lrfms.head())
