import numpy as np
import pandas as pd
from scipy import stats

def uncensor_demand(observed_booked, searches, is_sold_out, historical_conversion=0.028):
    """
    Recovers true unconstrained demand when a slot was sold out (search spillover).
    True Demand = Observed Booked + (Unserved Searches * Historical Conversion Rate)
    """
    if is_sold_out:
        estimated_unserved = int(searches * historical_conversion * 0.15)
        return observed_booked + max(5, estimated_unserved)
    return observed_booked

def calculate_time_variant_cancellation_hazard(lead_time_days, base_cancel_prob=0.18):
    """
    Models time-varying cancellation dynamics:
    1. P_cancel(t): Probability of reservation cancellation before check-in.
    2. Resale Probability sigma(t): Decays to 0 as arrival date t -> 0.
    3. Resale Failure (1 - sigma(t)): Probability that returned inventory expires unsold (spoilage).
    4. Supplier Contractual Penalty: Escalates within T-14 and T-7 windows.
    """
    # Cancellation rate is highest for early bookers and stabilizes close to arrival
    p_cancel = base_cancel_prob * (0.50 + 0.50 * (lead_time_days / 90.0))
    
    # Resale velocity sigma(t): chance of successfully reselling a cancelled or distressed room
    # At t=90 days, sigma ~ 0.95. At t=18 days, sigma = 0.50. At t=2 days, sigma ~ 0.05
    resale_success = 1.0 / (1.0 + np.exp(-0.08 * (lead_time_days - 18.0)))
    resale_failure = 1.0 - resale_success
    
    # Contractual penalty tiers
    if lead_time_days > 14:
        supplier_penalty_rate = 0.00
    elif lead_time_days > 7:
        supplier_penalty_rate = 0.50
    else:
        supplier_penalty_rate = 1.00 # 100% non-refundable cutoff
        
    return {
        "p_cancel": p_cancel,
        "resale_success_rate": resale_success,
        "resale_failure_rate": resale_failure,
        "supplier_penalty_rate": supplier_penalty_rate
    }

def calculate_pace_and_pickup(otb_bookings, lead_time_days, corridor_type="leisure", dow=6, search_index=1.0):
    """
    Advanced Booking Curve & Pickup Engine:
    Predicts final realized demand from current On-The-Books (OTB) bookings using
    lead-time pickup curves normalized by Day-of-Week (DOW) and seasonality.
    
    Pickup Ratio = Final Realized Demand / OTB Bookings(t)
    """
    # Empirical base pickup multiplier by lead time
    # Far out (t=90), confirmed bookings are only ~25-35% of final demand (Pickup ~ 3.0 - 4.0)
    # Near arrival (t=7), confirmed bookings are ~85-95% of final demand (Pickup ~ 1.05 - 1.15)
    t = max(1, min(90, lead_time_days))
    base_pickup = 1.0 + 2.8 * ((t / 90.0) ** 1.35)
    
    # Day-of-Week index (1=Mon, 5=Fri, 6=Sat, 7=Sun)
    # Leisure destinations surge on weekends; business corridors surge midweek
    if corridor_type in ["leisure", "heritage"]:
        dow_multipliers = {1: 0.88, 2: 0.90, 3: 0.92, 4: 0.98, 5: 1.15, 6: 1.25, 7: 1.10}
    else: # Outbound / Metro business
        dow_multipliers = {1: 1.12, 2: 1.15, 3: 1.18, 4: 1.08, 5: 0.95, 6: 0.85, 7: 0.90}
    dow_factor = dow_multipliers.get(dow, 1.0)
    
    # Combine pickup ratio with real-time search momentum multiplier
    adjusted_pickup = base_pickup * dow_factor * (1.0 + 0.20 * (search_index - 1.0))
    
    projected_demand = max(10, int(otb_bookings * adjusted_pickup))
    
    # Demand uncertainty expands with longer lead time
    std_dev = max(8.0, projected_demand * (0.10 + 0.18 * (t / 90.0)))
    
    p10 = max(5, int(projected_demand - 1.28 * std_dev))
    p50 = projected_demand
    p90 = int(projected_demand + 1.28 * std_dev)
    
    return {
        "otb_bookings": otb_bookings,
        "pickup_ratio": round(adjusted_pickup, 3),
        "p10_demand": p10,
        "p50_demand": p50,
        "p90_demand": p90,
        "demand_std": std_dev
    }

def macro_funnel_demand(corridor_pax_monthly, b2b_agent_share=0.55, tbo_market_share=0.20, los_nights=3.2, pax_per_room=2.4):
    """
    Converts monthly DGCA corridor passenger volume into TBO addressable room-night demand.
    """
    total_trips = corridor_pax_monthly / max(1.0, pax_per_room)
    room_nights = total_trips * los_nights
    b2b_addressable_nights = room_nights * b2b_agent_share
    tbo_addressable_nights = b2b_addressable_nights * tbo_market_share
    
    # Weekly equivalent
    weekly_p50 = int(tbo_addressable_nights / 4.3)
    p10 = int(weekly_p50 * 0.72)
    p90 = int(weekly_p50 * 1.38)
    
    return {
        "monthly_dgca_pax": corridor_pax_monthly,
        "weekly_room_nights_p50": weekly_p50,
        "p10": p10,
        "p90": p90
    }
