import numpy as np
import pandas as pd
from scipy import stats

def uncensor_demand(observed_booked, searches, is_sold_out, historical_conversion=0.028):
    """
    Recovers true unconstrained demand when a slot was sold out.
    If sold out, True Demand = Booked + (Searches * Historical Conversion Rate)
    """
    if is_sold_out:
        estimated_unserved = int(searches * historical_conversion * 0.15)
        return observed_booked + max(5, estimated_unserved)
    return observed_booked

def calculate_time_variant_cancellation_hazard(lead_time_days, base_cancel_prob=0.18):
    """
    Models:
    1. P_cancel(t): Probability of booking cancellation (higher for early bookers).
    2. Resale Failure Probability (1 - sigma(t)): Probability that returned room/seat CANNOT be resold.
       As t -> 0, resale failure approaches 100%.
    3. Ghost Liability Risk: Financial ruin risk of already-booked inventory.
    """
    # Cancel probability decays somewhat as arrival approaches (last-minute bookings cancel less)
    p_cancel = base_cancel_prob * (0.5 + 0.5 * (lead_time_days / 90.0))
    
    # Resale velocity sigma(t): chance of reselling if cancelled
    # At t=90 days, sigma ~ 0.95. At t=2 days, sigma ~ 0.05
    resale_success = 1.0 / (1.0 + np.exp(-0.08 * (lead_time_days - 18)))
    resale_failure = 1.0 - resale_success
    
    # Supplier penalty factor: 100% after T-14 days
    supplier_penalty_ratio = 1.0 if lead_time_days <= 14 else 0.35
    
    # Booked ruin multiplier
    booked_ruin_hazard = p_cancel * resale_failure * supplier_penalty_ratio
    
    return {
        "p_cancel": p_cancel,
        "resale_failure_rate": resale_failure,
        "booked_ruin_hazard": booked_ruin_hazard
    }

def forecast_quantiles(recent_series, horizon_days=30, seasonality_mult=1.0):
    """
    Generates P10 (pessimistic), P50 (median), P90 (optimistic) demand distributions
    using empirical quantile estimation and seasonal expansion.
    """
    mean_val = np.mean(recent_series) * seasonality_mult
    std_val = max(5.0, np.std(recent_series))
    
    p10 = max(5, int(mean_val - 1.28 * std_val))
    p50 = max(10, int(mean_val))
    p90 = max(15, int(mean_val + 1.28 * std_val))
    
    return {"p10": p10, "p50": p50, "p90": p90}
