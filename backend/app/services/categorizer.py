import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from app.services.gemini_client import gemini_client

logger = logging.getLogger(__name__)

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
    """
    3-Tier Cascading Transaction Categorization Engine:
    Tier 1: High-precision Keyword and Prefix Rules.
    Tier 2: Machine Learning Classifier (TF-IDF + LinearSVC).
    Tier 3: Google Gemini LLM fallback for ambiguous descriptions.
    Includes active learning feedback loop to record user corrections and adapt over time.
    """

    def __init__(self):
        self.user_corrections: Dict[str, str] = {}
        self.additional_training_samples: List[Tuple[str, str]] = []
        self._build_keyword_index()
        self._train_ml_fallback()

    def _clean_text(self, text: str) -> str:
        s = str(text).lower()
        # Remove common bank transaction prefixes
        s = re.sub(r"^(upi|pos|neft|imps|rtgs|ach|auto-debit|cr|dr)[-\s:]+", "", s)
        # Strip extraneous punctuation and numeric codes
        s = re.sub(r"[\d\-_/]+", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    def _build_keyword_index(self):
        self.exact_rules = []
        for category, keywords in KEYWORD_RULES.items():
            for kw in keywords:
                self.exact_rules.append((kw.lower(), category))
        # Sort by longest keyword first for maximal specificity
        self.exact_rules.sort(key=lambda x: len(x[0]), reverse=True)

    def _train_ml_fallback(self):
        corpus = []
        labels = []
        for category, keywords in KEYWORD_RULES.items():
            for kw in keywords:
                corpus.append(kw)
                labels.append(category)
                corpus.append(f"upi {kw} payment")
                labels.append(category)
                corpus.append(f"pos {kw} store")
                labels.append(category)

        # Incorporate dynamically learned user corrections
        for text, cat in self.additional_training_samples:
            corpus.append(text)
            labels.append(cat)

        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("clf", LinearSVC(dual="auto", max_iter=2000, random_state=42)),
        ])
        self.pipeline.fit(corpus, labels)

    def record_user_correction(self, raw_description: str, category_name: str):
        """
        Active learning hook: saves user-edited category mapping and updates
        the classifier training corpus for future classification consistency.
        """
        clean = self._clean_text(raw_description)
        desc_lower = raw_description.lower().strip()
        self.user_corrections[desc_lower] = category_name
        if clean:
            self.user_corrections[clean] = category_name
            self.additional_training_samples.append((clean, category_name))

        # Periodic retraining when sufficient corrections accumulate
        if len(self.additional_training_samples) % 5 == 0:
            try:
                self._train_ml_fallback()
                logger.info(
                    f"Retrained ML classifier with {len(self.additional_training_samples)} user corrections."
                )
            except Exception as e:
                logger.warning(f"Incremental retraining failed: {e}")

    def categorize(self, description: str, txn_type: str = "debit") -> Tuple[str, float]:
        """
        Categorizes a single transaction using Tier 1 rules and Tier 2 ML classifier.
        Returns (category_name, confidence).
        """
        desc_lower = str(description).lower().strip()
        clean_desc = self._clean_text(description)

        # Active Learning Check: direct match with user corrections
        if desc_lower in self.user_corrections:
            return self.user_corrections[desc_lower], 1.0
        if clean_desc in self.user_corrections:
            return self.user_corrections[clean_desc], 0.98

        # Prioritize Income / Salary keywords if transaction is credit
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

    async def categorize_batch_with_llm(
        self,
        transactions: List[Dict[str, Any]],
        available_categories: List[str]
    ) -> List[Tuple[str, float]]:
        """
        Runs the full 3-tier cascade on a batch of transactions.
        Unresolved or low-confidence transactions are submitted to Gemini Flash.
        """
        results: List[Tuple[str, float]] = []
        ambiguous_indices: List[int] = []
        ambiguous_descriptions: List[str] = []

        # Tiers 1 and 2
        for idx, txn in enumerate(transactions):
            desc = txn.get("description", "")
            ttype = txn.get("type", "debit")
            cat, conf = self.categorize(desc, txn_type=ttype)
            results.append((cat, conf))

            # Flag ambiguous items for Tier 3 LLM fallback
            if conf <= 0.60 or cat == "Miscellaneous":
                ambiguous_indices.append(idx)
                ambiguous_descriptions.append(desc)

        # Tier 3: Gemini LLM Fallback (batch limit up to 25 items per request)
        if gemini_client.is_available and ambiguous_descriptions:
            try:
                batch_to_send = ambiguous_descriptions[:25]
                llm_response = await gemini_client.batch_categorize_transactions(
                    batch_to_send,
                    available_categories
                )

                valid_cats = {c.lower(): c for c in available_categories}
                for item in llm_response:
                    if isinstance(item, dict) and "index" in item and "category" in item:
                        item_idx = int(item["index"]) - 1
                        assigned_cat = item["category"].strip()
                        if 0 <= item_idx < len(ambiguous_indices):
                            target_original_idx = ambiguous_indices[item_idx]
                            matched_cat = valid_cats.get(assigned_cat.lower())
                            if matched_cat:
                                results[target_original_idx] = (matched_cat, 0.90)
                                # Add to active learning memory
                                self.record_user_correction(
                                    ambiguous_descriptions[item_idx],
                                    matched_cat
                                )
            except Exception as e:
                logger.warning(f"Tier 3 Gemini categorization failed: {e}")

        return results

categorizer = TransactionCategorizer()
