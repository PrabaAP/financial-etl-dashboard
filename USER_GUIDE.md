# User Guide — Financial ETL Executive Dashboard

**No coding required. Works with QuickBooks, Sage, Xero, Tally, or any CSV export.**

---

## Quick Start (3 steps)

1. Open the dashboard: [Live Link](https://financial-etl-dashboard-jqswq7afq4twh76mfgzsbm.streamlit.app)
2. Choose **Demo Data** to explore instantly, or **Upload My Data** to use your own files
3. If uploading: map your columns → pick your account codes → click **Process**

That's it. No installation, no scripts, no technical knowledge needed.

---

## Option A — Demo Mode

Click **📊 Demo Data** in the sidebar. The dashboard loads instantly with a full year of sample data for a fictional accounting firm (Northgate Advisory Partners, FY 2024).

Use this to:
- Show the dashboard to a client or colleague before using real data
- Understand what each chart represents before uploading your own files
- Share the live URL on LinkedIn or a portfolio

---

## Option B — Upload Your Own Data

### What files do you need?

| File | What it is | Where to get it |
|------|-----------|----------------|
| **General Ledger CSV** *(required)* | All transactions for the period | QuickBooks: Reports → Accountant → General Ledger · Sage: Nominal Ledger export · Xero: General Ledger Detail · Excel: save as CSV |
| **Accounts Receivable CSV** *(optional)* | Outstanding invoices | QuickBooks: Reports → Customers → A/R Aging Detail · Sage: Aged Debtors · Xero: Aged Receivables |

Any CSV export works — the dashboard adapts to your column names.

---

### Step 1 — Upload

Drag your CSV files into the two uploaders in the sidebar, or click to browse. The dashboard immediately reads the column headers and shows you how many rows were found.

---

### Step 2 — Map Your Columns

The dashboard auto-detects which of your columns matches each required field. For example, if your file has a column called `Txn Date`, it will automatically suggest mapping it to **Date**.

You will see a dropdown for each field:

**General Ledger fields:**

| Field | What it means | Examples of column names |
|-------|--------------|--------------------------|
| Date * | Transaction date | Date, Txn Date, Posting Date, Entry Date |
| Account Code * | Unique code for each account | Account No, Acct Code, GL Code, Nominal Code |
| Debit * | Money going out / charges | Debit, Dr, Dr Amount, Paid Out |
| Credit * | Money coming in / receipts | Credit, Cr, Cr Amount, Paid In |
| Account Name | Description of the account | Account Name, Acct Title, Nominal Name |
| Department | Cost centre or division | Department, Branch, Division, Cost Centre |

**Accounts Receivable fields:**

| Field | What it means | Examples of column names |
|-------|--------------|--------------------------|
| Invoice Date * | Date the invoice was issued | Invoice Date, Inv Date, Issue Date |
| Customer Name * | Name of the client / debtor | Customer, Client, Debtor, Party Name |
| Amount Due * | Total invoice value | Amount Due, Invoice Value, Total, Gross |
| Amount Paid | How much has been received | Amount Paid, Received, Payment |
| Status | Open / Paid / Overdue / Partial | Status, Payment Status, Stage |

Fields marked * are required. All others are optional — if your file doesn't have them, leave the dropdown on **"— not in my file —"** and the dashboard will handle it gracefully.

If the auto-detection is wrong, just change the dropdown. It takes 10 seconds.

---

### Step 3 — Set Account Categories

After mapping, the dashboard reads all the unique account codes from your General Ledger and displays them as a list. You tick which ones are:

- **Revenue accounts** — money that comes into the business (sales, fees, income, retainers)
- **Expense accounts** — money that goes out (salaries, rent, subscriptions, marketing)

Everything else (assets, liabilities, equity) is automatically ignored — you don't need to categorise it.

**Example — QuickBooks US (standard chart of accounts):**
Revenue: 4000, 4010, 4020 | Expenses: 5000, 6000, 6100, 6200

**Example — Sage UK:**
Revenue: 4000, 4001, 4002 | Expenses: 7001, 7002, 7003, 7004, 8000

**Example — Xero:**
Revenue: 200, 260 | Expenses: 300, 310, 400, 404, 420, 425, 429, 431, 441, 445, 461, 469

This is how the dashboard works with **any** accounting system in **any** region — you're always in control of which accounts mean what.

---

### Step 4 — Process

Click **▶ Process & View Dashboard**. The cleaning, calculations, and charts all run in 2–3 seconds.

---

## Understanding the Dashboard

### KPI Cards (top row)

| Card | What it shows | Why it matters |
|------|--------------|---------------|
| 💰 Total Revenue | Sum of all credits in your revenue accounts | Top-line income for the period |
| 💸 Total Expenses | Sum of all debits in your expense accounts | Total cost of running the business |
| 📈 Net Cash Flow | Revenue minus all transactions (net position) | Shows if the business is cash-positive overall; the % change is vs the most recent prior month |
| 🔴 Outstanding AR | Total balance owed by customers still open | How much money hasn't been collected yet |

---

### Chart 1 — Monthly Revenue

A bar chart of revenue by month. Shows which months were strong and which were weak — something most small business owners never see because they only get annual totals.

---

### Chart 2 — Month-over-Month Revenue Variance

Green bars = growth vs the previous month. Red bars = decline. The number on each bar shows the exact dollar difference.

This is an early warning system — three consecutive red bars is a trend, not a blip.

---

### Chart 3 — Net Cash Flow + 3-Month Rolling Average

Two lines on the same chart:
- **Blue line** — actual net cash flow each month (can be volatile)
- **Orange dashed line** — the 3-month rolling average (smoothed trend)

The rolling average filters out one-off spikes so you can see the real direction of the business. The dotted red line at zero shows the break-even point.

---

### Chart 4 — AR Aging Buckets

Outstanding invoices grouped by how overdue they are:
- **0–30 days** (green) — normal payment cycle, no action needed
- **31–60 days** (amber) — follow up recommended
- **61–90 days** (orange) — overdue, chase required
- **90+ days** (red) — at risk of becoming bad debt

Longer bars mean more money sitting uncollected for longer.

---

### Chart 5 — Monthly Expense Breakdown

A stacked bar chart showing which expense categories (salaries, rent, software, etc.) make up costs each month. Shows if one category is growing unexpectedly.

---

### Chart 6 — Top Customers by Outstanding Balance

A ranked table of clients who owe money, from highest to lowest. This is a collections priority list — whoever is at the top needs to be called first.

---

## Compatible Accounting Systems

| System | GL Export | AR Export |
|--------|----------|-----------|
| QuickBooks Online | Reports → Accountant → General Ledger | Reports → Customers → A/R Aging Detail |
| QuickBooks Desktop | Reports → Accountant & Taxes → General Ledger | Reports → Customers & Receivables → A/R Aging Detail |
| Sage 50 | Reports → Nominal Ledger → Detailed | Reports → Customers → Aged Debtors |
| Sage Business Cloud | Reporting → Nominal Activity | Reporting → Aged Debtors |
| Xero | Accounting → Reports → General Ledger | Accounting → Reports → Aged Receivables |
| Tally ERP | Display → Account Books → Ledger | Display → Statement of Accounts → Outstandings |
| Excel / Manual | Export the worksheet as CSV | Export the invoice tracker as CSV |

---

## Troubleshooting

**"No revenue data found"** — Go back to the sidebar and check that you selected at least one Revenue account in Step 3.

**Dates look wrong after upload** — The dashboard tries to parse all common date formats automatically. If dates are still wrong, check that your date column doesn't contain mixed text and numbers.

**Charts show $0 or very small numbers** — Your Debit/Credit amounts may include currency symbols or commas (e.g. `$1,500.00`). The dashboard handles this automatically, but if amounts are text strings like `"1500 USD"`, the parsing may miss them. Try cleaning the amount column in Excel first (format as Number, no currency symbol).

**AR chart is empty** — The AR Aging chart only shows invoices with Status = Open, Overdue, or Partial. If all your invoices are marked Paid, the chart will be empty — which is actually good news.

---

## About This Project

Built by **Arun Prabakar Vadaseri Rajendran** as Portfolio Project 1.
[LinkedIn](https://linkedin.com/in/arun-prabakar-vadaseri-rajendran) · [GitHub Repo](https://github.com/PrabaAP/financial-etl-dashboard) · [Live Dashboard](https://financial-etl-dashboard-jqswq7afq4twh76mfgzsbm.streamlit.app)
