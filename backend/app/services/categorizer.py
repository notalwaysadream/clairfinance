import re
from typing import Dict, List, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline

KEYWORD_RULES = {
    # Salary / Income
    "Salary/Income": [
        "salary", "payroll", "acme", "infosys", "tcs", "wipro", "hcl", "tech mahindra",
        "stipend", "bonus", "allowance", "incentive", "neft-credit-salary", "ach-salary",
        "salary credit", "employer", "corp salary", "direct dep", "pension"
    ],
    # Freelance Income
    "Freelance Income": [
        "client payment", "freelance", "upwork", "fiverr", "toptal", "consulting fee",
        "project fee", "design fee", "development fee", "retainer", "invoice payment",
        "freelance -", "project -"
    ],
    # Rent & Housing
    "Rent & Housing": [
        "rent", "nobroker", "housing", "landlord", "flat rent", "house rent", "maintenance",
        "society maintenance", "apartment", "mygate", "nestaway", "co-living", "pg rent"
    ],
    # Food & Dining
    "Food & Dining": [
        "swiggy", "zomato", "blinkit", "zepto", "bigbasket", "instamart", "dominos",
        "mcdonald", "starbucks", "chai point", "haldirams", "bbq nation", "barbeque",
        "subway", "kfc", "burger king", "pizza hut", "dmart", "more supermarket",
        "nature's basket", "dunzo", "restaurant", "cafe", "dhaba", "canteen", "mess",
        "kitchen", "bakery", "sweets", "bistro", "eats", "food order"
    ],
    # Transport
    "Transport": [
        "uber", "ola", "rapido", "petrol", "diesel", "fuel", "indian oil", "hp petrol",
        "shell petrol", "bharat petroleum", "iocl", "bpcl", "metro recharge", "metro rail",
        "irctc", "rail ticket", "fastag", "toll", "bounce", "yulu", "cab", "auto fare",
        "parking", "flight", "indigo", "air india"
    ],
    # Shopping
    "Shopping": [
        "amazon", "flipkart", "myntra", "croma", "reliance digital", "nykaa", "ajio",
        "westside", "decathlon", "meesho", "zara", "h&m", "uniqlo", "lifestyle",
        "shoppers stop", "tatacliq", "retail", "clothing", "apparel", "footwear", "mall"
    ],
    # Subscriptions
    "Subscriptions": [
        "netflix", "spotify", "youtube premium", "amazon prime", "hotstar", "disney",
        "apple icloud", "google one", "linkedin premium", "coursera plus", "medium",
        "github", "chatgpt", "openai", "claude", "notion", "figma", "audible", "times prime"
    ],
    # Utilities
    "Utilities": [
        "electricity", "bescom", "tneb", "mseb", "uppcl", "water bill", "indane gas",
        "hp gas", "bharat gas", "piped gas", "broadband", "act fibernet", "airtel broadband",
        "jio fiber", "tataplay broadband", "hathway", "utility"
    ],
    # Recharge & Bills
    "Recharge & Bills": [
        "mobile recharge", "prepaid recharge", "postpaid bill", "airtel recharge",
        "jio recharge", "vi recharge", "dth recharge", "tata play", "dish tv", "sun direct"
    ],
    # Healthcare
    "Healthcare": [
        "apollo", "1mg", "tata 1mg", "pharmeasy", "netmeds", "hospital", "clinic",
        "pharmacy", "chemist", "medplus", "doctor", "dentist", "diagnostic", "dr lal",
        "pathlab", "healthcare", "lenskart", "practo"
    ],
    # Education
    "Education": [
        "semester fee", "college fee", "school fee", "tuition", "exam fee", "udemy",
        "coursera", "edx", "unacademy", "byjus", "physics wallah", "books", "library",
        "stationery", "university"
    ],
    # Entertainment
    "Entertainment": [
        "pvr", "inox", "cinepolis", "bookmyshow", "cinema", "movie", "steam games",
        "playstation", "xbox", "nintendo", "theme park", "amusement", "concert", "event"
    ],
    # EMI & Loans
    "EMI & Loans": [
        "emi", "loan", "bajaj finance", "hdfc loan", "sbi loan", "icici loan",
        "home loan emi", "car loan emi", "personal loan emi", "credit card payment",
        "cred", "slice", "uni card", "onecard", "zestmoney", "stashfin"
    ],
    # Transfers
    "Transfers": [
        "transfer to", "sent to", "upi to", "neft to", "imps to", "family transfer",
        "pocket money", "reimbursement", "sent money"
    ],
    # Investments
    "Investments": [
        "zerodha", "groww", "kuvera", "etmoney", "indmoney", "sip", "mutual fund",
        "camsonline", "kfintech", "coin", "upstox", "angelone", "national pension",
        "nps", "fixed deposit", "recurring deposit", "gold sovereign"
    ],
    # Gifts & Donations
    "Gifts & Donations": [
        "gift", "donation", "charity", "pm cares", "ngo", "akshaya patra", "cry",
        "temple donation", "wedding gift"
    ],
    # Travel
    "Travel": [
        "makemytrip", "goibibo", "cleartrip", "easemytrip", "booking.com", "agoda",
        "airbnb", "hotel", "resort", "homestay", "tour", "travels"
    ],
}

