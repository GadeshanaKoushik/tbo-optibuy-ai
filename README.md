# TBO OptiBuy AI

> **Autonomous B2B Travel Inventory Procurement & Dynamic Risk-Adjusted Capital Allocation**  
> *Developed for VOYAGEHACK 4.0 Hackathon Challenge: Inventory Optimization for TBO.com*

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io)

---

## 📌 Problem Overview
TBO.com is a global B2B travel distribution platform connecting 1M+ hotels and 750+ airlines to 159,000+ travel agents. This project solves TBO's core procurement challenge:
- **What to buy**: Optimizing hotel allotments and airline blocks across high-demand corridors (Goa, Dubai, Rajasthan, Thailand).
- **When to buy**: Managing perishable inventory expiry and lead-time hazard.
- **Under what contract**: Hard Pre-Buy vs. Soft Allotment with release date vs. Dynamic API.
- **At what price**: Dynamic B2B markup recommendations to maximize risk-adjusted gross margin under a fixed capital budget.

---

## 🚀 Key Innovations
1. **Dynamic Hazard Rate $\lambda(t)$**:
   - Risk is asymmetric in travel. Far from arrival ($t=90\text{d}$), the resale window is wide and supplier discounts are 30–35%.
   - Close to arrival ($t \to 0$), unsold rooms and late cancellations carry 100% terminal loss.
   - $\lambda(t)$ scales monotonically as $t \to 0$ to prevent late-stage spoilage write-offs.
2. **Late-Cancellation Hazard**:
   - Models the collapse of resale velocity $\sigma(t) \to 0$ and supplier non-refundable penalty cutoffs.
3. **Hidden Demand Uncensoring**:
   - Reconstructs unserved demand lost during sold-out states using search volumes and look-to-book ratios.
4. **Guaranteed Feasible MILP Optimizer**:
   - Budget-constrained Mixed-Integer Linear Program with soft availability floor ($-\mu \cdot s$) ensuring actionable nightly buy plans.

---

## 🛠️ Project Structure
```
tbo_optibuy/
├── app.py                # Interactive Streamlit Buyer Cockpit
├── optimizer.py          # MILP Solver (PuLP / CBC) with Dynamic Hazard λ(t)
├── forecast_engine.py    # Uncensored Demand & Cancellation Hazard Models
├── data_generator.py     # 2-Year Calibrated TBO Travel Dataset Generator
├── tbo_travel_dataset.csv# Calibrated transaction dataset (5,840 records)
├── requirements.txt      # Dependency specification
└── README.md             # Documentation
```

---

## 💻 Local Setup & Run

1. **Clone the repository:**
   ```bash
   git clone <REPO_URL>
   cd tbo_optibuy
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the Streamlit app:**
   ```bash
   streamlit run app.py
   ```
   Open `http://localhost:8501` in your browser.
