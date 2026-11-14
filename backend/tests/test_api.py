import pytest
import httpx
from app.main import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.asyncio
async def test_health_check():
    """Verify health endpoint returns status healthy."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "ClaireFinance API" in data["app"]

@pytest.mark.asyncio
async def test_personas_and_switching():
    """Verify listing and switching personas yields valid JWT and financial summary."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # List personas
        res = await client.get("/api/personas")
        assert res.status_code == 200
        personas = res.json()
        assert len(personas) == 3
        ids = [p["id"] for p in personas]
        assert "salaried" in ids
        assert "freelancer" in ids
        assert "student" in ids

        # Switch to Salaried
        switch_res = await client.post("/api/personas/switch/salaried")
        assert switch_res.status_code == 200
        s_data = switch_res.json()
        assert "access_token" in s_data
        assert s_data["active_persona"]["id"] == "salaried"
        assert s_data["transactions_count"] > 0

@pytest.mark.asyncio
async def test_categories():
    """Verify default categories listing."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/categories")
        assert res.status_code == 200
        cats = res.json()
        assert len(cats) >= 15
        cat_names = [c["name"] for c in cats]
        assert "Salary/Income" in cat_names
        assert "Food & Dining" in cat_names
        assert "Rent & Housing" in cat_names

@pytest.mark.asyncio
async def test_dashboard_endpoints():
    """Verify all dashboard analytics, budget, personality, benchmarks, and heatmap."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Switch to Salaried and acquire JWT
        sw = await client.post("/api/personas/switch/salaried")
        token = sw.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Overview
        ov = await client.get("/api/dashboard/overview", headers=headers)
        assert ov.status_code == 200
        ov_data = ov.json()
        assert "total_income" in ov_data
        assert "spending_breakdown" in ov_data
        assert "health_score" in ov_data

        # 2. Cashflow
        cf = await client.get("/api/dashboard/cashflow", headers=headers)
        assert cf.status_code == 200
        assert isinstance(cf.json(), list)

        # 3. Spending Breakdown
        sb = await client.get("/api/dashboard/spending-breakdown", headers=headers)
        assert sb.status_code == 200
        assert len(sb.json()) > 0

        # 4. Health Score
        hs = await client.get("/api/dashboard/health-score", headers=headers)
        assert hs.status_code == 200
        assert "total_score" in hs.json()
        assert "components" in hs.json()

        # 5. Budget Status
        bs = await client.get("/api/dashboard/budget-status", headers=headers)
        assert bs.status_code == 200
        b_items = bs.json()
        assert len(b_items) > 0

        # Set Custom Budget Limit
        target_cat_id = b_items[0]["category_id"]
        set_b = await client.post(
            "/api/dashboard/budget",
            json={"category_id": target_cat_id, "user_limit": 15000.0, "period": "monthly"},
            headers=headers
        )
        assert set_b.status_code == 200

        # Verify updated budget status reflects custom user limit
        bs_updated = await client.get("/api/dashboard/budget-status", headers=headers)
        matched = [x for x in bs_updated.json() if x["category_id"] == target_cat_id]
        assert len(matched) == 1
        assert matched[0]["user_limit"] == 15000.0

        # 6. Spending Personality Profile (Feature 15.3)
        pers = await client.get("/api/dashboard/personality", headers=headers)
        assert pers.status_code == 200
        p_data = pers.json()
        assert "archetype" in p_data
        assert "traits" in p_data
        assert len(p_data["traits"]) >= 3

        # 7. Peer Benchmarks (Feature 15.4)
        bm = await client.get("/api/dashboard/benchmarks", headers=headers)
        assert bm.status_code == 200
        bm_data = bm.json()
        assert "cohort_name" in bm_data
        assert len(bm_data["metrics"]) >= 3

        # 8. Savings Streaks & Milestones (Feature 15.6)
        strk = await client.get("/api/dashboard/streaks", headers=headers)
        assert strk.status_code == 200
        strk_data = strk.json()
        assert "current_streak_months" in strk_data
        assert len(strk_data["milestones"]) >= 3

        # 9. Calendar Heatmap (Feature 15.8)
        cal = await client.get("/api/dashboard/calendar", headers=headers)
        assert cal.status_code == 200
        cal_data = cal.json()
        assert "days" in cal_data
        assert len(cal_data["days"]) > 0

