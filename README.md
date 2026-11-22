# ✈️ TBO OptiBuy AI: Autonomous B2B Pre-Buy Optimization Engine

> **VOYAGEHACK 4.0 (TBO.com) — Inventory Optimization Challenge**  
> Dynamic Risk-Hedging, Pace & Pickup Forecasting, and Constrained Capital Allocation for Global B2B Travel Distribution.

---

## 📌 Executive Overview

TBO.com connects over **159,000+ travel agents and tour operators across 100+ countries** with hotels and airline capacity. In B2B travel distribution:
* **Airlines** serve as a high-frequency, low-margin (1.5%–3.0%) customer acquisition anchor.
* **Hotels** drive profitability (8.0%–15.0%+ net take-rates).
* **The Procurement Dilemma:** Locking in wholesale inventory 60–90 days in advance via **Hard Pre-Buys** yields 25%–40% discounts below spot API rates. However, heuristic-based procurement results in severe revenue leakage:
  1. **Perishable Inventory Spoilage ($C_o$):** Unsold rooms expire worthless at check-in ($t=0$), causing 100% loss of procurement capital and supplier penalties.
  2. **The "Booked Ghost" Risk:** Up to 25% of confirmed B2B bookings cancel between $T-14$ and $T-2$ days. Traditional systems treat booked rooms as safe, leaving buyers with toxic distressed stock.
  3. **Stockout & Agent Churn ($C_u$):** When an agent experiences a stockout on peak dates, they defect to competitor platforms (WebBeds, Hotelbeds). An alienated agency represents an average loss of **₹29.7 Lakhs in Customer Lifetime Value (CLV)**.

**TBO OptiBuy AI** replaces static spreadsheets with an autonomous, closed-loop procurement engine.

---

## 🏗️ Architecture & Pipeline

```
[Top-Down Macro Funnel]                  [Bottom-Up Pace & Pickup Tracker]
DGCA Flight Corridor Pax                 On-The-Books (OTB) Booking Velocity
Google Trends Search Momentum            De-seasonalized Pickup Multipliers
           │                                             │
           └──────────────────────┬──────────────────────┘
                                  ▼
                     Uncensored Demand Band 
                       (P10, P50, P90)
                                  │
                                  ▼
                [Dynamic Time-Varying Newsvendor]
                 Overage Cost C_o(t) vs Underage Cost C_u(t)
                 ==> Dynamic Critical Fractile CR(t)
                 ==> Slot Target Quantity Q*_i(t)
                                  │
                                  ▼
                [Constrained Portfolio Allocation LP]
            Global Weekly Budget (₹B) + Diversification Caps
            + Strategic Availability Floors (Search Guardrails)
                                  │
                                  ▼
                   Weekly Actionable Procurement Plan
```

---

## 📐 Mathematical Formulation

### 1. Dynamic Overage Cost: $C_o(t)$
Captures the holding spoilage loss if an acquired room remains unsold at lead time $t$:
$$C_o(t) = c(t) \cdot [1 - \sigma(t)] + \text{Penalty}_{\text{supplier}}(t)$$
* **$c(t)$:** Wholesale acquisition cost at lead time $t$.
* **$\sigma(t)$:** Resale probability function decaying as check-in approaches:
  $$\sigma(t) = \frac{1}{1 + \exp\left(-0.08 \cdot (t - 18)\right)}$$
* **$\text{Penalty}_{\text{supplier}}(t)$:** Contractual non-refundable penalties (0% before $T-14$, 50% between $T-14$ and $T-7$, 100% inside $T-7$).

### 2. Dynamic Underage Cost: $C_u(t)$
Integrates the complete business penalty of a stockout:

**Cᵤ(t) = [p(t) − c(t)] + P₍fail₎ · M₍comp₎ + P₍defect₎ · CLV₍agent₎**

The three terms represent **Direct Margin**, **Competitor Displacement**, and **Agency Lifetime Value at Risk**, respectively.
* **$P_{\text{defect}}$:** Probability of travel agent platform abandonment due to recurring peak-date stockouts.
* **$\text{CLV}_{\text{agent}}$:** Calibrated to **₹29.7 Lakhs** for high-volume Tier-1 agencies.

### 3. Dynamic Critical Fractile & Target $Q_i^*(t)$
$$CR_i(t) = \frac{C_{u,i}(t)}{C_{u,i}(t) + C_{o,i}(t)}$$
$$Q_i^*(t) = F_i^{-1}(CR_i(t))$$

### 4. Portfolio Linear Program (LP)
Reconciles target quantities across corridors under a global capital budget:
$$\max_{\{x_i\}} \sum_{i=1}^{N} \left[ (p_i - c_i) \cdot x_i - \lambda_i(t) \cdot \text{RiskPenalty}(x_i) \right] - \mu \cdot s$$

**Subject to:**
1. **Total Budget:** $\sum c_i(t) \cdot x_i \le B$
2. **Newsvendor Upper Bound:** $0 \le x_i \le Q_i^*(t)$
3. **Strategic Availability Floor:** $\sum_{i \in \text{peak}} x_i + s \ge \alpha \cdot \text{Demand}_{p50}$
4. **Corridor Exposure Cap:** $c_i(t) \cdot x_i \le 0.30 \cdot B$

---

## 📊 Backtest Results & ROI Validation

Benchmarked across **4 Anchor Corridors** (Goa, Dubai, Jaipur, Srinagar) against a static procurement baseline:

| Metric | Static Heuristic Baseline | OptiBuy Dynamic Engine | Business Impact |
| :--- | :--- | :--- | :--- |
| **Gross Margin** | 17.4% take-rate | **21.6% take-rate** | **+420 bps** margin expansion |
| **Inventory Spoilage** | 12.5% expired unsold | **4.0% expired unsold** | **-68%** spoilage reduction |
| **Peak Search Stockouts** | 18.0% zero-availability | **11.7% zero-availability** | **-35%** stockout reduction |

---

## 🚀 Getting Started

### Prerequisites
* Python 3.9+
* PuLP `<3.0.0` (pinned to 2.9.0 for stable solver bindings)

### Installation
```bash
git clone https://github.com/GadeshanaKoushik/tbo-optibuy-ai.git
cd tbo-optibuy-ai
pip install -r requirements.txt
```

### Run Decision Cockpit
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 📁 Repository Structure
```
tbo-optibuy-ai/
├── app.py                 # Streamlit Buyer Decision Cockpit (4 Interactive Tabs)
├── optimizer.py           # Dynamic Newsvendor & Constrained Portfolio LP Solver
├── forecast_engine.py     # Pace & Pickup Forecasting, Cancellation Hazard & Macro Funnel
├── data_generator.py      # Synthetic corridor historical booking & search generator
├── tbo_travel_dataset.csv # Calibrated multi-year corridor dataset
├── requirements.txt       # Dependencies (PuLP, Streamlit, Scipy, Pandas, Matplotlib)
└── README.md              # Project documentation
```
