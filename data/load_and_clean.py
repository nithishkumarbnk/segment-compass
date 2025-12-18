import pandas as pd

# -----------------------------
# Load Excel dataset
# -----------------------------
df = pd.read_excel(
    "raw/online_retail.xlsx",
    engine="openpyxl"
)

print("Initial shape:", df.shape)

# -----------------------------
# Drop rows without CustomerID
# -----------------------------
df = df.dropna(subset=["Customer ID"])

# -----------------------------
# Remove cancelled transactions
# -----------------------------
df = df[~df["Invoice"].astype(str).str.startswith("C")]

# -----------------------------
# Convert data types
# -----------------------------
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
df["Customer ID"] = df["Customer ID"].astype(int)
df["Quantity"] = df["Quantity"].astype(int)
df["Price"] = df["Price"].astype(float)

# -----------------------------
# Remove invalid values
# -----------------------------
df = df[(df["Quantity"] > 0) & (df["Price"] > 0)]

# -----------------------------
# Compute Monetary value
# -----------------------------
df["TotalAmount"] = df["Quantity"] * df["Price"]

# -----------------------------
# Keep only required columns
# -----------------------------
df = df[
    [
        "Customer ID",
        "Invoice",
        "InvoiceDate",
        "Quantity",
        "Price",
        "TotalAmount",
    ]
]

# -----------------------------
# Save cleaned dataset
# -----------------------------
df.to_csv(
    "processed/transactions_clean.csv",
    index=False
)

print("✅ Phase 1 completed successfully.")
print("Final shape:", df.shape)