@pytest.mark.asyncio
async def test_forecasting_endpoints():
    """Verify cash flow and category-specific forecasting endpoints."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        sw = await client.post("/api/personas/switch/salaried")
        token = sw.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Cashflow forecast
        fc = await client.get("/api/forecast/cashflow?months=3", headers=headers)
        assert fc.status_code == 200
        fc_data = fc.json()
        assert len(fc_data["forecast"]) == 3
        assert "predicted_income" in fc_data["forecast"][0]
        assert "lower_bound" in fc_data["forecast"][0]

        # Accuracy / Backtesting
        acc = await client.get("/api/forecast/accuracy", headers=headers)
        assert acc.status_code == 200
        assert "accuracy_percent" in acc.json()

        # Recurring payments
        rec = await client.get("/api/forecast/recurring", headers=headers)
        assert rec.status_code == 200
        assert "patterns" in rec.json()

        # Liquidity check
        liq = await client.get("/api/forecast/liquidity", headers=headers)
        assert liq.status_code == 200
        assert "is_shortage_risk" in liq.json()

        # Multi-category forecast
        cats_fc = await client.get("/api/forecast/categories?months=3", headers=headers)
        assert cats_fc.status_code == 200
        assert isinstance(cats_fc.json(), list)
        if cats_fc.json():
            first_cat_id = cats_fc.json()[0]["category_id"]
            single_cat_fc = await client.get(f"/api/forecast/category/{first_cat_id}?months=3", headers=headers)
            assert single_cat_fc.status_code == 200
            assert "trend" in single_cat_fc.json()
            assert "forecast" in single_cat_fc.json()

        # Verify predictions persisted to database table
        from app.database import AsyncSessionLocal
        from app.models.prediction import Prediction
        from sqlalchemy import select, func
        async with AsyncSessionLocal() as session:
            pred_count = (await session.execute(select(func.count(Prediction.id)))).scalar()
            assert pred_count > 0

@pytest.mark.asyncio
async def test_query_and_history():
    """Verify 'Can I Afford This?' query engine and chat history."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        sw = await client.post("/api/personas/switch/salaried")
        token = sw.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Ask affordability query - EMI
        payload = {
            "item_name": "Royal Enfield Himalayan 450",
            "estimated_price": 285000,
            "payment_method": "emi",
            "emi_tenure_months": 24,
            "interest_rate": 12.5,
            "additional_context": "Planning to buy before Diwali festival."
        }
        res = await client.post("/api/query/ask", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["verdict"] in ["easily_affordable", "affordable_with_caution", "risky", "not_recommended"]
        assert data["monthly_emi"] > 0
        assert len(data["cash_flow_impact_chart_data"]) == 6

        # Ask affordability query - One-Time Lump Sum
        payload_lump = {
            "item_name": "Samsung M47",
            "estimated_price": 30000,
            "payment_method": "one_time",
            "emi_tenure_months": 24,
            "interest_rate": 12.5,
            "additional_context": "Planning for purchase before next month."
        }
        res_lump = await client.post("/api/query/ask", json=payload_lump, headers=headers)
        assert res_lump.status_code == 200
        data_lump = res_lump.json()
        assert data_lump["verdict"] in ["easily_affordable", "affordable_with_caution", "risky", "not_recommended"]
        assert data_lump["monthly_emi"] == 0.0
        assert len(data_lump["cash_flow_impact_chart_data"]) == 6

        # Query history
        hist = await client.get("/api/query/history", headers=headers)
        assert hist.status_code == 200
        assert len(hist.json()) >= 2
        assert "Samsung" in hist.json()[0]["query_text"]
        assert "Himalayan" in hist.json()[1]["query_text"]

@pytest.mark.asyncio
async def test_simulators():
    """Verify loan amortization, purchase impact, savings goal, and what-if simulators."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        sw = await client.post("/api/personas/switch/salaried")
        token = sw.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Loan simulation
        loan_res = await client.post("/api/simulator/loan", json={
            "loan_amount": 500000,
            "interest_rate": 10.5,
            "tenure_months": 36
        })
        assert loan_res.status_code == 200
        l_data = loan_res.json()
        assert l_data["emi"] > 0
        assert len(l_data["schedule"]) == 36

        # 2. Purchase simulation
        pur_res = await client.post("/api/simulator/purchase", json={
            "amount": 75000,
            "item_name": "MacBook Air M3"
        }, headers=headers)
        assert pur_res.status_code == 200
        assert "emergency_buffer_after_months" in pur_res.json()

        # 3. Savings goal simulation
        sav_res = await client.post("/api/simulator/savings-goal", json={
            "goal_amount": 200000,
            "target_months": 12
        }, headers=headers)
        assert sav_res.status_code == 200
        assert "estimated_months_to_goal" in sav_res.json()

        # 4. What-If Scenario simulation
        whatif_res = await client.post("/api/simulator/what-if", json={
            "scenario_name": "15% Salary Hike and New Rent",
            "income_change_percent": 15.0,
            "monthly_expense_change": 5000.0,
            "one_time_inflow": 50000.0,
            "projection_months": 12
        }, headers=headers)
        assert whatif_res.status_code == 200
        w_data = whatif_res.json()
        assert w_data["simulated_monthly_income"] > w_data["baseline_monthly_income"]
        assert len(w_data["monthly_projection"]) == 12

        # 5. EMI Optimizer (Feature 15.7)
        emi_opt_res = await client.post("/api/simulator/emi-optimizer", json={
            "proposed_loan_amount": 285000,
            "proposed_interest_rate": 12.5,
            "proposed_tenure_months": 24,
            "lump_sum_prepayment_available": 50000.0
        }, headers=headers)
        assert emi_opt_res.status_code == 200
        opt_data = emi_opt_res.json()
        assert "scenarios" in opt_data
        assert len(opt_data["scenarios"]) >= 2
        assert "advisor_summary" in opt_data

@pytest.mark.asyncio
async def test_anomalies_and_alerts():
    """Verify anomaly detection, smart predictive alerts, and alerts endpoints."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        sw = await client.post("/api/personas/switch/salaried")
        token = sw.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Anomalies
        anom_res = await client.get("/api/anomalies", headers=headers)
        assert anom_res.status_code == 200
        assert "anomalies" in anom_res.json()

        # Anomaly patterns
        pat_res = await client.get("/api/anomalies/patterns", headers=headers)
        assert pat_res.status_code == 200
        assert "category_distribution" in pat_res.json()

        # Alerts
        alert_res = await client.get("/api/alerts", headers=headers)
        assert alert_res.status_code == 200
        assert isinstance(alert_res.json(), list)

        # Smart Predictive Alerts (Feature 15.5)
        pred_alerts_res = await client.get("/api/alerts/predictive", headers=headers)
        assert pred_alerts_res.status_code == 200
        assert "total_predictive_alerts" in pred_alerts_res.json()

@pytest.mark.asyncio
async def test_active_learning_category_patch():
    """Verify PATCH transaction updates category and triggers active learning feedback."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        sw = await client.post("/api/personas/switch/salaried")
        token = sw.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Fetch transaction
        txns_res = await client.get("/api/transactions?page=1&page_size=5", headers=headers)
        assert txns_res.status_code == 200
        txns = txns_res.json()["transactions"]
        assert len(txns) > 0
        first_txn = txns[0]

        # Fetch categories to get Entertainment ID
        cats_res = await client.get("/api/categories")
        entertainment_cat = next(c for c in cats_res.json() if c["name"] == "Entertainment")

        # Update category via PATCH
        patch_res = await client.patch(
            f"/api/transactions/{first_txn['id']}",
            json={"category_id": entertainment_cat["id"]},
            headers=headers
        )
        assert patch_res.status_code == 200
        updated = patch_res.json()
        assert updated["category_id"] == entertainment_cat["id"]
        assert updated["category_name"] == "Entertainment"

        # Verify categorizer learned the correction
        from app.services.categorizer import categorizer
        cat_predicted, _ = categorizer.categorize(first_txn["description"])
        assert cat_predicted == "Entertainment"

@pytest.mark.asyncio
async def test_google_auth_and_session():
    """Verify Google OAuth configuration, token issuance, session profile, and data persistence."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Config endpoint
        cfg_res = await client.get("/api/auth/config")
        assert cfg_res.status_code == 200
        cfg_data = cfg_res.json()
        assert "google_client_id" in cfg_data
        assert "apps.googleusercontent.com" in cfg_data["google_client_id"]

        # 2. Unauthenticated /api/auth/me should return 401
        unauth_res = await client.get("/api/auth/me")
        assert unauth_res.status_code == 401

        # 3. Google auth endpoint with mock token
        auth_res = await client.post("/api/auth/google", json={"id_token": "mock-token"})
        assert auth_res.status_code == 200
        auth_data = auth_res.json()
        assert "access_token" in auth_data
        assert "user" in auth_data
        token = auth_data["access_token"]
        user = auth_data["user"]
        assert user["id"] is not None

        # 4. Authenticated /api/auth/me with bearer token
        headers = {"Authorization": f"Bearer {token}"}
        me_res = await client.get("/api/auth/me", headers=headers)
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["id"] == user["id"]
        assert me_data["email"] == user["email"]

        # 5. Seed sample transactions into this account
        seed_res = await client.post("/api/transactions/seed-sample", headers=headers)
        assert seed_res.status_code == 200
        seed_data = seed_res.json()
        assert seed_data["total_saved"] > 0

        # 6. Verify transactions are stored and retrieved for this user
        txns_res = await client.get("/api/transactions?limit=10", headers=headers)
        assert txns_res.status_code == 200
        txns_data = txns_res.json()
        assert txns_data["total"] == seed_data["total_saved"]

