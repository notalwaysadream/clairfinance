import math
from typing import List, Dict, Any, Tuple
from app.schemas.dashboard import HealthScoreBreakdown, HealthScoreComponent

def calculate_health_score(
    total_income: float,
    total_expenses: float,
    monthly_expenses_list: List[float],
    total_emis: float,
    current_savings: float,
    category_expenses: Dict[str, float]
) -> HealthScoreBreakdown:
    """
    Computes 5-component Financial Health Score (0-100) per Hackathon Blueprint spec:
    1. Savings Rate (30 pts)
    2. Expense Consistency (20 pts)
    3. Debt-to-Income (20 pts)
    4. Emergency Buffer (15 pts)
    5. Spending Diversity (15 pts)
    """
    components = []
    recommendations = []

    # 1. Savings Rate (0-30 pts)
    if total_income > 0:
        savings_rate = max(0.0, ((total_income - total_expenses) / total_income) * 100.0)
    else:
        savings_rate = 0.0

    savings_score = min(30.0, (savings_rate / 20.0) * 30.0)
    components.append(HealthScoreComponent(
        name="Savings Rate",
        score=round(savings_score, 1),
        max_score=30.0,
        value=f"{savings_rate:.1f}%",
        description="Target: >20% of income saved each month."
    ))
    if savings_rate < 15.0:
        recommendations.append("Increase your monthly savings to at least 20% to build financial resilience.")

    # 2. Expense Consistency (0-20 pts)
    if len(monthly_expenses_list) >= 2:
        mean_exp = sum(monthly_expenses_list) / len(monthly_expenses_list)
        variance = sum((x - mean_exp) ** 2 for x in monthly_expenses_list) / len(monthly_expenses_list)
        std_exp = math.sqrt(variance)
        cv = std_exp / mean_exp if mean_exp > 0 else 1.0
        consistency_score = max(0.0, min(20.0, 20.0 * (1.0 - min(cv, 1.0))))
        cv_pct = cv * 100.0
    else:
        consistency_score = 15.0  # reasonable default if insufficient months
        cv_pct = 15.0

    components.append(HealthScoreComponent(
        name="Expense Consistency",
        score=round(consistency_score, 1),
        max_score=20.0,
        value=f"Variation: {cv_pct:.1f}%",
        description="Predictable spending month-over-month receives higher scores."
    ))
    if cv_pct > 35.0:
        recommendations.append("Smooth out large discretionary spikes across months to stabilize cash flow.")

    # 3. Debt-to-Income Ratio (0-20 pts)
    if total_income > 0:
        dti_ratio = (total_emis / total_income)
    else:
        dti_ratio = 0.0

    debt_score = max(0.0, min(20.0, 20.0 * (1.0 - (dti_ratio / 0.50))))
    components.append(HealthScoreComponent(
        name="Debt-to-Income",
        score=round(debt_score, 1),
        max_score=20.0,
        value=f"{dti_ratio * 100:.1f}%",
        description="EMIs should ideally remain below 30% of total income."
    ))
    if dti_ratio > 0.35:
        recommendations.append("Your EMIs consume over 35% of income. Avoid taking on new debt.")

    # 4. Emergency Buffer (0-15 pts)
    avg_monthly_exp = total_expenses / max(1, len(monthly_expenses_list)) if monthly_expenses_list else total_expenses
    if avg_monthly_exp > 0:
        emergency_months = max(0.0, current_savings / avg_monthly_exp)
    else:
        emergency_months = 3.0

    buffer_score = min(15.0, (emergency_months / 3.0) * 15.0)
    components.append(HealthScoreComponent(
        name="Emergency Buffer",
        score=round(buffer_score, 1),
        max_score=15.0,
        value=f"{emergency_months:.1f} months",
        description="Aim for at least 3 months of basic living expenses saved."
    ))
    if emergency_months < 2.0:
        recommendations.append("Build an emergency fund covering at least 3 months of essential living expenses.")

    # 5. Spending Diversity (0-15 pts)
    # Using Shannon entropy of category breakdown
    total_cat_exp = sum(category_expenses.values())
    if total_cat_exp > 0 and len(category_expenses) > 1:
        entropy = 0.0
        for amt in category_expenses.values():
            if amt > 0:
                p = amt / total_cat_exp
                entropy -= p * math.log(p)
        max_entropy = math.log(len(category_expenses))
        diversity_score = 15.0 * (entropy / max_entropy) if max_entropy > 0 else 10.0
    else:
        diversity_score = 10.0

    diversity_score = max(0.0, min(15.0, diversity_score))
    components.append(HealthScoreComponent(
        name="Spending Diversity",
        score=round(diversity_score, 1),
        max_score=15.0,
        value="Balanced" if diversity_score >= 10 else "Concentrated",
        description="A diversified budget prevents dependency on single expense spikes."
    ))

    # Total Score
    total_score = int(round(savings_score + consistency_score + debt_score + buffer_score + diversity_score))
    total_score = max(0, min(100, total_score))

    # Interpretation
    if total_score >= 80:
        status = "Excellent"
        status_color = "#22c55e"
    elif total_score >= 60:
        status = "Good"
        status_color = "#eab308"
    elif total_score >= 40:
        status = "Fair"
        status_color = "#f97316"
    else:
        status = "Needs Work"
        status_color = "#ef4444"

    if not recommendations:
        recommendations.append("Great job! Keep maintaining your disciplined spending and savings habits.")

    return HealthScoreBreakdown(
        total_score=total_score,
        status=status,
        status_color=status_color,
        components=components,
        recommendations=recommendations
    )
