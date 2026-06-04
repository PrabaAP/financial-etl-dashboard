"""
Script 04: Run Analytics Queries
==================================
Purpose : Run SQL queries against the SQLite database to produce the
          analytical outputs that power the executive dashboard.

Queries produced
----------------
  1. Monthly Revenue Summary
  2. Month-over-Month (MoM) Revenue Variance
  3. 3-Month Rolling Average — Cash Flow (Net Amount)
  4. Monthly Expense Breakdown by Account
  5. AR Aging Buckets (0-30, 31-60, 61-90, 90+ days)
  6. Top Customers by Outstanding Balance

AI Credit: SQL query logic and window function patterns written with Claude.

Output
------
  Prints tables to terminal.
  Saves results as CSVs to data/clean/ for the dashboard to consume.
"""

import sqlite3
import pandas as pd
import os

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH    = os.path.join(BASE, "database", "financial.db")
CLEAN_DIR  = os.path.join(BASE, "data", "clean")

conn = sqlite3.connect(DB_PATH)

print("=" * 60)
print("  NORTHGATE ADVISORY PARTNERS — EXECUTIVE ANALYTICS")
print("=" * 60)


# ══════════════════════════════════════════════════════════════════════════════
# 1.  Monthly Revenue Summary
# ══════════════════════════════════════════════════════════════════════════════
#
# Revenue rows have account codes starting with '4' (4000, 4100).
# We sum credits for those accounts, grouped by month.

monthly_revenue = pd.read_sql_query("""
    SELECT
        STRFTIME('%Y-%m', date)     AS month,
        ROUND(SUM(credit), 2)       AS total_revenue,
        COUNT(*)                    AS transaction_count
    FROM general_ledger
    WHERE account_code IN ('4000', '4100')          -- Revenue accounts
      AND credit > 0
    GROUP BY month
    ORDER BY month
""", conn)

print("\n── 1. Monthly Revenue ──────────────────────────────────")
print(monthly_revenue.to_string(index=False))
monthly_revenue.to_csv(os.path.join(CLEAN_DIR, "monthly_revenue.csv"), index=False)


# ══════════════════════════════════════════════════════════════════════════════
# 2.  Month-over-Month Revenue Variance
# ══════════════════════════════════════════════════════════════════════════════
#
# LAG() is a window function that looks at the previous row's value.
# Variance = current month revenue − previous month revenue.

mom_variance = pd.read_sql_query("""
    WITH monthly AS (
        SELECT
            STRFTIME('%Y-%m', date)     AS month,
            ROUND(SUM(credit), 2)       AS total_revenue
        FROM general_ledger
        WHERE account_code IN ('4000', '4100')
          AND credit > 0
        GROUP BY month
    )
    SELECT
        month,
        total_revenue,
        LAG(total_revenue) OVER (ORDER BY month)   AS prev_month_revenue,
        ROUND(
            total_revenue - LAG(total_revenue) OVER (ORDER BY month),
            2
        )                                           AS mom_variance,
        ROUND(
            CASE
                WHEN LAG(total_revenue) OVER (ORDER BY month) = 0 THEN NULL
                ELSE (
                    (total_revenue - LAG(total_revenue) OVER (ORDER BY month))
                    / LAG(total_revenue) OVER (ORDER BY month)
                ) * 100
            END,
            1
        )                                           AS mom_variance_pct
    FROM monthly
    ORDER BY month
""", conn)

print("\n── 2. Month-over-Month Revenue Variance ───────────────")
print(mom_variance.to_string(index=False))
mom_variance.to_csv(os.path.join(CLEAN_DIR, "mom_variance.csv"), index=False)


# ══════════════════════════════════════════════════════════════════════════════
# 3.  3-Month Rolling Average — Net Cash Flow
# ══════════════════════════════════════════════════════════════════════════════
#
# net_amount = credit - debit (positive = net inflow).
# Rolling average uses AVG() with a window of the current row
# plus the 2 preceding rows.

