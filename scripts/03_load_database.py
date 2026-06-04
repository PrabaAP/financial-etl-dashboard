"""
Script 03: Build the SQLite Database
======================================
Purpose : Load the clean CSVs into a local SQLite database so the
          analytics queries in script 04 can run against proper SQL.

Why SQLite?
-----------
  • Zero setup — no server, no installation, just a file.
  • Portable — the .db file travels with the project.
  • Realistic — same SQL syntax used in PostgreSQL / MySQL / BigQuery.

AI Credit: Schema design and INSERT logic written with Claude.

Output
------
  database/financial.db
"""

import sqlite3
import pandas as pd
import os

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE, "database", "financial.db")
GL_CSV   = os.path.join(BASE, "data", "clean", "general_ledger_clean.csv")
AR_CSV   = os.path.join(BASE, "data", "clean", "accounts_receivable_clean.csv")

os.makedirs(os.path.join(BASE, "database"), exist_ok=True)

# Remove old database if re-running (keeps things idempotent)
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("  Removed old database.")

# ── Connect ────────────────────────────────────────────────────────────────────
conn   = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ══════════════════════════════════════════════════════════════════════════════
# 1.  Create tables
# ══════════════════════════════════════════════════════════════════════════════

cursor.execute("""
CREATE TABLE IF NOT EXISTS general_ledger (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT,           -- YYYY-MM-DD
    transaction_id  TEXT,
    account_code    TEXT,
    account_name    TEXT,
    description     TEXT,
    debit           REAL DEFAULT 0,
    credit          REAL DEFAULT 0,
    net_amount      REAL,           -- credit - debit (positive = income)
    department      TEXT,
    notes           TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS accounts_receivable (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_date        TEXT,       -- YYYY-MM-DD
    invoice_number      TEXT,
    customer_name       TEXT,
    amount_due          REAL,
    amount_paid         REAL DEFAULT 0,
    balance_outstanding REAL,
    due_date            TEXT,
    status              TEXT,       -- Open | Paid | Overdue | Partial
    days_outstanding    INTEGER,
    notes               TEXT
)
""")

conn.commit()
print("✓ Tables created: general_ledger, accounts_receivable")

# ══════════════════════════════════════════════════════════════════════════════
# 2.  Load data from clean CSVs
# ══════════════════════════════════════════════════════════════════════════════

# General Ledger
gl = pd.read_csv(GL_CSV)
gl_cols = [
    "Date", "Transaction_ID", "Account_Code", "Account_Name",
    "Description", "Debit", "Credit", "Net_Amount", "Department", "Notes"
]
gl_insert = gl[gl_cols].rename(columns={c: c.lower() for c in gl_cols})
gl_insert.to_sql("general_ledger", conn, if_exists="append", index=False)
print(f"  ✓ Loaded {len(gl_insert)} rows into general_ledger")

# Accounts Receivable
ar = pd.read_csv(AR_CSV)
ar_cols = [
    "Invoice_Date", "Invoice_Number", "Customer_Name",
    "Amount_Due", "Amount_Paid", "Balance_Outstanding",
    "Due_Date", "Status", "Days_Outstanding", "Notes"
]
ar_insert = ar[ar_cols].rename(columns={c: c.lower() for c in ar_cols})
ar_insert.to_sql("accounts_receivable", conn, if_exists="append", index=False)
print(f"  ✓ Loaded {len(ar_insert)} rows into accounts_receivable")

# ══════════════════════════════════════════════════════════════════════════════
# 3.  Quick verification
# ══════════════════════════════════════════════════════════════════════════════

print("\n── Verification queries ──────────────────────────────")

row_counts = cursor.execute("""
    SELECT 'general_ledger' AS tbl, COUNT(*) AS rows FROM general_ledger
    UNION ALL
    SELECT 'accounts_receivable', COUNT(*) FROM accounts_receivable
""").fetchall()
for tbl, count in row_counts:
    print(f"  {tbl}: {count} rows")

date_range = cursor.execute("""
    SELECT MIN(date), MAX(date) FROM general_ledger
""").fetchone()
print(f"  GL date range: {date_range[0]}  →  {date_range[1]}")

conn.close()
print(f"\n✓ Database saved  →  database/financial.db")
print("Run 04_analytics.py next.")
