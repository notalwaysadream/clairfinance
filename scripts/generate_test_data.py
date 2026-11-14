#!/usr/bin/env python3
"""
Test Data Generator for Clairfinance
Generates realistic 12-month transaction histories for 3 Indian personas:
1. Salaried Employee
2. Freelancer
3. Student
"""

import os
import random
import argparse
from datetime import date, timedelta
from pathlib import Path

FOOD_MERCHANTS = [
    ("UPI-SWIGGY-FOOD ORDER", "UPI", 150, 950),
    ("UPI-ZOMATO-RESTAURANT", "UPI", 220, 1200),
    ("UPI-DOMINOS PIZZA", "UPI", 350, 990),
    ("POS-MCDONALD'S", "Card", 200, 650),
    ("UPI-STARBUCKS COFFEE", "UPI", 320, 850),
    ("UPI-CHAI POINT", "UPI", 80, 250),
    ("UPI-BLINKIT GROCERY", "UPI", 250, 1800),
    ("UPI-ZEPTO GROCERY", "UPI", 180, 1400),
    ("POS-DMART SUPERMARKET", "Card", 1200, 5500),
    ("UPI-BIGBASKET", "UPI", 800, 3200),
    ("UPI-HALDIRAMS", "UPI", 250, 900),
    ("POS-BARBEQUE NATION", "Card", 1600, 3400),
]

TRANSPORT_MERCHANTS = [
    ("UPI-UBER INDIA", "UPI", 120, 750),
    ("UPI-OLA CABS", "UPI", 95, 680),
    ("UPI-RAPIDO BIKE", "UPI", 45, 180),
    ("POS-SHELL PETROL PUMP", "Card", 500, 2800),
    ("POS-INDIAN OIL PETROL", "Card", 400, 2500),
    ("POS-HP PETROL PUMP", "Card", 300, 2200),
    ("UPI-METRO RECHARGE", "UPI", 100, 500),
    ("UPI-IRCTC RAIL TICKET", "UPI", 450, 2400),
    ("POS-FASTAG TOLL RECHARGE", "UPI", 500, 1000),
]

SHOPPING_MERCHANTS = [
    ("UPI-AMAZON PAY INDIA", "UPI", 350, 4500),
    ("POS-FLIPKART INTERNET", "Card", 499, 6200),
    ("UPI-MYNTRA FASHION", "UPI", 899, 3500),
    ("POS-CROMA ELECTRONICS", "Card", 1200, 14000),
    ("POS-RELIANCE DIGITAL", "Card", 800, 8500),
    ("UPI-NYKAA BEAUTY", "UPI", 450, 2200),
    ("UPI-AJIO APPAREL", "UPI", 700, 2800),
    ("POS-DECATHLON SPORTS", "Card", 600, 4200),
    ("UPI-MEESHO ONLINE", "UPI", 250, 1100),
]

SUBSCRIPTION_MERCHANTS = [
    ("AUTO-DEBIT-NETFLIX INDIA", "Auto-Debit", 649, 649),
    ("AUTO-DEBIT-SPOTIFY INDIA", "Auto-Debit", 119, 119),
    ("AUTO-DEBIT-YOUTUBE PREMIUM", "Auto-Debit", 149, 149),
    ("AUTO-DEBIT-AMAZON PRIME", "Auto-Debit", 299, 299),
    ("AUTO-DEBIT-DISNEY HOTSTAR", "Auto-Debit", 299, 299),
    ("AUTO-DEBIT-APPLE ICLOUD", "Auto-Debit", 75, 219),
    ("AUTO-DEBIT-GOOGLE ONE", "Auto-Debit", 130, 130),
]

UTILITY_MERCHANTS = [
    ("UPI-BESCOM ELECTRICITY", "UPI", 850, 2800),
    ("UPI-ACT FIBERNET BROADBAND", "UPI", 943, 1179),
    ("UPI-INDANE GAS CYLINDER", "UPI", 850, 950),
    ("UPI-AIRTEL POSTPAID BILL", "UPI", 499, 999),
]

