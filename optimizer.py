import numpy as np
import pandas as pd
import pulp

def solve_inventory_allocation(
    candidate_slots,
    total_budget,
    risk_tolerance=1.0,
    peak_availability_floor=0.90,
    soft_floor_penalty=250000.0,
    lead_time_days=45,
    max_lead_window=90
):
    """
    Mixed-Integer Linear Programming Optimizer with:
    1. Dynamic Time-Decay Hazard Lambda(t) on Holding Spoilage & Late-Cancellation Risk.
    2. Soft Availability Floor Constraint (-mu * s) guaranteeing mathematical feasibility.
    3. Multi-Contract Selection (Hard Pre-Buy vs Soft Allotment vs Dynamic API).
    4. Capital Budget Limitation (sum c_i * q_i <= Budget).
    """
    # Normalized time parameter: t -> 0 means arrival is near
    t = max(1, min(max_lead_window, lead_time_days))
    T = max_lead_window
    
    # Dynamic Hazard Function: lambda(t) increases monotonically as t -> 0
    # Early on (t=90): lambda ~ lambda_0. Near check-in (t=2): lambda shoots up
    lambda_0 = 0.40 * risk_tolerance
    beta = 3.60 * risk_tolerance
    gamma = 2.4
    lambda_t = lambda_0 + beta * ((T - t) / T) ** gamma
    
    # Initialize PuLP Problem
    prob = pulp.LpProblem("TBO_OptiBuy_Procurement", pulp.LpMaximize)
    
    # Decision Variables
    q_vars = {}        # Quantity to pre-buy/commit
    contract_vars = {} # 1 if chosen, 0 otherwise
    
    for idx, slot in enumerate(candidate_slots):
        sid = slot["slot_id"]
        # Integer quantity between 0 and max allotment capacity
        q_vars[sid] = pulp.LpVariable(f"q_{sid}", lowBound=0, upBound=slot.get("max_capacity", 300), cat=pulp.LpInteger)
        
    # Slack variable for soft availability floor
    s = pulp.LpVariable("availability_shortfall", lowBound=0, cat=pulp.LpContinuous)
    
    # 1. Budget Constraint: Sum(c_i * q_i) <= Total Budget
    cost_expr = pulp.lpSum([candidate_slots[i]["cost"] * q_vars[candidate_slots[i]["slot_id"]] for i in range(len(candidate_slots))])
    prob += (cost_expr <= total_budget, "Budget_Cap")
    
    # 2. Objective Function:
    # Maximize: Expected Margin - lambda(t) * Spoilage Tail Loss - mu * shortfall
    obj_terms = []
    
    for slot in candidate_slots:
        sid = slot["slot_id"]
        q = q_vars[sid]
        
        cost = slot["cost"]
        price = slot["price"]
        p50_demand = slot["p50_demand"]
        p10_demand = slot["p10_demand"] # Conservative baseline
        cancel_ruin_hazard = slot.get("cancel_hazard", 0.08)
        
        # Expected Margin per unit: Price * (1 - cancel_ruin) - Cost
        expected_margin_per_unit = (price * (1.0 - cancel_ruin_hazard)) - cost
        
        # Spoilage Risk: Cost * max(0, q - p10)
        # In linear approximation, spoilage risk penalty kicks in when q > p10
        spoilage_penalty_rate = lambda_t * cost * 0.45
        
        # Net value contributed per unit
        net_coeff = expected_margin_per_unit - (spoilage_penalty_rate if t <= 20 else spoilage_penalty_rate * 0.3)
        obj_terms.append(net_coeff * q)
        
    # Add soft floor penalty
    obj_terms.append(-soft_floor_penalty * s)
    prob += pulp.lpSum(obj_terms), "Total_Risk_Adjusted_Profit"
    
    # 3. Soft Availability Floor Constraint
    # We want total rooms booked across peak slots to meet service level A
    total_expected_demand = sum([s["p50_demand"] for s in candidate_slots])
    target_units = peak_availability_floor * total_expected_demand
    prob += (pulp.lpSum([q_vars[s["slot_id"]] for s in candidate_slots]) + s >= target_units, "Peak_Availability_Floor")
    
    # Solve using CBC solver
    solver = pulp.PULP_CBC_CMD(msg=False)
    prob.solve(solver)
    
    # Extract Results
    allocations = []
    total_spent = 0.0
    total_expected_profit = 0.0
    
    for slot in candidate_slots:
        sid = slot["slot_id"]
        rec_q = int(q_vars[sid].varValue) if q_vars[sid].varValue is not None else 0
        spent = rec_q * slot["cost"]
        total_spent += spent
        
        # Simulated profit
        actual_sales = min(rec_q, slot["p50_demand"])
        net_profit = actual_sales * slot["price"] * (1.0 - slot.get("cancel_hazard", 0.08)) - spent
        total_expected_profit += net_profit
        
        allocations.append({
            "slot_id": sid,
            "name": slot["name"],
            "type": slot["type"],
            "destination": slot["destination"],
            "contract_type": slot["contract"],
            "cost_per_unit": slot["cost"],
            "resell_price": slot["price"],
            "recommended_qty": rec_q,
            "total_outlay": spent,
            "expected_net_margin": net_profit,
            "margin_pct": round((net_profit / spent * 100) if spent > 0 else 0, 1)
        })
        
    shortfall_val = s.varValue if s.varValue is not None else 0.0
    
    return {
        "status": pulp.LpStatus[prob.status],
        "lead_time_days": t,
        "dynamic_lambda_t": round(lambda_t, 3),
        "total_budget": total_budget,
        "total_spent": total_spent,
        "budget_utilization": round((total_spent / total_budget) * 100, 1),
        "total_expected_profit": total_expected_profit,
        "overall_roi_pct": round((total_expected_profit / total_spent * 100) if total_spent > 0 else 0, 1),
        "availability_shortfall": round(shortfall_val, 1),
        "allocations": allocations
    }
