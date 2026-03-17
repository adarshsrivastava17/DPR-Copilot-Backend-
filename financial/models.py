"""Financial calculation models for DPR generation.

Generates project cost tables, revenue projections, break-even analysis,
ROI calculations, cash flow estimates, and balance sheets.
"""
from typing import Dict, Any


def generate_financial_data(inputs: dict) -> Dict[str, Any]:
    """
    Generate all financial tables and calculations from project inputs.
    Uses sensible defaults when specific inputs are not provided.
    """
    # Extract inputs with defaults
    total_project_cost = _parse_amount(inputs.get("total_project_cost", 5000000))
    term_loan = _parse_amount(inputs.get("term_loan", total_project_cost * 0.75))
    promoter_contribution = total_project_cost - term_loan
    annual_revenue = _parse_amount(inputs.get("annual_revenue", total_project_cost * 1.5))
    machinery_cost = _parse_amount(inputs.get("machinery_cost", total_project_cost * 0.4))
    working_capital = _parse_amount(inputs.get("working_capital", total_project_cost * 0.15))
    interest_rate = float(inputs.get("interest_rate", 12.0))
    num_employees = int(inputs.get("num_employees", 10))
    revenue_growth = float(inputs.get("revenue_growth", 10.0))  # %

    # ─── Project Cost ───────────────────────────────────
    land_cost = total_project_cost * 0.15
    building_cost = total_project_cost * 0.20
    preoperative = total_project_cost * 0.05
    misc_assets = total_project_cost * 0.05
    contingency = total_project_cost * 0.03

    project_cost = {
        "land_and_site": round(land_cost),
        "building_civil": round(building_cost),
        "plant_machinery": round(machinery_cost),
        "misc_fixed_assets": round(misc_assets),
        "preoperative_expenses": round(preoperative),
        "contingency": round(contingency),
        "working_capital_margin": round(working_capital * 0.25),
        "total": round(total_project_cost),
    }

    # ─── Means of Finance ──────────────────────────────
    subsidy = _parse_amount(inputs.get("subsidy", 0))
    means_of_finance = {
        "promoter_contribution": round(promoter_contribution),
        "term_loan": round(term_loan),
        "working_capital_loan": round(working_capital * 0.75),
        "subsidy": round(subsidy),
        "total": round(total_project_cost),
        "debt_equity_ratio": round(term_loan / max(promoter_contribution, 1), 2),
    }

    # ─── Revenue Projections (5 years) ─────────────────
    revenue_projections = []
    raw_material_pct = 0.45
    power_pct = 0.05
    salary_per_employee = float(inputs.get("avg_salary", 15000)) * 12
    admin_pct = 0.05
    selling_pct = 0.03
    depreciation_rate = 0.10
    tax_rate = 0.25

    depreciable_assets = machinery_cost + building_cost + misc_assets
    annual_depreciation = depreciable_assets * depreciation_rate

    outstanding_loan = term_loan
    loan_repayment_years = int(inputs.get("loan_tenure", 7))
    annual_principal = term_loan / max(loan_repayment_years, 1)

    for year in range(1, 6):
        growth_factor = (1 + revenue_growth / 100) ** (year - 1)
        capacity_utilization = min(0.60 + (year - 1) * 0.10, 1.0)
        rev = round(annual_revenue * growth_factor * capacity_utilization)

        raw_material = round(rev * raw_material_pct)
        power = round(rev * power_pct)
        salaries = round(salary_per_employee * num_employees * (1 + 0.05 * (year - 1)))
        admin = round(rev * admin_pct)
        selling = round(rev * selling_pct)
        depreciation = round(annual_depreciation * max(1 - depreciation_rate * (year - 1), 0.5))
        interest_term = round(outstanding_loan * interest_rate / 100)
        interest_wc = round(working_capital * 0.75 * (interest_rate + 1) / 100)

        total_expenses = raw_material + power + salaries + admin + selling + depreciation + interest_term + interest_wc
        pbt = rev - total_expenses
        tax = round(max(pbt * tax_rate, 0))
        pat = pbt - tax

        outstanding_loan = max(outstanding_loan - annual_principal, 0)

        revenue_projections.append({
            "year": year,
            "revenue": rev,
            "raw_material": raw_material,
            "power_fuel": power,
            "salaries": salaries,
            "admin_expenses": admin,
            "selling_expenses": selling,
            "depreciation": depreciation,
            "interest_term_loan": interest_term,
            "interest_working_capital": interest_wc,
            "total_expenses": total_expenses,
            "profit_before_tax": pbt,
            "tax": tax,
            "net_profit": pat,
            "capacity_utilization": f"{capacity_utilization*100:.0f}%",
            "net_profit_margin": f"{(pat/max(rev,1)*100):.1f}%",
        })

    # ─── Break-Even Analysis ───────────────────────────
    if revenue_projections:
        yr1 = revenue_projections[0]
        fixed_costs = yr1["depreciation"] + yr1["interest_term_loan"] + yr1["interest_working_capital"] + yr1["salaries"] + yr1["admin_expenses"]
        variable_costs = yr1["raw_material"] + yr1["power_fuel"] + yr1["selling_expenses"]
        contribution = yr1["revenue"] - variable_costs
        bep_revenue = round(fixed_costs / max(contribution / max(yr1["revenue"], 1), 0.01))
        bep_percentage = round(bep_revenue / max(yr1["revenue"], 1) * 100, 1)
    else:
        fixed_costs = 0
        variable_costs = 0
        bep_revenue = 0
        bep_percentage = 0

    breakeven = {
        "fixed_costs": round(fixed_costs),
        "variable_costs": round(variable_costs),
        "total_revenue": revenue_projections[0]["revenue"] if revenue_projections else 0,
        "contribution_margin": round(contribution) if revenue_projections else 0,
        "bep_revenue": bep_revenue,
        "bep_percentage": bep_percentage,
        "margin_of_safety": round(100 - bep_percentage, 1),
    }

    # ─── Cash Flow (5 years) ──────────────────────────
    cash_flow = []
    cumulative_cash = 0
    outstanding = term_loan

    for yr in revenue_projections:
        year = yr["year"]
        sources = yr["net_profit"] + yr["depreciation"]
        repayment = round(min(annual_principal, outstanding))
        outstanding = max(outstanding - annual_principal, 0)
        net_cash = sources - repayment
        cumulative_cash += net_cash

        cash_flow.append({
            "year": year,
            "net_profit": yr["net_profit"],
            "depreciation": yr["depreciation"],
            "total_sources": sources,
            "loan_repayment": repayment,
            "net_surplus": net_cash,
            "cumulative_cash": round(cumulative_cash),
        })

    # ─── Key Ratios ───────────────────────────────────
    ratios = []
    outstanding = term_loan
    accumulated_profit = 0

    for yr in revenue_projections:
        outstanding = max(outstanding - annual_principal, 0)
        accumulated_profit += yr["net_profit"]
        dscr_num = yr["net_profit"] + yr["depreciation"] + yr["interest_term_loan"]
        dscr_den = annual_principal + yr["interest_term_loan"]

        ratios.append({
            "year": yr["year"],
            "current_ratio": round((working_capital * 0.75 + accumulated_profit * 0.3) / max(working_capital * 0.3, 1), 2),
            "debt_equity_ratio": round(outstanding / max(promoter_contribution + accumulated_profit, 1), 2),
            "dscr": round(dscr_num / max(dscr_den, 1), 2),
            "net_profit_margin": yr["net_profit_margin"],
            "roi": f"{(yr['net_profit'] / max(total_project_cost, 1) * 100):.1f}%",
        })

    return {
        "project_cost": project_cost,
        "means_of_finance": means_of_finance,
        "revenue_projections": revenue_projections,
        "breakeven": breakeven,
        "cash_flow": cash_flow,
        "ratios": ratios,
        "assumptions": {
            "interest_rate": interest_rate,
            "depreciation_rate": depreciation_rate * 100,
            "tax_rate": tax_rate * 100,
            "revenue_growth": revenue_growth,
            "loan_tenure_years": loan_repayment_years,
        },
    }


def _parse_amount(value) -> float:
    """Parse a monetary amount from string or number."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").replace("₹", "").replace("$", "").replace(" ", "")
        try:
            # Handle lakhs/crores notation
            if "cr" in cleaned.lower():
                return float(cleaned.lower().replace("cr", "").strip()) * 10000000
            if "lakh" in cleaned.lower() or "lac" in cleaned.lower():
                cleaned = cleaned.lower().replace("lakhs", "").replace("lakh", "").replace("lacs", "").replace("lac", "").strip()
                return float(cleaned) * 100000
            return float(cleaned)
        except ValueError:
            return 5000000  # Default 50 lakhs
    return 5000000
