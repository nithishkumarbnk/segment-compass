import pandas as pd
import shap
import joblib
import numpy as np

# -----------------------------
# Load data and model
# -----------------------------
df = pd.read_csv("data/processed/customer_tiers.csv")
X = df[["L", "R", "F", "M", "S"]]

rf = joblib.load("models/rf_model.pkl")

# -----------------------------
# Create SHAP explainer
# -----------------------------
explainer = shap.TreeExplainer(rf)
shap_output = explainer(X)

# -----------------------------
# HANDLE MULTI-CLASS SAFELY
# -----------------------------
# shap_output.values shape:
# (n_samples, n_features, n_classes)
shap_values = shap_output.values

# Compute mean |SHAP| across samples & classes
mean_abs_shap = np.mean(np.abs(shap_values), axis=(0, 2))

# -----------------------------
# Global Feature Importance
# -----------------------------
importance = pd.DataFrame({
    "feature": X.columns.tolist(),
    "importance": mean_abs_shap.tolist()
}).sort_values(by="importance", ascending=False)

importance.to_csv(
    "data/processed/global_feature_importance.csv",
    index=False
)

print("✅ Global SHAP feature importance generated")
print(importance)

# -----------------------------
# Local Explanation (One Customer)
# -----------------------------
sample_idx = 0
sample = X.iloc[[sample_idx]]

sample_shap = explainer(sample)
sample_values = sample_shap.values  # shape: (1, features, classes)

predicted_class = rf.predict(sample)[0]
class_index = list(rf.classes_).index(predicted_class)

print(f"\n🔍 Local explanation for Customer {df.iloc[sample_idx]['Customer ID']}")
print(f"Predicted Tier: {predicted_class}\n")

for feature, value in zip(X.columns, sample_values[0, :, class_index]):
    print(f"{feature}: {value:.4f}")
