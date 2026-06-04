"""
Script 02: Clean the Raw Financial Data
=========================================
Purpose : Take the messy raw CSVs produced by 01_generate_data.py and
          output clean, analysis-ready CSVs.

What it fixes
-------------
  Dates        → parse all inconsistent formats into one standard YYYY-MM-DD
  Numbers      → strip "$" and "," then cast to float
  Account codes → normalise to plain 4-digit code (strip "ACC-" prefix, spaces)
  Text fields  → strip whitespace, title-case for consistency
  Duplicates   → drop exact duplicate rows
  Blank rows   → drop rows where every critical field is empty
  Status       → normalise to title case (Open, Paid, Overdue, Partial)

AI Credit: Cleaning logic and pandas patterns written with Claude.

Output
------
  data/clean/general_ledger_clean.csv
  data/clean/accounts_receivable_clean.csv
"""

import pandas as pd
import numpy as np
import re
import os

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR   = os.path.join(BASE, "data", "raw")
CLEAN_DIR = os.path.join(BASE, "data", "clean")
os.makedirs(CLEAN_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# Helper functions
# ══════════════════════════════════════════════════════════════════════════════

def parse_date(val):
    """
    Try to parse a date string in any format pandas can recognise.
    Returns a pd.Timestamp on success, NaT (not-a-time) on failure.
    """
    if pd.isna(val) or str(val).strip() == "":
        return pd.NaT
    try:
        # dayfirst=False so MM/DD/YYYY is preferred over DD/MM/YYYY
        return pd.to_datetime(str(val).strip(), dayfirst=False)
    except Exception:
        return pd.NaT


def clean_amount(val):
    """
    Strip currency symbols and commas, then convert to float.
    Returns NaN if the value is empty or unparseable.
    """
    if pd.isna(val) or str(val).strip() in ("", "0"):
        return np.nan
    cleaned = re.sub(r"[\$,]", "", str(val).strip())  # remove $ and ,
    try:
        return float(cleaned)
    except ValueError:
        return np.nan


def clean_account_code(val):
    """
    Normalise account codes to plain digits (e.g. 'ACC-1000 ' → '1000').
    """
    if pd.isna(val) or str(val).strip() == "":
        return np.nan
    code = str(val).strip().upper()
    code = re.sub(r"[^0-9]", "", code)   # keep only digits
    return code if code else np.nan


# ══════════════════════════════════════════════════════════════════════════════
# 1.  Clean General Ledger
# ══════════════════════════════════════════════════════════════════════════════

print("Cleaning General Ledger...")
gl = pd.read_csv(os.path.join(RAW_DIR, "general_ledger_raw.csv"), dtype=str)

# Step 1 – Drop completely blank rows (all critical columns empty)
critical_gl = ["Date", "Account_Code", "Debit", "Credit"]
gl.dropna(how="all", inplace=True)                           # all NaN
gl = gl[~(gl[critical_gl].apply(lambda r: r.str.strip().eq("")).all(axis=1))]

# Step 2 – Drop duplicate rows
gl.drop_duplicates(inplace=True)

# Step 3 – Parse dates
gl["Date"] = gl["Date"].apply(parse_date)
gl.dropna(subset=["Date"], inplace=True)           # drop rows with unparseable dates
gl["Date"] = gl["Date"].dt.strftime("%Y-%m-%d")    # standardise format

# Step 4 – Clean numeric columns
gl["Debit"]  = gl["Debit"].apply(clean_amount).fillna(0.0)
gl["Credit"] = gl["Credit"].apply(clean_amount).fillna(0.0)

# Step 5 – Normalise account codes
gl["Account_Code"] = gl["Account_Code"].apply(clean_account_code)
gl.dropna(subset=["Account_Code"], inplace=True)

# Step 6 – Clean text columns
gl["Account_Name"]   = gl["Account_Name"].str.strip().str.title()
gl["Description"]    = gl["Description"].str.strip().str.title()
gl["Department"]     = gl["Department"].str.strip().str.title()
gl["Notes"]          = gl["Notes"].str.strip().str.title().replace("", np.nan)
gl["Transaction_ID"] = gl["Transaction_ID"].str.strip().replace("", np.nan)

# Step 7 – Add derived column: Net (Credit − Debit) for easier analysis
gl["Net_Amount"] = gl["Credit"] - gl["Debit"]

# Step 8 – Reset index
gl.reset_index(drop=True, inplace=True)

gl.to_csv(os.path.join(CLEAN_DIR, "general_ledger_clean.csv"), index=False)
print(f"  ✓ {len(gl)} clean rows saved  →  data/clean/general_ledger_clean.csv")


# ══════════════════════════════════════════════════════════════════════════════
# 2.  Clean Accounts Receivable
# ══════════════════════════════════════════════════════════════════════════════

print("\nCleaning Accounts Receivable...")
ar = pd.read_csv(os.path.join(RAW_DIR, "accounts_receivable_raw.csv"), dtype=str)

# Step 1 – Drop blank rows
critical_ar = ["Invoice_Date", "Customer_Name", "Amount_Due"]
ar.dropna(how="all", inplace=True)
ar = ar[~(ar[critical_ar].apply(lambda r: r.str.strip().eq("")).all(axis=1))]

# Step 2 – Drop duplicates
ar.drop_duplicates(inplace=True)

# Step 3 – Parse dates
ar["Invoice_Date"] = ar["Invoice_Date"].apply(parse_date)
ar["Due_Date"]     = ar["Due_Date"].apply(parse_date)
ar.dropna(subset=["Invoice_Date"], inplace=True)
ar["Invoice_Date"] = ar["Invoice_Date"].dt.strftime("%Y-%m-%d")
ar["Due_Date"]     = ar["Due_Date"].dt.strftime("%Y-%m-%d")

# Step 4 – Clean numeric columns
ar["Amount_Due"]  = ar["Amount_Due"].apply(clean_amount)
ar["Amount_Paid"] = ar["Amount_Paid"].apply(clean_amount).fillna(0.0)
ar.dropna(subset=["Amount_Due"], inplace=True)

# Step 5 – Derive outstanding balance
ar["Balance_Outstanding"] = (ar["Amount_Due"] - ar["Amount_Paid"]).round(2)

# Step 6 – Normalise Status to title case
ar["Status"] = ar["Status"].str.strip().str.title()

# Step 7 – Clean text
ar["Customer_Name"]  = ar["Customer_Name"].str.strip().str.title()
ar["Invoice_Number"] = ar["Invoice_Number"].str.strip().replace("", np.nan)
ar["Notes"]          = ar["Notes"].str.strip().str.title().replace("", np.nan)

# Step 8 – Days outstanding (from invoice date to today)
ar["Invoice_Date_dt"]     = pd.to_datetime(ar["Invoice_Date"])
ar["Days_Outstanding"]    = (pd.Timestamp.today() - ar["Invoice_Date_dt"]).dt.days
ar.drop(columns=["Invoice_Date_dt"], inplace=True)

ar.reset_index(drop=True, inplace=True)

ar.to_csv(os.path.join(CLEAN_DIR, "accounts_receivable_clean.csv"), index=False)
print(f"  ✓ {len(ar)} clean rows saved  →  data/clean/accounts_receivable_clean.csv")

print("\nCleaning complete. Run 03_load_database.py next.")
