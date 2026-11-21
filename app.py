import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# Ensure local module import
sys.path.append(os.path.dirname(__file__))
from optimizer import solve_inventory_allocation
from forecast_engine import calculate_time_variant_cancellation_hazard, uncensor_demand

st.set_page_config(
    page_title="TBO OptiBuy AI - Procurement Cockpit",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Tech Styling
st.markdown("""
<style>
    .reportview-container {
        background: #0B192C;
    }
    .metric-card {
        background-color: #132744;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #1E3A5F;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-title {
        color: #94A3B8;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
    }
    .metric-val {
        color: #00D2FF;
        font-size: 26px;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# App Header
st.title("✈️ TBO OptiBuy AI")
st.markdown("### Autonomous B2B Travel Procurement & Dynamic Risk-Adjusted Capital Allocation")
st.markdown("*Optimizing hotel allotments and airline blocks across core Indian domestic and outbound corridors.*")
st.write("---")

# Load Synthetic Travel Dataset
@st.cache_data
def load_data():
    csv_path = os.path.join(os.path.dirname(__file__), "tbo_travel_dataset.csv")
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return None

df_raw = load_data()

# Sidebar Controls
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Airplane_silhouette.svg/1024px-Airplane_silhouette.svg.png", width=60)
st.sidebar.title("🎛️ Procurement Controls")

budget_cr = st.sidebar.slider("Total Capital Budget (₹ Crores)", min_value=0.5, max_value=10.0, value=2.5, step=0.5)
total_budget_inr = budget_cr * 10000000.0

lead_time = st.sidebar.slider("Days Remaining to Arrival Date (t)", min_value=1, max_value=90, value=45, step=1,
                              help="t=90 is far out (Seed stage); t=2 is last-minute check-in.")

risk_appetite = st.sidebar.slider("TBO Corporate Risk Tolerance (λ)", min_value=0.2, max_value=2.0, value=1.0, step=0.1,
                                  help="Higher values make the optimizer more risk-averse to unsold inventory.")

target_avail = st.sidebar.slider("Peak Season Availability Floor (%)", min_value=75, max_value=98, value=92, step=1) / 100.0

# Extract candidate slots from dataset
slots_meta = [
    {"slot_id": "HOTEL_GOA_5S", "name": "Goa Beachfront Luxury Resort", "type": "Hotel", "destination": "Goa", 
     "cost": 7500, "price": 10500, "p50_demand": 145, "p10_demand": 95, "contract": "Hard Pre-Buy", "max_capacity": 180},
    {"slot_id": "HOTEL_GOA_4S", "name": "Goa Candolim 4-Star Suites", "type": "Hotel", "destination": "Goa", 
     "cost": 4200, "price": 5800, "p50_demand": 210, "p10_demand": 130, "contract": "Soft Allotment", "max_capacity": 250},
    {"slot_id": "HOTEL_DXB_5S", "name": "Dubai Marina 5-Star Hotel", "type": "Hotel", "destination": "Dubai", 
     "cost": 11000, "price": 15500, "p50_demand": 240, "p10_demand": 160, "contract": "Hard Pre-Buy", "max_capacity": 300},
    {"slot_id": "HOTEL_DXB_4S", "name": "Dubai Downtown Business Hotel", "type": "Hotel", "destination": "Dubai", 
     "cost": 6800, "price": 9200, "p50_demand": 175, "p10_demand": 115, "contract": "Soft Allotment", "max_capacity": 220},
    {"slot_id": "HOTEL_JAI_PALACE", "name": "Jaipur Heritage Palace", "type": "Hotel", "destination": "Rajasthan", 
     "cost": 8500, "price": 12000, "p50_demand": 120, "p10_demand": 75, "contract": "Hard Pre-Buy", "max_capacity": 150},
    {"slot_id": "FLIGHT_DEL_DXB", "name": "DEL-DXB Morning Seat Block", "type": "Flight", "destination": "Dubai", 
     "cost": 14000, "price": 17200, "p50_demand": 190, "p10_demand": 125, "contract": "Hard Pre-Buy", "max_capacity": 200},
    {"slot_id": "FLIGHT_BOM_GOI", "name": "BOM-GOI Weekend Seat Block", "type": "Flight", "destination": "Goa", 
     "cost": 4800, "price": 6200, "p50_demand": 165, "p10_demand": 110, "contract": "Soft Allotment", "max_capacity": 180},
    {"slot_id": "HOTEL_HKT_RESORT", "name": "Phuket Seafront Pool Villas", "type": "Hotel", "destination": "Thailand", 
     "cost": 9200, "price": 13400, "p50_demand": 105, "p10_demand": 65, "contract": "Soft Allotment", "max_capacity": 120}
]

# Calculate time-decay hazard for current lead time
hazard_metrics = calculate_time_variant_cancellation_hazard(lead_time)
for s in slots_meta:
    s["cancel_hazard"] = hazard_metrics["booked_ruin_hazard"]

# Run Optimization Solver
results = solve_inventory_allocation(
    candidate_slots=slots_meta,
    total_budget=total_budget_inr,
    risk_tolerance=risk_appetite,
    peak_availability_floor=target_avail,
    lead_time_days=lead_time
)

# Top KPI Dashboard
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Budget Utilized</div>
        <div class="metric-val">₹{results['total_spent']/10000000:.2f} Cr</div>
        <div style="color: #94A3B8; font-size: 11px;">{results['budget_utilization']}% of allocated capital</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Expected Net Margin</div>
        <div class="metric-val" style="color: #10B981;">₹{results['total_expected_profit']/100000:.1f} Lakh</div>
        <div style="color: #94A3B8; font-size: 11px;">Expected ROI: {results['overall_roi_pct']}%</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Dynamic Hazard λ(t)</div>
        <div class="metric-val" style="color: #F59E0B;">{results['dynamic_lambda_t']}</div>
        <div style="color: #94A3B8; font-size: 11px;">Lead Time: {lead_time} days to arrival</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    resale_fail_pct = round(hazard_metrics['resale_failure_rate'] * 100, 1)
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Resale Failure Risk</div>
        <div class="metric-val" style="color: {'#EF4444' if resale_fail_pct > 50 else '#00D2FF'};">{resale_fail_pct}%</div>
        <div style="color: #94A3B8; font-size: 11px;">Late-Cancellation Default Penalty</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Tabs: Recommendations | Risk Curves | Uncensored Demand Analytics
tab1, tab2, tab3 = st.tabs(["📋 Nightly Procurement Plan", "📉 Time-Decay Risk Curves", "🔍 Hidden Demand Uncensoring"])

with tab1:
    st.subheader("Actionable Category Manager Buy Plan")
    st.write(f"Solver Status: **{results['status']}** | Re-planned for Lead Time **T-{lead_time} days**")
    
    df_alloc = pd.DataFrame(results["allocations"])
    
    # Format table for display
    df_display = df_alloc.copy()
    df_display["cost_per_unit"] = df_display["cost_per_unit"].apply(lambda x: f"₹{x:,.0f}")
    df_display["resell_price"] = df_display["resell_price"].apply(lambda x: f"₹{x:,.0f}")
    df_display["total_outlay"] = df_display["total_outlay"].apply(lambda x: f"₹{x:,.0f}")
    df_display["expected_net_margin"] = df_display["expected_net_margin"].apply(lambda x: f"₹{x:,.0f}")
    df_display["margin_pct"] = df_display["margin_pct"].apply(lambda x: f"{x}%")
    
    st.dataframe(df_display, use_container_width=True)
    
    # Download plan
    csv = df_alloc.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export Buy Plan to CSV", data=csv, file_name=f"TBO_Buy_Plan_T{lead_time}d.csv", mime="text/csv")

with tab2:
    st.subheader("Dynamic Hazard Rate & Cancellation Exposure over Lead Time")
    
    t_vals = np.linspace(90, 1, 100)
    T = 90
    lambda_spoil_vals = 0.40 * risk_appetite + 3.60 * risk_appetite * ((T - t_vals) / T) ** 2.4
    cancel_risks = [calculate_time_variant_cancellation_hazard(tv)['resale_failure_rate'] * 100 for tv in t_vals]
    
    fig, ax1 = plt.subplots(figsize=(10, 4.2), facecolor='#0B192C')
    ax1.set_facecolor('#132744')
    
    line1 = ax1.plot(t_vals, lambda_spoil_vals, color='#00D2FF', linewidth=3, label=r'Holding Spoilage Penalty $\lambda(t)$')
    ax1.set_xlabel('Lead Time Remaining to Arrival Date (Days)', color='#CBD5E1', fontsize=10)
    ax1.set_ylabel(r'Risk Aversion Multiplier $\lambda(t)$', color='#00D2FF', fontsize=10)
    ax1.tick_params(colors='#CBD5E1')
    ax1.set_xlim(90, 1)
    
    ax2 = ax1.twinx()
    line2 = ax2.plot(t_vals, cancel_risks, color='#F43F5E', linewidth=2.5, linestyle='--', label='Late-Cancellation Resale Failure %')
    ax2.set_ylabel('Cancellation Spoilage Probability (%)', color='#F43F5E', fontsize=10)
    ax2.tick_params(colors='#CBD5E1')
    
    # Vertical current position line
    ax1.axvline(lead_time, color='#F59E0B', linestyle=':', linewidth=2, label=f'Current Run: T-{lead_time}d')
    
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, facecolor='#0B192C', edgecolor='#1E3A5F', labelcolor='#FFFFFF', loc='upper right')
    
    for spine in ax1.spines.values():
        spine.set_color('#1E3A5F')
    for spine in ax2.spines.values():
        spine.set_color('#1E3A5F')
        
    st.pyplot(fig)
    st.info("💡 **Key Economic Insight**: Notice how both penalties remain low between T-90d and T-40d (allowing TBO to capture wholesale bulk discounts), then skyrocket between T-14d and T-1d to prevent dead inventory write-offs.")

with tab3:
    st.subheader("Look-to-Book Uncensored Demand Recovery")
    if df_raw is not None:
        sample_slot = st.selectbox("Select Inventory Slot to Inspect:", df_raw["slot_id"].unique())
        sub_df = df_raw[df_raw["slot_id"] == sample_slot].tail(90)
        
        st.write("Comparing **Observed Historical Bookings** vs. **Reconstructed True Unconstrained Demand**:")
        
        fig2, ax = plt.subplots(figsize=(10, 4), facecolor='#0B192C')
        ax.set_facecolor('#132744')
        
        ax.plot(pd.to_datetime(sub_df['date']), sub_df['unconstrained_demand'], color='#10B981', linewidth=2, label='Recovered True Unconstrained Demand')
        ax.plot(pd.to_datetime(sub_df['date']), sub_df['observed_booked'], color='#00D2FF', linewidth=1.8, linestyle='--', label='Observed Bookings (Capped at Sold-Out)')
        
        # Highlight sold out periods
        sold_out_dates = sub_df[sub_df['is_sold_out'] == 1]
        ax.scatter(pd.to_datetime(sold_out_dates['date']), sold_out_dates['observed_booked'], color='#EF4444', s=35, zorder=5, label='Sold-Out Truncation Point')
        
        ax.set_ylabel('Daily Room / Seat Demand', color='#CBD5E1')
        ax.tick_params(colors='#CBD5E1')
        ax.legend(facecolor='#0B192C', edgecolor='#1E3A5F', labelcolor='#FFFFFF')
        for spine in ax.spines.values():
            spine.set_color('#1E3A5F')
            
        st.pyplot(fig2)
        st.success("✅ **Uncensoring Engine**: When sold-out flags occur, OptiBuy analyzes agent search traffic and historical look-to-book conversion to estimate the demand TBO missed, ensuring the optimizer buys enough capacity for the next cycle.")
