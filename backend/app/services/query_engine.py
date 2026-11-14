import math
import json
from typing import Dict, Any, List, Optional
from app.schemas.query import QueryAskRequest, QueryAskResponse, AffordabilityImpact
from app.services.gemini_client import gemini_client

def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    if tenure_months <= 0 or principal <= 0:
        return 0.0
    r = (annual_rate / 12.0) / 100.0
    if r == 0:
        return principal / tenure_months
    emi = (principal * r * ((1.0 + r) ** tenure_months)) / (((1.0 + r) ** tenure_months) - 1.0)
    return emi

async def evaluate_affordability(
    req: QueryAskRequest,
    avg_monthly_income: float,
    avg_monthly_expenses: float,
    current_savings: float,
    existing_emis: float,
    health_score: int,
    persona_type: str = "salaried",
    past_queries: Optional[List[Dict[str, Any]]] = None
) -> QueryAskResponse:
    """
    Evaluates whether the user can afford a proposed purchase or loan.
    Integrates Gemini Flash with conversational memory of past inquiries,
    supported by deterministic financial rules fallback.
    """
    price = float(req.estimated_price)
    current_monthly_savings = max(0.0, avg_monthly_income - avg_monthly_expenses)
    months_until_strain: Optional[int] = None
    remaining_buffer: float = max(0.0, current_savings - price)

    if req.payment_method.lower() in ["emi", "loan"]:
        tenure = req.emi_tenure_months or 24
        rate = req.interest_rate or 12.5
        monthly_emi = calculate_emi(price, rate, tenure)
    else:
        # One-time purchase
        tenure = 1
        monthly_emi = 0.0

    if req.payment_method.lower() == "one_time":
        projected_monthly_savings = current_monthly_savings
        savings_reduction_pct = (price / current_savings * 100.0) if current_savings > 0 else 100.0
        months_buffer = remaining_buffer / avg_monthly_expenses if avg_monthly_expenses > 0 else 0.0
        
        if price > current_savings:
            months_until_strain = 0

        if price <= current_savings * 0.3 and months_buffer >= 3.0:
            verdict = "easily_affordable"
            confidence = 0.90
        elif price <= current_savings * 0.7 and months_buffer >= 1.5:
            verdict = "affordable_with_caution"
            confidence = 0.82
        elif price <= current_savings:
            verdict = "risky"
            confidence = 0.78
        else:
            verdict = "not_recommended"
            confidence = 0.95
    else:
        projected_monthly_savings = current_monthly_savings - monthly_emi
        savings_reduction_pct = (monthly_emi / current_monthly_savings * 100.0) if current_monthly_savings > 0 else 100.0
        
        # Strain timeline: how many months until current savings is depleted if deficit occurs
        if projected_monthly_savings < 0:
            deficit = abs(projected_monthly_savings)
            months_until_strain = math.floor(current_savings / deficit) if deficit > 0 else 0
        else:
            months_until_strain = None

        # Verdict rules
        new_dti = (existing_emis + monthly_emi) / avg_monthly_income if avg_monthly_income > 0 else 1.0

        if persona_type == "student" and (monthly_emi > avg_monthly_income * 0.5 or projected_monthly_savings < 0):
            verdict = "not_recommended"
            confidence = 0.95
        elif persona_type == "freelancer" and (new_dti > 0.35 or projected_monthly_savings < (current_monthly_savings * 0.4)):
            verdict = "risky"
            confidence = 0.86
        elif projected_monthly_savings > (current_monthly_savings * 0.5) and new_dti <= 0.30:
            verdict = "easily_affordable"
            confidence = 0.88
        elif projected_monthly_savings > 0 and new_dti <= 0.45:
            verdict = "affordable_with_caution"
            confidence = 0.82
        elif projected_monthly_savings > 0 and new_dti > 0.45:
            verdict = "risky"
            confidence = 0.80
        else:
            verdict = "not_recommended"
            confidence = 0.92

    # Generate Chart Points for Next.js (6 months projection)
    chart_data = []
    base_balance = current_savings
    proj_balance = current_savings
    month_names = ["Month 1", "Month 2", "Month 3", "Month 4", "Month 5", "Month 6"]

    for i, m_label in enumerate(month_names):
        base_balance += current_monthly_savings
        if req.payment_method.lower() == "one_time":
            if i == 0:
                proj_balance = max(0.0, proj_balance - price + current_monthly_savings)
            else:
                proj_balance += current_monthly_savings
            commitment_this_month = price if i == 0 else 0.0
        else:
            proj_balance += projected_monthly_savings
            commitment_this_month = monthly_emi

        chart_data.append({
            "month": m_label,
            "baseline_savings": round(base_balance, 2),
            "projected_savings": round(proj_balance, 2),
            "monthly_commitment": round(commitment_this_month, 2)
        })

    # Build contextual memory section from previous user queries
    history_context_str = "None"
    if past_queries and len(past_queries) > 0:
        history_lines = []
        for pq in past_queries[:5]:
            q_txt = pq.get("query_text", "")
            q_verdict = pq.get("verdict", "")
            q_date = pq.get("created_at", "")
            history_lines.append(f"- [{q_date}] Query: '{q_txt}' | Past Verdict: {q_verdict}")
        history_context_str = "\n".join(history_lines)

    # Try Gemini LLM prompt if available
    llm_analysis = None
    if gemini_client.is_available:
        prompt = f"""
You are an expert Indian financial advisor. Analyze this person's financial situation and determine if they can afford the proposed purchase/loan.

FINANCIAL PROFILE:
- Average monthly income: ₹{avg_monthly_income:,.0f}
- Average monthly expenses: ₹{avg_monthly_expenses:,.0f}
- Current monthly savings: ₹{current_monthly_savings:,.0f}
- Existing EMIs: ₹{existing_emis:,.0f}/month
- Financial health score: {health_score}/100
- Persona: {persona_type}

USER'S PAST FINANCIAL INQUIRIES (CONTEXTUAL MEMORY):
{history_context_str}

PROPOSED PURCHASE:
- Item: {req.item_name}
- Price: ₹{price:,.0f}
- Payment Method: {req.payment_method}
- Calculated Monthly EMI: ₹{monthly_emi:,.0f}
- Product Link: {req.link or 'None'}
- Additional User Notes: {req.additional_context or 'None'}

INSTRUCTIONS:
Respond in this EXACT JSON structure:
{{
  "verdict": "{verdict}",
  "confidence": {confidence},
  "analysis": "2-3 concise sentences analyzing affordability and impact on savings, factoring in their past inquiries if relevant.",
  "risks": ["Specific risk 1", "Specific risk 2"],
  "alternatives": ["Specific alternative 1", "Specific alternative 2"],
  "reasoning": "Detailed financial reasoning based on income, EMI buffer, and prior commitment questions."
}}
"""
        llm_analysis = await gemini_client.generate_json(prompt)

    valid_verdicts = {"easily_affordable", "affordable_with_caution", "risky", "not_recommended"}
    llm_verdict = llm_analysis.get("verdict") if llm_analysis else None
    if llm_verdict not in valid_verdicts:
        llm_verdict = verdict

    if llm_analysis and "analysis" in llm_analysis:
        return QueryAskResponse(
            verdict=llm_verdict,
            confidence=float(llm_analysis.get("confidence", confidence)),
            monthly_emi=round(monthly_emi, 2),
            impact=AffordabilityImpact(
                current_monthly_savings=round(current_monthly_savings, 2),
                projected_monthly_savings=round(projected_monthly_savings, 2),
                savings_reduction_percent=round(savings_reduction_pct, 1),
                months_until_strain=months_until_strain,
            ),
            analysis=llm_analysis.get("analysis", ""),
            risks=llm_analysis.get("risks", []),
            alternatives=llm_analysis.get("alternatives", []),
            reasoning=llm_analysis.get("reasoning", ""),
            cash_flow_impact_chart_data=chart_data
        )

    # Deterministic fallback response with comprehensive reasoning
    risks = []
    alternatives = []

    if persona_type == "student":
        risks.append("As a student, this commitment exceeds your monthly allowance and risks defaulting on semester fee deadlines.")
        if projected_monthly_savings < 0:
            risks.append(f"Creates an unsustainable deficit of ₹{abs(projected_monthly_savings):,.0f} every single month.")
        alternatives.append("Postpone large vehicle purchases until securing full-time employment or steady post-grad stipend.")
        alternatives.append("Consider shared transit or a pre-owned 2-wheeler under ₹30,000 paid in full.")
    elif persona_type == "freelancer":
        risks.append("Freelance income is highly variable. Fixed recurring EMIs create severe liquidity stress during client payment delay months.")
        if savings_reduction_pct > 50:
            risks.append(f"Consumes {savings_reduction_pct:.1f}% of your typical monthly surplus, narrowing your freelance buffer.")
        alternatives.append("Build a mandatory 6-month buffer before locking in fixed debt commitments.")
        alternatives.append("Opt for shorter project-funded milestones or pay upfront with project retainers.")
    else:
        if req.payment_method.lower() in ["emi", "loan"]:
            if savings_reduction_pct > 60:
                risks.append(f"This EMI consumes {savings_reduction_pct:.1f}% of your monthly savings, leaving little room for unexpected expenses.")
            if existing_emis + monthly_emi > avg_monthly_income * 0.40:
                risks.append(f"Total debt obligations rise to {((existing_emis + monthly_emi) / avg_monthly_income) * 100:.1f}% of income.")
            
            alternatives.append(f"Extend tenure to {(req.emi_tenure_months or 24) + 12} months to lower monthly commitment.")
            alternatives.append(f"Save up for a 30% down payment (₹{price * 0.3:,.0f}) to reduce principal and total interest.")
        else:
            if price > current_savings * 0.5:
                risks.append("This purchase depletes over 50% of your current liquid savings buffer.")
            alternatives.append("Consider postponing this purchase by 2-3 months to replenish savings first.")
            alternatives.append("Explore zero-cost EMI options to spread the cash outflow.")

    if not risks:
        risks.append("Ensure automatic payment setup to avoid late fees or interest penalties.")
    if not alternatives:
        alternatives.append("Prepay principal early whenever you receive bonus or surplus income.")

    if req.payment_method.lower() == "one_time":
        analysis = (
            f"Based on your liquid savings of ₹{current_savings:,.0f} and monthly surplus of ₹{current_monthly_savings:,.0f}, "
            f"this one-time purchase of ₹{price:,.0f} leaves a remaining liquid reserve of ₹{remaining_buffer:,.0f}."
        )
        reasoning = (
            f"Your current financial health score is {health_score}/100 with liquid savings of ₹{current_savings:,.0f}. "
            f"A one-time expenditure of ₹{price:,.0f} yields an affordability verdict of {verdict.replace('_', ' ').title()}."
        )
    else:
        analysis = (
            f"Based on your average income of ₹{avg_monthly_income:,.0f}/month and expenses of ₹{avg_monthly_expenses:,.0f}/month, "
            f"this purchase requires an EMI of ₹{monthly_emi:,.0f}/month. Your monthly savings will change from ₹{current_monthly_savings:,.0f} "
            f"to ₹{projected_monthly_savings:,.0f} (a {savings_reduction_pct:.1f}% change)."
        )
        reasoning = (
            f"Your current financial health score is {health_score}/100 with an existing monthly surplus of ₹{current_monthly_savings:,.0f}. "
            f"Adding a monthly obligation of ₹{monthly_emi:,.0f} yields a verdict of {verdict.replace('_', ' ').title()}."
        )

    return QueryAskResponse(
        verdict=verdict,
        confidence=confidence,
        monthly_emi=round(monthly_emi, 2),
        impact=AffordabilityImpact(
            current_monthly_savings=round(current_monthly_savings, 2),
            projected_monthly_savings=round(projected_monthly_savings, 2),
            savings_reduction_percent=round(savings_reduction_pct, 1),
            months_until_strain=months_until_strain,
        ),
        analysis=analysis,
        risks=risks,
        alternatives=alternatives,
        reasoning=reasoning,
        cash_flow_impact_chart_data=chart_data
    )