def generate_salaried(months: int = 12) -> list:
    txns = []
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)
    salary_amount = random.choice([75000.0, 85000.0, 95000.0, 110000.0])

    curr = start_date
    while curr <= end_date:
        # Salary credit on the 1st
        if curr.day == 1:
            txns.append({
                "Date": curr.strftime("%Y-%m-%d"),
                "Description": "NEFT-CREDIT-SALARY-ACME TECHNOLOGIES",
                "Amount": salary_amount,
                "Type": "credit",
                "Mode": "NEFT"
            })
            # Rent paid between 1st and 3rd
            txns.append({
                "Date": (curr + timedelta(days=random.randint(1, 3))).strftime("%Y-%m-%d"),
                "Description": "UPI-HOUSE RENT-NOBROKER",
                "Amount": random.choice([15000.0, 18000.0, 20000.0]),
                "Type": "debit",
                "Mode": "UPI"
            })
            # Car / Personal EMI on 5th
            txns.append({
                "Date": (curr + timedelta(days=4)).strftime("%Y-%m-%d"),
                "Description": "ACH-DEBIT-HDFC BANK CAR LOAN EMI",
                "Amount": 9500.0,
                "Type": "debit",
                "Mode": "Auto-Debit"
            })
            # SIP on 7th
            txns.append({
                "Date": (curr + timedelta(days=6)).strftime("%Y-%m-%d"),
                "Description": "AUTO-DEBIT-ZERODHA NIFTY 50 INDEX SIP",
                "Amount": 5000.0,
                "Type": "debit",
                "Mode": "Auto-Debit"
            })

        # Subscriptions on recurring days
        if curr.day == 15:
            for desc, mode, low, high in SUBSCRIPTION_MERCHANTS[:3]:
                txns.append({
                    "Date": curr.strftime("%Y-%m-%d"),
                    "Description": desc,
                    "Amount": float(low),
                    "Type": "debit",
                    "Mode": mode
                })

        # Utilities on 10th
        if curr.day == 10:
            for desc, mode, low, high in UTILITY_MERCHANTS[:2]:
                txns.append({
                    "Date": curr.strftime("%Y-%m-%d"),
                    "Description": desc,
                    "Amount": float(random.randint(low, high)),
                    "Type": "debit",
                    "Mode": mode
                })

        # Daily variable: Food & Transport
        is_weekend = curr.weekday() >= 5
        if random.random() < (0.50 if is_weekend else 0.30):
            desc, mode, low, high = random.choice(FOOD_MERCHANTS)
            txns.append({
                "Date": curr.strftime("%Y-%m-%d"),
                "Description": desc,
                "Amount": float(random.randint(low, high)),
                "Type": "debit",
                "Mode": mode
            })

        if random.random() < 0.25:
            desc, mode, low, high = random.choice(TRANSPORT_MERCHANTS)
            txns.append({
                "Date": curr.strftime("%Y-%m-%d"),
                "Description": desc,
                "Amount": float(random.randint(low, high)),
                "Type": "debit",
                "Mode": mode
            })

        # Occasional shopping (1-2 times a month)
        if random.random() < 0.08:
            desc, mode, low, high = random.choice(SHOPPING_MERCHANTS)
            txns.append({
                "Date": curr.strftime("%Y-%m-%d"),
                "Description": desc,
                "Amount": float(random.randint(low, min(high, 4000))),
                "Type": "debit",
                "Mode": mode
            })

        curr += timedelta(days=1)

    # Inject 1-2 realistic anomalies (hospital/wedding gift)
    anomaly_dates = [start_date + timedelta(days=90), start_date + timedelta(days=240)]
    txns.append({
        "Date": anomaly_dates[0].strftime("%Y-%m-%d"),
        "Description": "POS-APOLLO HOSPITAL EMERGENCY",
        "Amount": 18500.0,
        "Type": "debit",
        "Mode": "Card"
    })
    txns.append({
        "Date": anomaly_dates[1].strftime("%Y-%m-%d"),
        "Description": "UPI-WEDDING GIFT TRANSFER",
        "Amount": 10000.0,
        "Type": "debit",
        "Mode": "UPI"
    })

    return sorted(txns, key=lambda x: x["Date"])

def generate_freelancer(months: int = 12) -> list:
    txns = []
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)

    curr = start_date
    while curr <= end_date:
        # Irregular client payments (2-4 times a month on random days)
        if random.random() < 0.10:
            client_name = random.choice(["Fintech US Corp", "Design Studio EU", "EdTech Startup", "HealthApp Inc"])
            amount = random.choice([25000.0, 45000.0, 75000.0, 95000.0, 120000.0])
            txns.append({
                "Date": curr.strftime("%Y-%m-%d"),
                "Description": f"NEFT-CLIENT PAYMENT-{client_name}",
                "Amount": amount,
                "Type": "credit",
                "Mode": "NEFT"
            })

        # Rent on 1st-4th
        if curr.day == 2:
            txns.append({
                "Date": curr.strftime("%Y-%m-%d"),
                "Description": "UPI-HOUSE RENT-LANDLORD",
                "Amount": 20000.0,
                "Type": "debit",
                "Mode": "UPI"
            })
            # Coworking space
            txns.append({
                "Date": curr.strftime("%Y-%m-%d"),
                "Description": "POS-WEWORK COWORKING MEMBERSHIP",
                "Amount": 7500.0,
                "Type": "debit",
                "Mode": "Card"
            })

        # Software / tools on 12th
        if curr.day == 12:
            txns.append({
                "Date": curr.strftime("%Y-%m-%d"),
                "Description": "AUTO-DEBIT-FIGMA DESIGN PRO",
                "Amount": 1250.0,
                "Type": "debit",
                "Mode": "Card"
            })
            txns.append({
                "Date": curr.strftime("%Y-%m-%d"),
                "Description": "AUTO-DEBIT-AWS CLOUD HOSTING",
                "Amount": 3400.0,
                "Type": "debit",
                "Mode": "Card"
            })

        # Variable Food & Transport
        if random.random() < 0.70:
            desc, mode, low, high = random.choice(FOOD_MERCHANTS)
            txns.append({
                "Date": curr.strftime("%Y-%m-%d"),
                "Description": desc,
                "Amount": float(random.randint(low, high)),
                "Type": "debit",
                "Mode": mode
            })

        if random.random() < 0.35:
            desc, mode, low, high = random.choice(TRANSPORT_MERCHANTS)
            txns.append({
                "Date": curr.strftime("%Y-%m-%d"),
                "Description": desc,
                "Amount": float(random.randint(low, high)),
                "Type": "debit",
                "Mode": mode
            })

        curr += timedelta(days=1)

    return sorted(txns, key=lambda x: x["Date"])

