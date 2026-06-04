"""
Script 01: Generate Dummy Financial Data
=========================================
Purpose : Simulate messy exports from QuickBooks / Sage 50 for
          a small accounting firm client (Northgate Advisory Partners).

What it creates
---------------
  data/raw/general_ledger_raw.csv   — 200 rows of messy GL transactions
  data/raw/accounts_receivable_raw.csv — 80 rows of messy AR invoices

"Mess" intentionally baked in (to mimic real exports):
  - Mixed date formats (MM/DD/YYYY, DD-Mon-YYYY, YYYY-MM-DD, blanks)
  - Dollar signs and commas inside numeric fields
  - Inconsistent account code formats (plain number vs "ACC-XXXX")
  - Mixed case in text fields ("revenue", "REVENUE", "Revenue")
  - Duplicate rows
  - Blank / NaN rows
  - Trailing / leading whitespace in string columns

AI Credit: Data generation logic drafted with Google Gemini (free tier),
           then refined here.
"""

import pandas as pd
import numpy as np
import random
import os

# ── Reproducibility ────────────────────────────────────────────────────────────
random.seed(42)
np.random.seed(42)

# ── Output paths ───────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE, "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# 1.  GENERAL LEDGER
# ══════════════════════════════════════════════════════════════════════════════

ACCOUNTS = [
    ("1000", "Cash and Bank"),
    ("1100", "Accounts Receivable"),
    ("2000", "Accounts Payable"),
    ("4000", "Revenue - Consulting"),
    ("4100", "Revenue - Retainer"),
    ("5000", "Salaries Expense"),
    ("5100", "Rent Expense"),
    ("5200", "Software Subscriptions"),
    ("5300", "Marketing Expense"),
    ("5400", "Office Supplies"),
]

DEPARTMENTS = ["Operations", "Finance", " Sales", "Admin", "SALES", "finance", "operations"]
DESCRIPTIONS = [
    "Client invoice payment received",
    "Monthly office rent",
    "Payroll run",
    "Software licence renewal",
    "Google Ads campaign",
    "Consulting fees billed",
    "Retainer fee - Q1",
    "Office supply purchase",
    "Bank charges",
    "Tax remittance",
    "  Consulting fees billed  ",   # trailing/leading spaces
    "client invoice payment received",  # lowercase duplicate style
]

def messy_date(base_date):
    """Return the same date in one of several inconsistent formats, or blank."""
    formats = [
        base_date.strftime("%m/%d/%Y"),          # 01/15/2024
        base_date.strftime("%d-%b-%Y"),           # 15-Jan-2024
        base_date.strftime("%Y-%m-%d"),           # 2024-01-15
        base_date.strftime("%d/%m/%Y"),           # 15/01/2024  (ambiguous)
        base_date.strftime("%B %d, %Y"),          # January 15, 2024
        "",                                       # blank
    ]
    return random.choice(formats)

def messy_amount(amount):
    """Return amount as a clean float, dollar-string, or comma-formatted string."""
    styles = [
        f"{amount:.2f}",
        f"${amount:,.2f}",
        f"{amount:,.2f}",
        str(int(amount)),
    ]
    return random.choice(styles)

def messy_account_code(code):
    """Return account code in one of several inconsistent formats."""
    styles = [
        code,
        f"ACC-{code}",
        f"{code} ",           # trailing space
        code.lower(),
    ]
    return random.choice(styles)

# Generate 190 real rows
dates = pd.date_range("2024-01-01", "2024-12-31", periods=190)
gl_rows = []
for i, date in enumerate(dates):
    acc_code, acc_name = random.choice(ACCOUNTS)
    is_revenue = acc_code.startswith("4")
    amount = round(random.uniform(200, 15000), 2)
    debit  = amount if not is_revenue else 0
    credit = amount if is_revenue else 0

    gl_rows.append({
        "Date"           : messy_date(date),
        "Transaction_ID" : f"TXN-{1000 + i}" if random.random() > 0.05 else "",
        "Account_Code"   : messy_account_code(acc_code),
        "Account_Name"   : random.choice([acc_name, acc_name.upper(), acc_name.lower()]),
        "Description"    : random.choice(DESCRIPTIONS),
        "Debit"          : messy_amount(debit) if debit else "",
        "Credit"         : messy_amount(credit) if credit else "",
        "Department"     : random.choice(DEPARTMENTS),
        "Notes"          : random.choice(["", "Approved", "APPROVED", "approved", "  ", "Pending review"]),
    })

