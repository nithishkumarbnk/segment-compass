# 🧭 Segment Compass
### AI-Powered Customer Intelligence & E-Commerce Platform

**Segment Compass** is a dual-interface application designed to demonstrate advanced customer segmentation logic. It features a fully functional **Customer Shop** (Amazon-style) for generating behavioral data and an **Admin Console** for real-time analytics, LRFMS modeling, and predictive tier simulation.

---

## 🚀 Features

### 🛍️ Customer Shop (Frontend)
- **Modern UI/UX**: Responsive, Amazon-inspired interface with dynamic category navigation.
- **Smart Pagination**: Efficient browsing of large product catalogs (10 items per page).
- **Real-time Cart**: Add-to-cart actions trigger immediate backend event logging.
- **Personalized Recommendations**: Products suggested based on the user’s computed Tier (New, Bronze, Silver, Gold, Platinum).
- **User Switcher**: Sidebar utility to instantly switch between customer identities for testing.

### 📊 Admin Console (Backend Intelligence)
- **LRFMS Metrics Engine**: Automatically calculates **Length, Recency, Frequency, Monetary, and Satisfaction** scores for each user.
- **Predictive Simulator**: Forecasts tier changes based on behavioral deltas (e.g., additional ₹500 spend) using a Random Forest model.
- **Customer Journey Map**: Visual timeline of tier transitions with AI confidence scores.
- **Paginated Events Log**: Detailed user action history with server-side pagination (10 events per page).
- **Data Visualization**: Risk status and stability score snapshots.

---

## 🛠️ Tech Stack
- **Backend**: Python, Flask  
- **Database**: MongoDB (Local or Atlas)  
- **Frontend**: HTML5, CSS3, Jinja2, JavaScript  
- **Machine Learning**: Scikit-learn (Random Forest Classifier), Pandas, NumPy  
- **Containerization**: Docker  

---

## 📂 Project Structure

```text
/segment-compass
├── app.py                     # Main Flask application entry point
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker configuration
├── docker-compose.yml         # Container orchestration
├── .env                       # Environment variables (not committed)
├── core/
│   └── recompute_mongo.py     # LRFMS calculation & tier assignment logic
├── models/
│   └── rf_model.pkl           # Pre-trained Random Forest model
├── static/
│   ├── css/
│   │   └── style.css          # Global stylesheet
│   └── js/
│       └── main.js            # Frontend scripts
└── templates/
    ├── landing.html           # Entry page
    ├── admin_login.html       # Admin authentication
    ├── admin_dashboard.html   # Analytics dashboard
    ├── customer_dashboard.html# Shopping interface
    └── cart.html              # Cart view

⚡ Getting Started
Prerequisites

Python 3.9 or higher

MongoDB (Local on port 27017 or MongoDB Atlas)

1️⃣ Installation (Local)

Clone the repository

git clone https://github.com/yourusername/segment-compass.git
cd segment-compass


Install dependencies

pip install -r requirements.txt


Configure environment
Create a .env file in the root directory:

MONGO_URI=mongodb://localhost:27017/segment_compass
# Or for Atlas:
# mongodb+srv://<user>:<password>@cluster.mongodb.net/segment_compass


Run the application

python app.py


Access the app at: http://127.0.0.1:5000

2️⃣ Installation (Docker) 🐳

Build the image

docker build -t segment-compass .


Run the container

Note: If using local MongoDB, replace localhost with host.docker.internal in .env.

docker run -p 5000:5000 --env-file .env segment-compass

📖 Usage Guide
🛍️ For Customers

Open the Landing Page and select Customer Shop.

Auto-login as a guest or first available user.

Browse products via category navigation.

Add items to cart to generate purchase events.

Use the Switch ID sidebar tool to impersonate users and observe tier changes.

🔐 For Admins

Open the Landing Page and select Admin Console.

Login credentials:

Password:------

Dashboard capabilities:

Select users from the dropdown.

Refresh LRFMS metrics on demand.

Run simulations with ΔFrequency or ΔMonetary inputs to see AI predictions.

🤝 Contributing

Fork the repository

Create your feature branch

git checkout -b feature/AmazingFeature


Commit changes

git commit -m "Add AmazingFeature"


Push to branch

git push origin feature/AmazingFeature


Open a Pull Request
