# Backend Progress and Status

## Overview
This file tracks what is currently built in the backend and what remains to be built.
Tech stack: FastAPI, SQLAlchemy (async SQLite with aiosqlite), scikit-learn, and Pydantic.

## Implemented Features

### 1. Database and Project Setup
- FastAPI app in `backend/app/main.py` with CORS, health check endpoints, and automatic database initialization on startup.
- Async SQLite database engine in `backend/app/database.py`.
- Models in `backend/app/models/`:
  - `User`: user accounts and authentication.
  - `Category`: 18 default financial categories (salary, rent, groceries, transport, utilities, loans, etc.).
  - `Transaction`: bank transactions with date, amount, credit/debit type, payment mode, anomaly score, and recurring flag.
  - `ChatHistory`: stored affordability questions and AI responses.
  - `Prediction`: monthly forecasting values with confidence bounds.
  - `Alert`: spending alerts, upcoming bill reminders, and anomaly notifications.
  - `BudgetLimit`: category budget limits.
  - `RecurringPattern`: detected recurring subscriptions and bills.
- Auth setup in `backend/app/routers/auth.py` and `backend/app/utils/helpers.py`:
  - Google OAuth token verification (`POST /api/auth/google`).
  - Fallback dev user mode for local testing without external Google setup.
  - JWT generation and route protection.

### 2. Multi-Persona Switcher
- Router in `backend/app/routers/personas.py`:
  - `salaried`: Rahul Sharma (fixed monthly salary, car loan EMI, rent, regular savings).
  - `freelancer`: Priya Patel (irregular client payments, software subscriptions, coworking).
  - `student`: Amit Verma (tight monthly allowance, mess fees, semester fee spikes).
- Endpoints:
  - `GET /api/personas`: list available personas and see which is active.
  - `GET /api/personas/active`: get the currently active persona.
  - `POST /api/personas/switch/{persona_id}`: switch the active profile, load their 12-month transaction dataset, and get a fresh JWT.
  - `POST /api/personas/seed-all`: pre-seed all three datasets at once.

### 3. Core Processing Services
- Indian Bank CSV Parser (`backend/app/services/csv_parser.py`):
  - Handles various Indian bank formats (HDFC separate Debit/Credit columns, single amount column with Cr/Dr flag, negative values).
  - Skips preamble bank account metadata.
  - Parses common date formats (YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, DD MMM YYYY).
  - Detects payment modes (UPI, NEFT, IMPS, Card, Auto-Debit, Cash).
- Transaction Categorizer (`backend/app/services/categorizer.py`):
  - Rule-based keyword matching for 200+ Indian merchants (Swiggy, Zomato, Uber, Ola, Apollo, Netflix, BESCOM, Zerodha, etc.).
  - scikit-learn fallback (TF-IDF + LinearSVC) for unseen transaction descriptions.
- Financial Health Scorer (`backend/app/services/health_scorer.py`):
  - Calculates a 0 to 100 score based on 5 metrics:
    1. Savings rate (30% weight)
    2. Expense consistency (20% weight, coefficient of variation)
    3. Debt to income ratio (20% weight, EMI load)
    4. Emergency buffer (15% weight, months of basic expenses covered)
    5. Spending diversity (15% weight, category entropy)
- Anomaly Detector (`backend/app/services/anomaly_detector.py`):
  - Flags transactions where amount deviates significantly from category average (|z-score| > 2.5).
- Recurring Payment Detector (`backend/app/services/recurring_detector.py`):
  - Identifies recurring subscriptions, EMIs, and bills using interval clustering (weekly, monthly, quarterly, annual).
- Affordability Query Engine (`backend/app/services/query_engine.py`):
  - Answers "Can I afford this?" questions.
  - Calculates EMI, savings reduction rate, buffer impact, and potential strain timeline.
  - Uses persona-specific financial context (warns students about semester fees and low allowance; warns freelancers about dry invoice months).
  - Generates 6-month projected savings comparison data for frontend charts.
- Simulators (`backend/app/services/simulator.py`):
  - Loan amortization schedule calculator.
  - One-time purchase impact simulator.
  - Savings goal timeline calculator.
- Forecaster (`backend/app/services/forecaster.py`):
  - Generates forward monthly cash flow estimates with confidence bands.
  - Computes backtest accuracy against historical actuals.

### 4. API Endpoints
- Auth:
  - `POST /api/auth/google`
  - `GET /api/auth/me`
  - `POST /api/auth/dev-login`
- Personas:
  - `GET /api/personas`
  - `GET /api/personas/active`
  - `POST /api/personas/switch/{persona_id}`
  - `POST /api/personas/seed-all`
- Transactions:
  - `POST /api/transactions/upload`
  - `GET /api/transactions`
  - `GET /api/transactions/summary`
  - `GET /api/transactions/{id}`
  - `PATCH /api/transactions/{id}`
  - `DELETE /api/transactions/{id}`
- Dashboard:
  - `GET /api/dashboard/overview`
  - `GET /api/dashboard/cashflow`
  - `GET /api/dashboard/spending-breakdown`
  - `GET /api/dashboard/health-score`
  - `GET /api/dashboard/budget-status`
- Decision Engine & Simulator:
  - `POST /api/query/ask`
  - `GET /api/query/history`
  - `POST /api/simulator/loan`
  - `POST /api/simulator/purchase`
  - `POST /api/simulator/savings-goal`
- Forecast & Alerts:
  - `GET /api/forecast/cashflow`
  - `GET /api/forecast/accuracy`
  - `GET /api/forecast/recurring`
  - `GET /api/forecast/liquidity`
  - `GET /api/alerts`
  - `PATCH /api/alerts/{id}/read`
  - `GET /api/alerts/upcoming`

### 5. Scripts and Utilities
- `scripts/generate_test_data.py`: generates 12-month synthetic CSVs for salaried, freelancer, and student profiles.
- `scripts/seed_db.py`: loads any CSV file into the SQLite database.
- `run_backend.sh`: one-command bash script to start the backend with venv and dependencies checked.

## What is Yet to be Implemented

1. Live Google Gemini API Integration:
   - Wire live Gemini 2.0 Flash API key to produce natural language responses in the query endpoint.
2. Advanced Time Series Models:
   - Evaluate Darts ExponentialSmoothing / Theta models on category-level forecasts.
3. Active Learning Feedback:
   - When a user updates a category via PATCH, update keyword mappings and retrain the classifier.
4. Alembic Migrations:
   - Configure Alembic with batch mode for SQLite schema migrations.

## How to Run

From the root project directory:
```bash
./run_backend.sh
```

Swagger API documentation:
http://localhost:8000/docs
