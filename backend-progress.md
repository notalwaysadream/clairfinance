# Backend Progress and Status

## Overview
This file tracks the architectural build status of the ClairFinance backend.
Tech stack: FastAPI, SQLAlchemy (async SQLite with aiosqlite), scikit-learn, google-genai, Alembic, and Pydantic.

## Implemented Features

### 1. Database and Project Setup
- FastAPI application in `backend/app/main.py` with CORS, health check endpoints, and automatic database initialization on startup.
- Async SQLite database engine in `backend/app/database.py`.
- Alembic database migration environment configured with SQLite batch mode (`render_as_batch=True`) in `backend/alembic/env.py`.
- SQLAlchemy ORM models in `backend/app/models/`:
  - `User`: User accounts, profile metadata, and authentication records.
  - `Category`: 18 standard financial categories (Salary, Rent, Groceries, Transport, Utilities, Loans, etc.).
  - `Transaction`: Bank transactions with date, amount, credit/debit type, payment mode, anomaly score, and recurring flag.
  - `ChatHistory`: Stored affordability questions and AI responses.
  - `Prediction`: Monthly forecasting records with lower and upper confidence bounds.
  - `Alert`: Spending alerts, upcoming bill reminders, and anomaly notifications.
  - `BudgetLimit`: Category budget limits with support for user overrides.
  - `RecurringPattern`: Detected recurring subscriptions, EMIs, and bills.
- Authentication in `backend/app/routers/auth.py` and `backend/app/utils/helpers.py`:
  - Google OAuth token verification (`POST /api/auth/google`).
  - Fallback developer mode for local testing without external Google Cloud setup (`POST /api/auth/dev-login`).
  - JWT token generation, expiration, and dependency injection route protection (`get_current_user`).

### 2. Multi-Persona Switcher
- Router in `backend/app/routers/personas.py`:
  - `salaried`: Rahul Sharma (fixed monthly salary, car loan EMI, rent, regular savings).
  - `freelancer`: Priya Patel (irregular client payments, software subscriptions, coworking).
  - `student`: Amit Verma (tight monthly allowance, mess fees, semester fee spikes).
- Endpoints:
  - `GET /api/personas`: List available personas and identify the currently active profile.
  - `GET /api/personas/active`: Retrieve the currently active persona profile.
  - `POST /api/personas/switch/{persona_id}`: Switch the active profile, dynamically load the 12-month synthetic transaction dataset, and return a fresh JWT.
  - `POST /api/personas/seed-all`: Pre-seed all three persona datasets simultaneously for immediate switching.

### 3. Core Processing Services and AI Integration
- Indian Bank Statement CSV Parser (`backend/app/services/csv_parser.py`):
  - Handles diverse Indian bank statement formats (separate Debit/Credit columns, single amount column with Cr/Dr indicators, negative values).
  - Automatically skips preamble bank account metadata.
  - Robust multi-format date parser (YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, DD MMM YYYY).
  - Automatic payment channel classification (UPI, NEFT, IMPS, Card, Auto-Debit, Cash).
- 3-Tier Cascading Transaction Categorizer (`backend/app/services/categorizer.py`):
  - Tier 1: High-precision keyword and merchant matching for 200+ Indian merchants.
  - Tier 2: Machine Learning classifier (TF-IDF vectorizer + LinearSVC) for unseen text patterns.
  - Tier 3: Live Google Gemini 2.0 Flash LLM batch classification for ambiguous descriptions.
  - Active Learning Feedback Loop: Captures user manual category corrections via `PATCH /api/transactions/{id}` and updates classifier memory.
- Google GenAI SDK Client (`backend/app/services/gemini_client.py`):
  - Integrated with the official unified `google-genai` SDK.
  - Built-in rate limiting (15 requests per minute protection).
  - In-memory SHA-256 TTL caching (5-minute expiration) to prevent redundant queries.
  - Exponential backoff retry logic on rate limit (HTTP 429) and transient network errors.
- Financial Health Scorer (`backend/app/services/health_scorer.py`):
  - 0 to 100 composite score derived from 5 weighted components:
    1. Savings rate (30% weight)
    2. Expense consistency (20% weight, coefficient of variation)
    3. Debt-to-income ratio (20% weight, EMI load)
    4. Emergency buffer coverage (15% weight, basic expense months)
    5. Spending diversity (15% weight, category Shannon entropy)
- Multi-Layered Anomaly Detection Engine (`backend/app/services/anomaly_detector.py`):
  - Layer 1: Category-level statistical Z-score outlier detection (|z| > 2.5).
  - Layer 2: Multi-dimensional scikit-learn IsolationForest (amount, day of week, day of month, category encoding).
  - Layer 3: Weekly category order frequency surge detection identifying sudden order pace anomalies.
- Recurring Payment Detector (`backend/app/services/recurring_detector.py`):
  - Mathematical interval clustering detecting weekly, monthly, quarterly, and annual commitments.
- Affordability Query Engine with Contextual Memory (`backend/app/services/query_engine.py`):
  - Answers "Can I afford this?" queries using structured financial metrics and Gemini 2.0 Flash advice.
  - Conversational memory: Injects the user's past 5 financial inquiries and verdicts into the LLM context.
  - Computes EMI schedules, savings reduction rates, emergency buffer impact, and potential strain timelines.
