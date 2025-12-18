import os
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv

# =========================================================
# LOAD ENV
# =========================================================
load_dotenv()
MONGO_URI = os.environ["MONGO_URI"]

# =========================================================
# CONFIG
# =========================================================
DB_NAME = "segment_compass"
COLLECTION_NAME = "products"
EXCEL_PATH = "products.xlsx"

# =========================================================
# CONNECT TO MONGO
# =========================================================
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
products_col = db[COLLECTION_NAME]

# =========================================================
# LOAD EXCEL
# =========================================================
df = pd.read_excel(EXCEL_PATH)

# =========================================================
# VALIDATION
# =========================================================
required_cols = {
    "product_id",
    "product_name",
    "category",
    "price",
    "image_url",
    "segment_target",
    "popularity",
}

missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns: {missing}")

# =========================================================
# CLEAN & CONVERT (FLOAT POPULARITY)
# =========================================================

# product_id stays STRING (P101, etc.)
df["product_id"] = df["product_id"].astype(str).str.strip()

# price → float
df["price"] = pd.to_numeric(df["price"], errors="coerce")

# popularity → FLOAT (THIS IS THE CHANGE)
df["popularity"] = pd.to_numeric(df["popularity"], errors="coerce").fillna(0.0)

# remove broken rows
df = df.dropna(subset=["price"])

records = df.to_dict(orient="records")

# =========================================================
# OPTIONAL: CLEAR EXISTING PRODUCTS
# =========================================================
print("Deleting existing products...")
products_col.delete_many({})

# =========================================================
# INSERT
# =========================================================
result = products_col.insert_many(records)

print(f"Inserted {len(result.inserted_ids)} products successfully.")