def generate_student(months: int = 12) -> list:
    txns = []
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)

    curr = start_date
    while curr <= end_date:
        # Family allowance on 1st
        if curr.day == 1:
            txns.append({
                "Date": curr.strftime("%Y-%m-%d"),
                "Description": "UPI-TRANSFER FROM FAMILY-POCKET MONEY",
                "Amount": random.choice([8000.0, 10000.0, 12000.0]),
                "Type": "credit",
                "Mode": "UPI"
            })
            # Hostel / Mess Fee
            txns.append({
                "Date": curr.strftime("%Y-%m-%d"),
                "Description": "UPI-CAMPUS MESS MONTHLY FEE",
                "Amount": 4200.0,
                "Type": "debit",
                "Mode": "UPI"
            })

        # Occasional tutoring/part-time gig
        if curr.day == 18 and random.random() < 0.70:
            txns.append({
                "Date": curr.strftime("%Y-%m-%d"),
                "Description": "UPI-STUDENT TUTORING STIPEND",
                "Amount": random.choice([3000.0, 5000.0]),
                "Type": "credit",
                "Mode": "UPI"
            })

        # Semester Fee Spike in Months 1 and 7
        if (curr - start_date).days in [30, 210]:
            txns.append({
                "Date": curr.strftime("%Y-%m-%d"),
                "Description": "NEFT-SEMESTER TUITION FEE-ENGINEERING COLLEGE",
                "Amount": 45000.0,
                "Type": "debit",
                "Mode": "NEFT"
            })
            txns.append({
                "Date": (curr - timedelta(days=2)).strftime("%Y-%m-%d"),
                "Description": "NEFT-FAMILY EDUCATION SUPPORT FOR FEES",
                "Amount": 45000.0,
                "Type": "credit",
                "Mode": "NEFT"
            })

        # Micro UPI transactions: chai, snacks, books
        if random.random() < 0.75:
            item = random.choice([
                ("UPI-CHAI & MAGGI CORNER", 35, 120),
                ("UPI-COLLEGE CANTEEN SNACKS", 50, 180),
                ("UPI-CAMPUS STATIONERY & XEROX", 20, 150),
                ("UPI-ZEPTO QUICK SNACKS", 80, 320),
                ("UPI-METRO BUS FARE", 25, 60),
                ("UPI-SPOTIFY STUDENT PLAN", 59, 59),
            ])
            txns.append({
                "Date": curr.strftime("%Y-%m-%d"),
                "Description": item[0],
                "Amount": float(random.randint(item[1], item[2])),
                "Type": "debit",
                "Mode": "UPI"
            })

        curr += timedelta(days=1)

    return sorted(txns, key=lambda x: x["Date"])

def save_csv(filepath: Path, txns: list):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("Date,Description,Amount,Type,Mode\n")
        for t in txns:
            f.write(f"{t['Date']},{t['Description']},{t['Amount']:.2f},{t['Type']},{t['Mode']}\n")

    income = sum(t["Amount"] for t in txns if t["Type"] == "credit")
    expenses = sum(t["Amount"] for t in txns if t["Type"] == "debit")
    savings_rate = ((income - expenses) / income * 100.0) if income > 0 else 0.0

    print(f"Generated: {filepath.name}")
    print(f"  • Total transactions: {len(txns)}")
    print(f"  • Date range: {txns[0]['Date']} to {txns[-1]['Date']}")
    print(f"  • Total Income: ₹{income:,.2f}")
    print(f"  • Total Expenses: ₹{expenses:,.2f}")
    print(f"  • Savings Rate: {savings_rate:.1f}%\n")

def main():
    parser = argparse.ArgumentParser(description="Generate Indian transaction datasets for test personas.")
    parser.add_argument("--persona", choices=["salaried", "freelancer", "student", "all"], default="all")
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--output-dir", type=str, default="./data")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    out_dir = Path(args.output_dir)

    if args.persona in ["salaried", "all"]:
        data = generate_salaried(args.months)
        save_csv(out_dir / "salaried_transactions.csv", data)

    if args.persona in ["freelancer", "all"]:
        data = generate_freelancer(args.months)
        save_csv(out_dir / "freelancer_transactions.csv", data)

    if args.persona in ["student", "all"]:
        data = generate_student(args.months)
        save_csv(out_dir / "student_transactions.csv", data)

if __name__ == "__main__":
    main()