gl_df = pd.DataFrame(gl_rows)

# Add 5 duplicate rows
duplicates = gl_df.sample(5, random_state=1)
gl_df = pd.concat([gl_df, duplicates], ignore_index=True)

# Add 5 completely blank rows
blank_rows = pd.DataFrame([{col: "" for col in gl_df.columns}] * 5)
gl_df = pd.concat([gl_df, blank_rows], ignore_index=True)

# Shuffle
gl_df = gl_df.sample(frac=1, random_state=7).reset_index(drop=True)

gl_df.to_csv(os.path.join(RAW_DIR, "general_ledger_raw.csv"), index=False)
print(f"✓ General Ledger created: {len(gl_df)} rows  →  data/raw/general_ledger_raw.csv")


# ══════════════════════════════════════════════════════════════════════════════
# 2.  ACCOUNTS RECEIVABLE
# ══════════════════════════════════════════════════════════════════════════════

CUSTOMERS = [
    "Maple Leaf Consulting",
    "maple leaf consulting",          # same customer, different casing
    "MAPLE LEAF CONSULTING",
    "Rideau Tech Solutions",
    "Rideau Tech Solutions Ltd.",
    "Northern Lights Retail",
    "NorthernLights Retail",          # no space variant
    "Bytown Manufacturing",
    "Bytown Manufacturing Inc",
    "Capital City Lawyers",
    "Capital City Lawyers LLP",
    "Gatineau Services",
]

STATUSES = ["Open", "OPEN", "open", "Paid", "PAID", "paid", "Overdue", "OVERDUE", "Partial"]

ar_rows = []
for i in range(75):
    inv_date = pd.Timestamp("2024-01-01") + pd.Timedelta(days=random.randint(0, 364))
    due_date = inv_date + pd.Timedelta(days=random.choice([30, 45, 60]))
    amount_due = round(random.uniform(500, 20000), 2)
    status = random.choice(STATUSES)

    if "paid" in status.lower():
        amount_paid = amount_due
    elif status.lower() == "partial":
        amount_paid = round(amount_due * random.uniform(0.3, 0.7), 2)
    else:
        amount_paid = 0

    ar_rows.append({
        "Invoice_Date"   : messy_date(inv_date),
        "Invoice_Number" : f"INV-{2000 + i}" if random.random() > 0.04 else "",
        "Customer_Name"  : random.choice(CUSTOMERS),
        "Amount_Due"     : messy_amount(amount_due),
        "Amount_Paid"    : messy_amount(amount_paid) if amount_paid else "",
        "Due_Date"       : messy_date(due_date),
        "Status"         : status,
        "Notes"          : random.choice(["", "Follow up", "FOLLOW UP", "  ", "Disputed"]),
    })

ar_df = pd.DataFrame(ar_rows)

# Add duplicates and blank rows
ar_df = pd.concat([ar_df, ar_df.sample(3, random_state=2)], ignore_index=True)
blank_ar = pd.DataFrame([{col: "" for col in ar_df.columns}] * 2)
ar_df = pd.concat([ar_df, blank_ar], ignore_index=True)
ar_df = ar_df.sample(frac=1, random_state=8).reset_index(drop=True)

ar_df.to_csv(os.path.join(RAW_DIR, "accounts_receivable_raw.csv"), index=False)
print(f"✓ Accounts Receivable created: {len(ar_df)} rows  →  data/raw/accounts_receivable_raw.csv")
print("\nRun 02_clean_data.py next.")
