from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.chat_history import ChatHistory
from app.models.prediction import Prediction
from app.models.alert import Alert, BudgetLimit, RecurringPattern

DEFAULT_CATEGORIES = [
    {"name": "Salary/Income", "icon": "wallet", "color": "#22c55e"},
    {"name": "Rent & Housing", "icon": "home", "color": "#ef4444"},
    {"name": "Food & Dining", "icon": "utensils", "color": "#f97316"},
    {"name": "Transport", "icon": "car", "color": "#3b82f6"},
    {"name": "Shopping", "icon": "shopping-bag", "color": "#a855f7"},
    {"name": "Subscriptions", "icon": "tv", "color": "#ec4899"},
    {"name": "Utilities", "icon": "zap", "color": "#eab308"},
    {"name": "Healthcare", "icon": "heart-pulse", "color": "#14b8a6"},
    {"name": "Education", "icon": "book-open", "color": "#6366f1"},
    {"name": "Entertainment", "icon": "gamepad", "color": "#f43f5e"},
    {"name": "EMI & Loans", "icon": "credit-card", "color": "#dc2626"},
    {"name": "Transfers", "icon": "repeat", "color": "#64748b"},
    {"name": "Investments", "icon": "trending-up", "color": "#059669"},
    {"name": "Gifts & Donations", "icon": "gift", "color": "#d946ef"},
    {"name": "Miscellaneous", "icon": "circle", "color": "#78716c"},
    {"name": "Recharge & Bills", "icon": "phone", "color": "#0ea5e9"},
    {"name": "Travel", "icon": "plane", "color": "#8b5cf6"},
    {"name": "Freelance Income", "icon": "briefcase", "color": "#10b981"},
]

__all__ = [
    "User",
    "Category",
    "Transaction",
    "ChatHistory",
    "Prediction",
    "Alert",
    "BudgetLimit",
    "RecurringPattern",
    "DEFAULT_CATEGORIES"
]