rolling_avg = pd.read_sql_query("""
    WITH monthly_cf AS (
        SELECT
            STRFTIME('%Y-%m', date)         AS month,
            ROUND(SUM(net_amount), 2)        AS net_cash_flow
        FROM general_ledger
        GROUP BY month
        ORDER BY month
    )
    SELECT
        month,
        net_cash_flow,
        ROUND(
            AVG(net_cash_flow) OVER (
                ORDER BY month
                ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
            ),
            2
        )                                   AS rolling_3m_avg
    FROM monthly_cf
    ORDER BY month
""", conn)

print("\n── 3. 3-Month Rolling Avg — Net Cash Flow ─────────────")
print(rolling_avg.to_string(index=False))
rolling_avg.to_csv(os.path.join(CLEAN_DIR, "rolling_cashflow.csv"), index=False)


# ══════════════════════════════════════════════════════════════════════════════
# 4.  Monthly Expense Breakdown by Account
# ══════════════════════════════════════════════════════════════════════════════

expense_breakdown = pd.read_sql_query("""
    SELECT
        STRFTIME('%Y-%m', date)     AS month,
        account_name,
        ROUND(SUM(debit), 2)        AS total_expense
    FROM general_ledger
    WHERE account_code IN ('5000','5100','5200','5300','5400')   -- Expense accounts
      AND debit > 0
    GROUP BY month, account_name
    ORDER BY month, total_expense DESC
""", conn)

print("\n── 4. Monthly Expense Breakdown ────────────────────────")
print(expense_breakdown.head(20).to_string(index=False))
expense_breakdown.to_csv(os.path.join(CLEAN_DIR, "expense_breakdown.csv"), index=False)


# ══════════════════════════════════════════════════════════════════════════════
# 5.  AR Aging Buckets
# ══════════════════════════════════════════════════════════════════════════════
#
# Standard aging: 0-30 days, 31-60, 61-90, 90+ days.
# Only for invoices that are still Open or Partial.

ar_aging = pd.read_sql_query("""
    SELECT
        CASE
            WHEN days_outstanding <= 30  THEN '0-30 Days'
            WHEN days_outstanding <= 60  THEN '31-60 Days'
            WHEN days_outstanding <= 90  THEN '61-90 Days'
            ELSE                              '90+ Days'
        END                                         AS aging_bucket,
        COUNT(*)                                    AS invoice_count,
        ROUND(SUM(balance_outstanding), 2)          AS total_outstanding
    FROM accounts_receivable
    WHERE status IN ('Open', 'Overdue', 'Partial')
    GROUP BY aging_bucket
    ORDER BY
        CASE aging_bucket
            WHEN '0-30 Days'  THEN 1
            WHEN '31-60 Days' THEN 2
            WHEN '61-90 Days' THEN 3
            ELSE                   4
        END
""", conn)

print("\n── 5. AR Aging Buckets ─────────────────────────────────")
print(ar_aging.to_string(index=False))
ar_aging.to_csv(os.path.join(CLEAN_DIR, "ar_aging.csv"), index=False)


# ══════════════════════════════════════════════════════════════════════════════
# 6.  Top Customers by Outstanding Balance
# ══════════════════════════════════════════════════════════════════════════════

top_customers = pd.read_sql_query("""
    SELECT
        customer_name,
        COUNT(*)                                AS open_invoices,
        ROUND(SUM(balance_outstanding), 2)      AS total_outstanding
    FROM accounts_receivable
    WHERE status IN ('Open', 'Overdue', 'Partial')
    GROUP BY customer_name
    ORDER BY total_outstanding DESC
    LIMIT 10
""", conn)

print("\n── 6. Top Customers by Outstanding Balance ─────────────")
print(top_customers.to_string(index=False))
top_customers.to_csv(os.path.join(CLEAN_DIR, "top_customers.csv"), index=False)


conn.close()
print("\n✓ All analytics complete. CSVs saved to data/clean/")
print("Run 05_dashboard.py next.")
