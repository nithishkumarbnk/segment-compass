import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score

# -----------------------------
# Load LRFMS dataset
# -----------------------------
df = pd.read_csv("data/processed/customer_lrfms.csv")

features = ["L", "R", "F", "M", "S"]
X = df[features]

# -----------------------------
# Scale features
# -----------------------------
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# -----------------------------
# Find optimal number of clusters
# -----------------------------
best_k = 2
best_score = -1

for k in range(2, 7):
    gmm = GaussianMixture(n_components=k, random_state=42)
    labels = gmm.fit_predict(X_scaled)

    score = silhouette_score(X_scaled, labels)
    print(f"k={k}, Silhouette Score={score:.4f}")

    if score > best_score:
        best_k = k
        best_score = score

print(f"\n✅ Optimal number of clusters: {best_k}")

# -----------------------------
# Train final GMM
# -----------------------------
final_gmm = GaussianMixture(
    n_components=best_k, random_state=42
)
df["cluster"] = final_gmm.fit_predict(X_scaled)

# -----------------------------
# Save clustered output
# -----------------------------
df.to_csv(
    "data/processed/customer_clusters.csv",
    index=False
)

print("✅ Phase 3 completed: GMM clustering applied")
print(df.head())




from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# -----------------------------
# Create business tier labels
# -----------------------------
df["score"] = df["F"] * df["M"]

df["tier"] = pd.qcut(
    df["score"],
    q=[0, 0.2, 0.5, 0.8, 1.0],
    labels=["Bronze", "Silver", "Gold", "Platinum"]
)

# -----------------------------
# Prepare data for classification
# -----------------------------
X = df[["L", "R", "F", "M", "S"]]
y = df["tier"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# -----------------------------
# Train Random Forest
# -----------------------------
rf = RandomForestClassifier(
    n_estimators=200,
    random_state=42
)
rf.fit(X_train, y_train)

accuracy = rf.score(X_test, y_test)
print(f"✅ Random Forest Accuracy: {accuracy:.4f}")

# -----------------------------
# Save final labeled dataset
# -----------------------------
df.to_csv(
    "data/processed/customer_tiers.csv",
    index=False
)

print("✅ Phase 4 completed: Business tiers assigned")

joblib.dump(rf, "models/rf_model.pkl")
print("✅ Random Forest model saved")