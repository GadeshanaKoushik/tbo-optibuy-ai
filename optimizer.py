import numpy as np
import pandas as pd
from scipy import stats
import pulp

def compute_newsvendor_targets(candidate_slots, lead_time_days=45, clv_agent=2970000.0):
    """
    Computes slot-level optimal purchase target Q*_i(t) using Dynamic Newsvendor:
    
    1. Dynamic Overage Cost C_o(t):
       C_o(t) = Cost(t) * (1 - sigma(t)) + Penalty_supplier(t)
       
    2. Dynamic Underage Cost C_u(t):
       C_u(t) = [Price(t) - Cost(t)] + P_fail * M_comp + P_defect * CLV_agent
       
    3. Critical Ratio CR(t):
       CR(t) = C_u(t) / [C_u(t) + C_o(t)]
       
    4. Target Inventory Q*_i(t) = F_i^-1(CR(t))
    """
    t = max(1, min(90, lead_time_days))
    
    # Resale probability sigma(t): decays to 0 as arrival approaches
    resale_success = 1.0 / (1.0 + np.exp(-0.08 * (t - 18.0)))
    resale_failure = 1.0 - resale_success
    
    # Supplier penalty factor: 0% before T-14, 50% T-14 to T-7, 100% inside T-7
    if t > 14:
        penalty_rate = 0.00
    elif t > 7:
        penalty_rate = 0.50
    else:
        penalty_rate = 1.00
        
    # Agent defection probability on peak stockout
    # Weighted average churn risk for high-value travel agency (~12%)
    p_defect = 0.12
    # Competitor displacement margin penalty
    p_fail_comp = 0.65
    m_comp = 1800.0
    
    slots_with_nv = []
    
    for slot in candidate_slots:
        cost = slot["cost"]
        price = slot["price"]
        p50 = slot.get("p50_demand", 120)
        p10 = slot.get("p10_demand", int(p50 * 0.72))
        p90 = slot.get("p90_demand", int(p50 * 1.38))
        
        # Estimate standard deviation from (P90 - P10) / 2.56
        std_dev = max(5.0, (p90 - p10) / 2.56)
        
        # 1. Overage Cost C_o(t)
        c_over = (cost * resale_failure) + (cost * penalty_rate * 0.50)
        c_over = max(500.0, c_over)
        
        # 2. Underage Cost C_u(t)
        direct_margin = max(500.0, price - cost)
        displacement_cost = p_fail_comp * m_comp
        # Amortized stockout churn penalty per room-night stockout
        # An agent stocks out of a ~3 night stay; 1/25 of total annual relationship affected
        agent_churn_loss = (p_defect * clv_agent) / 350.0 
        c_under = direct_margin + displacement_cost + agent_churn_loss
        
        # 3. Critical Ratio CR(t)
        critical_ratio = c_under / (c_under + c_over)
        critical_ratio = min(0.96, max(0.40, critical_ratio))
        
        # 4. Optimal Target Q* = F^-1(CR)
        q_star = int(stats.norm.ppf(critical_ratio, loc=p50, scale=std_dev))
        q_star = max(5, min(slot.get("max_capacity", 350), q_star))
        
        slot_res = dict(slot)
        slot_res.update({
            "c_over": round(c_over, 1),
            "c_under": round(c_under, 1),
            "critical_ratio": round(critical_ratio, 3),
            "q_star": q_star,
            "demand_std": round(std_dev, 1)
        })
        slots_with_nv.append(slot_res)
        
    return slots_with_nv