class TransactionCategorizer:
    def __init__(self):
        self._build_keyword_index()
        self._train_ml_fallback()

    def _clean_text(self, text: str) -> str:
        s = str(text).lower()
        # Remove common bank prefixes
        s = re.sub(r"^(upi|pos|neft|imps|rtgs|ach|auto-debit|cr|dr)[-\s:]+", "", s)
        # Strip extraneous punctuation and numbers
        s = re.sub(r"[\d\-_/]+", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    def _build_keyword_index(self):
        self.exact_rules = []
        for category, keywords in KEYWORD_RULES.items():
            for kw in keywords:
                self.exact_rules.append((kw.lower(), category))
        # Sort by longest keyword first so more specific patterns match before generic ones
        self.exact_rules.sort(key=lambda x: len(x[0]), reverse=True)

    def _train_ml_fallback(self):
        corpus = []
        labels = []
        for category, keywords in KEYWORD_RULES.items():
            for kw in keywords:
                corpus.append(kw)
                labels.append(category)
                # Augmented examples
                corpus.append(f"upi {kw} payment")
                labels.append(category)
                corpus.append(f"pos {kw} store")
                labels.append(category)

        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("clf", LinearSVC(dual="auto", max_iter=2000, random_state=42)),
        ])
        self.pipeline.fit(corpus, labels)

    def categorize(self, description: str, txn_type: str = "debit") -> Tuple[str, float]:
        """
        Categorizes a transaction string.
        Returns (category_name, confidence).
        """
        desc_lower = str(description).lower()
        clean_desc = self._clean_text(description)

        # Salary / Income prioritization if credit
        if txn_type == "credit":
            for kw in ["salary", "payroll", "acme", "employer", "stipend", "bonus"]:
                if kw in desc_lower:
                    return "Salary/Income", 0.99
            for kw in ["client", "freelance", "project", "upwork", "fiverr", "invoice"]:
                if kw in desc_lower:
                    return "Freelance Income", 0.95
            for kw in ["dividend", "interest", "fd interest"]:
                if kw in desc_lower:
                    return "Investments", 0.90
            for kw in ["refund", "cashback"]:
                return "Miscellaneous", 0.85

        # Tier 1: Exact keyword match
        for kw, cat in self.exact_rules:
            if kw in desc_lower:
                return cat, 0.95

        # Tier 2: ML Fallback
        try:
            if clean_desc and len(clean_desc) >= 3:
                predicted = self.pipeline.predict([clean_desc])[0]
                return predicted, 0.75
        except Exception:
            pass

        return "Miscellaneous", 0.50

categorizer = TransactionCategorizer()
