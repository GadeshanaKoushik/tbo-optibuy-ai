import numpy as np
import pandas as pd
import datetime

def generate_calibrated_tbo_data(n_days=730, seed=42):
    """
    Generates 2 years of daily B2B search and booking data across 
    TBO's core domestic and outbound corridors with realistic seasonality,
    unserved look-to-book demand, and lead-time cancellation behavior.
    """
    np.random.seed(seed)
    start_date = pd.to_datetime("2024-01-01")
    dates = pd.date_range(start=start_date, periods=n_days, freq='D')
    
    # Core TBO Corridors (Hotels & Airline Blocks)
    slots = [
        {"slot_id": "HOTEL_GOA_5S", "type": "Hotel", "destination": "Goa", "name": "Goa Beachfront Luxury Resort", 
         "base_demand": 140, "base_cost": 7500, "base_price": 10500, "contract": "Hard Pre-Buy", "release_days": 0},
        {"slot_id": "HOTEL_GOA_4S", "type": "Hotel", "destination": "Goa", "name": "Goa Candolim 4-Star Suites", 
         "base_demand": 190, "base_cost": 4200, "base_price": 5800, "contract": "Soft Allotment", "release_days": 14},
        {"slot_id": "HOTEL_DXB_5S", "type": "Hotel", "destination": "Dubai", "name": "Dubai Marina 5-Star Hotel", 
         "base_demand": 220, "base_cost": 11000, "base_price": 15500, "contract": "Hard Pre-Buy", "release_days": 0},
        {"slot_id": "HOTEL_DXB_4S", "type": "Hotel", "destination": "Dubai", "name": "Dubai Downtown Business Hotel", 
         "base_demand": 160, "base_cost": 6800, "base_price": 9200, "contract": "Soft Allotment", "release_days": 14},
        {"slot_id": "HOTEL_JAI_PALACE", "type": "Hotel", "destination": "Rajasthan", "name": "Jaipur Heritage Palace", 
         "base_demand": 110, "base_cost": 8500, "base_price": 12000, "contract": "Hard Pre-Buy", "release_days": 0},
        {"slot_id": "FLIGHT_DEL_DXB", "type": "Flight", "destination": "Dubai", "name": "DEL-DXB Morning Seat Block", 
         "base_demand": 180, "base_cost": 14000, "base_price": 17200, "contract": "Hard Pre-Buy", "release_days": 0},
        {"slot_id": "FLIGHT_BOM_GOI", "type": "Flight", "destination": "Goa", "name": "BOM-GOI Weekend Seat Block", 
         "base_demand": 150, "base_cost": 4800, "base_price": 6200, "contract": "Soft Allotment", "release_days": 7},
        {"slot_id": "HOTEL_HKT_RESORT", "type": "Hotel", "destination": "Thailand", "name": "Phuket Seafront Pool Villas", 
         "base_demand": 95, "base_cost": 9200, "base_price": 13400, "contract": "Soft Allotment", "release_days": 14}
    ]
    
    rows = []
    
    for d_idx, cur_date in enumerate(dates):
        doy = cur_date.dayofyear
        dow = cur_date.dayofweek
        
        # 1. Macro Trend (TBO growth)
        trend_mult = 1.0 + 0.12 * (d_idx / n_days)
        
        # 2. Indian Festival Calendar Multipliers
        is_festive = 1.0
        # New Year / Christmas (Dec 20 - Jan 5)
        if doy >= 354 or doy <= 5:
            is_festive = 1.65
        # Diwali Peak (Approx late Oct / early Nov: days 295 - 308)
        elif 295 <= doy <= 308:
            is_festive = 1.50
        # Summer Holidays (May: days 121 - 151)
        elif 121 <= doy <= 151:
            is_festive = 1.30
            
        for slot in slots:
            # Destination Seasonality
            dest = slot["destination"]
            if dest == "Goa":
                # High in winter (Oct-Feb), low in monsoon (June-Aug)
                annual_season = 1.0 + 0.50 * np.cos(2 * np.pi * (doy - 355) / 365.25)
                weekend_mult = 1.35 if dow in [4, 5, 6] else 0.85
            elif dest == "Dubai":
                # High in Nov-March (shopping festival), low in extreme summer July-Aug
                annual_season = 1.0 + 0.45 * np.cos(2 * np.pi * (doy - 15) / 365.25)
                weekend_mult = 1.15 if dow in [3, 4, 5] else 0.92
            elif dest == "Rajasthan":
                # Peak winter tourism (Oct-March)
                annual_season = 1.0 + 0.55 * np.cos(2 * np.pi * (doy - 360) / 365.25)
                weekend_mult = 1.25 if dow in [4, 5] else 0.90
            else: # Thailand
                annual_season = 1.0 + 0.35 * np.cos(2 * np.pi * (doy - 340) / 365.25)
                weekend_mult = 1.20 if dow in [4, 5] else 0.90
                
            # True Unconstrained Demand
            noise = np.random.normal(1.0, 0.08)
            unconstrained_demand = int(slot["base_demand"] * trend_mult * annual_season * weekend_mult * is_festive * noise)
            unconstrained_demand = max(10, unconstrained_demand)
            
            # Look-to-Book Searches (typically 25x to 45x actual bookings)
            search_multiplier = np.random.uniform(28, 42)
            total_searches = int(unconstrained_demand * search_multiplier)
            
            # Capacity Cap simulating historical fixed allocation (Sold-out simulation)
            historical_capacity = int(slot["base_demand"] * np.random.uniform(0.9, 1.25))
            observed_booked = min(unconstrained_demand, historical_capacity)
            is_sold_out = 1 if observed_booked >= historical_capacity else 0
            
            # Unserved Demand lost to sold out
            unserved_demand = unconstrained_demand - observed_booked if is_sold_out else 0
            
            # Booking Lead Time (Days before arrival) - Log normal
            avg_lead_days = int(np.random.lognormal(mean=3.2, sigma=0.5))
            avg_lead_days = min(90, max(2, avg_lead_days))
            
            # Cancel Pace (% of bookings that cancel)
            # Early bookers cancel more (25-30%), last-minute bookers cancel less (8-12%)
            base_cancel_rate = 0.08 + 0.20 * (avg_lead_days / 90.0)
            cancellations = int(observed_booked * base_cancel_rate)
            
            rows.append({
                "date": cur_date,
                "slot_id": slot["slot_id"],
                "type": slot["type"],
                "destination": slot["destination"],
                "name": slot["name"],
                "contract_type": slot["contract"],
                "release_cutoff_days": slot["release_days"],
                "supplier_base_cost": slot["base_cost"],
                "standard_resell_price": slot["base_price"],
                "observed_booked": observed_booked,
                "historical_capacity": historical_capacity,
                "is_sold_out": is_sold_out,
                "agent_searches": total_searches,
                "unconstrained_demand": unconstrained_demand,
                "unserved_demand": unserved_demand,
                "avg_lead_days": avg_lead_days,
                "cancellations": cancellations
            })
            
    df = pd.DataFrame(rows)
    return df

if __name__ == "__main__":
    df = generate_calibrated_tbo_data()
    out_path = r"E:\python work\tbo_optibuy\tbo_travel_dataset.csv"
    df.to_csv(out_path, index=False)
    print(f"Generated {len(df)} rows of calibrated TBO travel records -> {out_path}")