def solve_inventory_allocation(
    candidate_slots,
    total_budget,
    risk_tolerance=1.0,
    peak_availability_floor=0.90,
    soft_floor_penalty=250000.0,
    lead_time_days=45,
    max_lead_window=90,
    corridor_cap_ratio=0.30
):
    """
    Constrained Portfolio Linear Program (LP):
    Reconciles Newsvendor slot targets Q*_i(t) under global capital budget,
    strategic availability floors, and corridor concentration caps.
    """
    t = max(1, min(max_lead_window, lead_time_days))
    T = max_lead_window
    
    # Step 1: Compute Dynamic Newsvendor Upper Bounds Q*_i(t)
    nv_slots = compute_newsvendor_targets(candidate_slots, lead_time_days=t)
    
    # Step 2: Dynamic Hazard Rate on Spoilage Risk
    lambda_0 = 0.35 * risk_tolerance
    beta = 3.20 * risk_tolerance
    gamma = 2.4
    lambda_t = lambda_0 + beta * ((T - t) / T) ** gamma
    
    # Step 3: Formulate Linear Program in PuLP
    prob = pulp.LpProblem("TBO_OptiBuy_Portfolio_Allocation", pulp.LpMaximize)
    
    # Decision Variables: Room/Seat units to pre-buy for slot i (bounded by Q*_i)
    q_vars = {}
    for slot in nv_slots:
        sid = slot["slot_id"]
        q_max = slot["q_star"]
        q_vars[sid] = pulp.LpVariable(f"q_{sid}", lowBound=0, upBound=q_max, cat=pulp.LpInteger)
        
    # Slack variable for soft availability floor
    s = pulp.LpVariable("availability_shortfall", lowBound=0, cat=pulp.LpContinuous)
    
    # Constraint 1: Global Capital Budget sum(c_i * q_i) <= Total Budget
    cost_expr = pulp.lpSum([s_data["cost"] * q_vars[s_data["slot_id"]] for s_data in nv_slots])
    prob += (cost_expr <= total_budget, "Budget_Constraint")
    
    # Constraint 2: Single-Corridor Exposure Cap (Prevents over-concentration)
    max_corridor_spend = total_budget * corridor_cap_ratio
    destinations = set(s_data.get("destination", s_data["slot_id"]) for s_data in nv_slots)
    for dest in destinations:
        dest_slots = [s_data for s_data in nv_slots if s_data.get("destination", s_data["slot_id"]) == dest]
        if dest_slots:
            dest_cost = pulp.lpSum([ds["cost"] * q_vars[ds["slot_id"]] for ds in dest_slots])
            prob += (dest_cost <= max_corridor_spend, f"Cap_{dest.replace(' ', '_')}")
            
    # Constraint 3: Strategic Availability Floor (Soft constraint with penalty)
    total_expected_demand = sum(s_data["p50_demand"] for s_data in nv_slots)
    target_units = peak_availability_floor * total_expected_demand
    prob += (pulp.lpSum([q_vars[s_data["slot_id"]] for s_data in nv_slots]) + s >= target_units, "Availability_Floor")
    
    # Objective Function: Maximize Expected Portfolio Return minus Risk Penalty
    obj_terms = []
    for slot in nv_slots:
        sid = slot["slot_id"]
        q = q_vars[sid]
        cost = slot["cost"]
        price = slot["price"]
        p10 = slot["p10_demand"]
        
        # Expected base margin
        unit_margin = price - cost
        
        # Dynamic risk penalty scaling as check-in approaches
        spoilage_rate = lambda_t * (cost * (1.0 - (1.0 / (1.0 + np.exp(-0.08 * (t - 18.0))))))
        net_coeff = unit_margin - spoilage_rate
        
        obj_terms.append(net_coeff * q)
        
    # Shortfall penalty in objective
    obj_terms.append(-soft_floor_penalty * s)
    prob += pulp.lpSum(obj_terms), "Net_Portfolio_Objective"
    
    # Solve LP using CBC solver
    solver = pulp.PULP_CBC_CMD(msg=False)
    prob.solve(solver)
    
    # Compile allocation report
    allocations = []
    total_spent = 0.0
    total_expected_profit = 0.0
    
    for slot in nv_slots:
        sid = slot["slot_id"]
        rec_q = int(q_vars[sid].varValue) if q_vars[sid].varValue is not None else 0
        spent = rec_q * slot["cost"]
        total_spent += spent
        exp_margin = rec_q * (slot["price"] - slot["cost"])
        total_expected_profit += exp_margin
        
        allocations.append({
            "slot_id": sid,
            "name": slot["name"],
            "destination": slot.get("destination", "General"),
            "contract_type": slot.get("contract_type", "Hard Pre-Buy"),
            "cost": slot["cost"],
            "price": slot["price"],
            "p50_demand": slot["p50_demand"],
            "c_over": slot["c_over"],
            "c_under": slot["c_under"],
            "critical_ratio": slot["critical_ratio"],
            "q_star": slot["q_star"],
            "allocated_units": rec_q,
            "spent": spent,
            "expected_margin": exp_margin,
            "pct_q_star_met": round((rec_q / slot["q_star"]) * 100.0, 1) if slot["q_star"] > 0 else 0.0
        })
        
    df_alloc = pd.DataFrame(allocations)
    shortfall_val = float(s.varValue) if s.varValue is not None else 0.0
    
    return {
        "status": pulp.LpStatus[prob.status],
        "allocations": df_alloc,
        "total_budget": total_budget,
        "total_spent": total_spent,
        "budget_utilization_pct": round((total_spent / total_budget) * 100.0, 2),
        "total_expected_profit": total_expected_profit,
        "roi_pct": round((total_expected_profit / max(1.0, total_spent)) * 100.0, 2),
        "lambda_t": round(lambda_t, 3),
        "shortfall_units": int(shortfall_val)
    }
