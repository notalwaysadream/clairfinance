import pytest
import httpx
from app.main import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.asyncio
async def test_promises_overview():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Switch to salaried persona first
        await client.post("/api/personas/switch/salaried")
        res = await client.get("/api/promises/overview?buffer_amount=5000&shock_day=1")
        assert res.status_code == 200
        data = res.json()
        assert "promise_1" in data
        assert "promise_2" in data
        assert "fan_chart" in data
        assert "backtest" in data
        assert data["promise_1"]["has_enough_data"] is True
        assert data["promise_1"]["X"] >= 0
        assert data["promise_2"]["risk_A"] >= 0
        assert data["backtest"]["under_5_pct_promise_verified"] is True

@pytest.mark.asyncio
async def test_promises_simulate_shock():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"shock_day": 15, "buffer_amount": 5000.0, "current_balance": 50000.0}
        res = await client.post("/api/promises/simulate-shock", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["shock_day"] == 15
        assert data["has_enough_data"] is True

@pytest.mark.asyncio
async def test_promises_simulate_bill():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "bill_name": "Annual Laptop Insurance",
            "bill_amount": 18000.0,
            "due_day": 12,
            "buffer_amount": 5000.0,
            "current_balance": 45000.0,
            "expected_inflow_amount": 25000.0,
            "expected_inflow_prob": 0.80
        }
        res = await client.post("/api/promises/simulate-bill", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["bill_amount"] == 18000.0
        assert "first_shortfall_date" in data
        assert "start_by_date" in data
        assert "upside_note" in data