- Financial Simulators (`backend/app/services/simulator.py`):
  - Loan amortization calculator with month-by-month principal and interest schedules.
  - Large purchase impact simulator evaluating post-purchase emergency reserve recovery.
  - Savings goal timeline and required monthly contribution calculator.
  - What-If Scenario simulator projecting 6 to 24 month balances under custom income shifts and expense adjustments.
  - EMI Optimizer evaluating debt restructuring, prepayment impact, and tenure adjustment options.
- Time-Series Forecaster (`backend/app/services/forecaster.py`):
  - Cash flow projection model with exponential weighting, linear trend estimation, and lower/upper confidence intervals.
  - Category-specific spending forecaster with trend velocity and uncertainty intervals.
  - Historical backtesting engine (Financial Time Machine) calculating Mean Absolute Percentage Error (MAPE), accuracy percentage, and month-by-month actual versus predicted comparison points.
  - Automatically persists generated forward predictions to the SQLite `PREDICTIONS` database table for tracking and empirical verification.

### 4. Complete API Surface

#### Authentication
- `POST /api/auth/google`: Verify Google ID token, provision user, and return JWT.
- `GET /api/auth/me`: Get current authenticated user profile.
- `POST /api/auth/dev-login`: Issue developer test JWT.

#### Multi-Persona Management
- `GET /api/personas`: List test personas.
- `GET /api/personas/active`: Retrieve active persona.
- `POST /api/personas/switch/{persona_id}`: Switch active profile and load data.
- `POST /api/personas/seed-all`: Seed all test personas.

#### Categories
- `GET /api/categories`: List all 18 default categories with icons and hex colors.
- `GET /api/categories/{category_id}`: Get single category details.

#### Transactions
- `POST /api/transactions/upload`: Upload bank statement CSV with 3-tier auto-categorization and anomaly detection.
- `GET /api/transactions`: Paginated transaction list with date, category, and type filters.
- `GET /api/transactions/summary`: Aggregated total income, expenses, net savings, and savings rate.
- `GET /api/transactions/{id}`: Single transaction detail.
- `PATCH /api/transactions/{id}`: Update transaction (category update triggers active learning loop).
- `DELETE /api/transactions/{id}`: Delete a transaction.

#### Dashboard and Analytics
- `GET /api/dashboard/overview`: Complete dashboard summary with recent transactions and breakdowns.
- `GET /api/dashboard/cashflow`: Monthly historical income and expense points.
- `GET /api/dashboard/spending-breakdown`: Category-wise expense distribution.
- `GET /api/dashboard/health-score`: 5-factor composite score and recommendations.
- `GET /api/dashboard/budget-status`: Spending vs recommended and user-configured limits.
- `POST /api/dashboard/budget`: Set or update custom category budget limits.
- `GET /api/dashboard/personality`: Spending Personality Profile classifying users into financial archetypes.
- `GET /api/dashboard/benchmarks`: Anonymous peer benchmarking against cohort averages.
- `GET /api/dashboard/streaks`: Consecutive positive savings streaks and financial milestone achievements.
- `GET /api/dashboard/calendar`: Daily spending intensity heatmap data for calendar visualization.

#### Decision Engine and Simulators
- `POST /api/query/ask`: Submit financial questions and receive AI-backed affordability verdicts and impact charts.
- `GET /api/query/history`: Retrieve past affordability inquiries.
- `GET /api/query/{id}`: Get specific inquiry detail.
- `POST /api/simulator/loan`: Loan amortization simulation.
- `POST /api/simulator/purchase`: One-time purchase buffer depletion simulation.
- `POST /api/simulator/savings-goal`: Goal timeline and accelerator simulation.
- `POST /api/simulator/what-if`: Multi-variable what-if scenario projection.
- `POST /api/simulator/emi-optimizer`: Debt restructuring and EMI optimization comparing prepayment and tenure options.

#### Forecast and Predictions
- `GET /api/forecast/cashflow`: Forward 3 to 12 month cash flow forecasts with confidence bounds.
- `GET /api/forecast/category/{category_id}`: Category-specific spending forecast and trend velocity.
- `GET /api/forecast/categories`: Multi-category spending forecasts for all active categories.
- `GET /api/forecast/accuracy`: Empirical backtest evaluation (MAPE, accuracy %, and Financial Time Machine actual vs predicted comparison points).
- `GET /api/forecast/recurring`: Detected recurring subscriptions and bills.
- `GET /api/forecast/liquidity`: 30-day liquidity shortage risk evaluation.

#### Alerts and Anomalies
- `GET /api/alerts`: List user notifications (recurring bills, anomalies, low balance).
- `PATCH /api/alerts/{id}/read`: Mark alert as read.
- `GET /api/alerts/upcoming`: Upcoming recurring payments within specified day window.
- `GET /api/alerts/predictive`: Predictive alert engine evaluating category budget run-rate and liquidity crunch.
- `GET /api/anomalies`: List transactions flagged with anomaly scores.
- `GET /api/anomalies/patterns`: Summary of anomaly patterns across categories and days of week.

### 5. Automated Test Suite
- Comprehensive integration test suite in `backend/tests/test_api.py` covering all endpoints, persona switching, active learning feedback, simulators, and forecasting.

## How to Run

### Run Backend Server
From the root project directory:
```bash
./run_backend.sh
```

Or from the `backend/` directory:
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Run Automated Tests
```bash
cd backend
PYTHONPATH=. ./venv/bin/pytest tests/test_api.py -v
```

### Interactive API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
