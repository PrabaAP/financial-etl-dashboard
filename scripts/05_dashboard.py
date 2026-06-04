"""
Script 05: Executive Financial Dashboard — Polished Version
=============================================================
Three major upgrades over v1:

  1. FILE UPLOAD  — drag-and-drop your own GL + AR CSV exports.
                    No command line, no scripts, no repo access needed.

  2. COLUMN MAPPING — auto-detects your column names and lets you
                    correct them inside the dashboard if needed.

  3. ACCOUNT CATEGORIES — shows every unique account code found in
                    your data; you tick which are Revenue and which
                    are Expenses. Works for any chart of accounts
                    (QuickBooks UK, Sage, Xero, Tally, custom).

DEMO MODE: loads the pre-built Northgate Advisory Partners sample
           data instantly — no upload needed.

Run:  streamlit run scripts/05_dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import re

# ── Theme-safe chart defaults (transparent = inherits Streamlit dark/light) ──
CHART_BG   = "rgba(0,0,0,0)"          # transparent — adapts to dark & light mode
GRID_COLOR = "rgba(128,128,128,0.15)" # subtle gridlines in both modes
AXIS_STYLE = dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Financial ETL Dashboard",
    page_icon="📊",
    layout="wide",
)

# ── Paths for demo data ───────────────────────────────────────────────────────
BASE  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(BASE, "data", "clean")

# ══════════════════════════════════════════════════════════════════════════════
# CLEANING HELPERS  (embedded — no external scripts needed)
# ══════════════════════════════════════════════════════════════════════════════

def _parse_date(val):
    if pd.isna(val) or str(val).strip() == "":
        return pd.NaT
    try:
        return pd.to_datetime(str(val).strip(), dayfirst=False)
    except Exception:
        return pd.NaT

def _clean_amount(val):
    if pd.isna(val) or str(val).strip() in ("", "0"):
        return np.nan
    cleaned = re.sub(r"[\$,£€\s]", "", str(val).strip())
    try:
        return float(cleaned)
    except ValueError:
        return np.nan

def clean_gl(df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
    """Clean a raw General Ledger DataFrame using the user's column mapping."""
    out = pd.DataFrame()
    out["date"]         = df[col_map["date"]].apply(_parse_date)
    out["account_code"] = df[col_map["account_code"]].astype(str).str.strip().str.upper()
    out["debit"]        = df[col_map["debit"]].apply(_clean_amount).fillna(0.0)
    out["credit"]       = df[col_map["credit"]].apply(_clean_amount).fillna(0.0)
    out["net_amount"]   = out["credit"] - out["debit"]

    # Optional columns — gracefully fall back if not provided
    if col_map.get("account_name"):
        out["account_name"] = df[col_map["account_name"]].astype(str).str.strip().str.title()
    else:
        out["account_name"] = out["account_code"]

    if col_map.get("department"):
        out["department"] = df[col_map["department"]].astype(str).str.strip().str.title()
    else:
        out["department"] = "General"

    out.dropna(subset=["date"], inplace=True)
    out.drop_duplicates(inplace=True)
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    return out.reset_index(drop=True)

def clean_ar(df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
    """Clean a raw Accounts Receivable DataFrame using the user's column mapping."""
    out = pd.DataFrame()
    out["invoice_date"]  = df[col_map["invoice_date"]].apply(_parse_date)
    out["customer_name"] = df[col_map["customer_name"]].astype(str).str.strip().str.title()
    out["amount_due"]    = df[col_map["amount_due"]].apply(_clean_amount)
    out["amount_paid"]   = df[col_map["amount_paid"]].apply(_clean_amount).fillna(0.0) if col_map.get("amount_paid") else 0.0
    out["status"]        = df[col_map["status"]].astype(str).str.strip().str.title() if col_map.get("status") else "Open"

    out.dropna(subset=["invoice_date", "amount_due"], inplace=True)
    out.drop_duplicates(inplace=True)
    out["balance_outstanding"] = (out["amount_due"] - out["amount_paid"]).round(2)
    out["days_outstanding"]    = (pd.Timestamp.today() - out["invoice_date"]).dt.days
    out["invoice_date"]        = out["invoice_date"].dt.strftime("%Y-%m-%d")
    return out.reset_index(drop=True)

def empty_ar():
    """Return an empty AR DataFrame with the expected columns."""
    return pd.DataFrame(columns=[
        "invoice_date", "customer_name", "amount_due", "amount_paid",
        "balance_outstanding", "days_outstanding", "status"
    ])

# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS  (pure pandas — works on any cleaned DataFrame)
# ══════════════════════════════════════════════════════════════════════════════

def monthly_revenue(gl, rev_codes):
    sub = gl[gl["account_code"].isin(rev_codes) & (gl["credit"] > 0)].copy()
    sub["month"] = pd.to_datetime(sub["date"]).dt.to_period("M").astype(str)
    return sub.groupby("month").agg(
        total_revenue=("credit", "sum"),
        transaction_count=("credit", "count"),
    ).reset_index().sort_values("month")

def mom_variance(rev_df):
    df = rev_df.copy().sort_values("month")
    df["prev"] = df["total_revenue"].shift(1)
    df["mom_variance"] = (df["total_revenue"] - df["prev"]).round(2)
    df["mom_variance_pct"] = (df["mom_variance"] / df["prev"] * 100).round(1)
    return df

def rolling_cashflow(gl):
    cf = gl.copy()
    cf["month"] = pd.to_datetime(cf["date"]).dt.to_period("M").astype(str)
    cf = cf.groupby("month")["net_amount"].sum().reset_index()
    cf.columns = ["month", "net_cash_flow"]
    cf = cf.sort_values("month")
    cf["rolling_3m_avg"] = cf["net_cash_flow"].rolling(3).mean().round(2)
    return cf

def ar_aging(ar):
    open_ar = ar[ar["status"].isin(["Open", "Overdue", "Partial"])].copy()
    if open_ar.empty:
        return pd.DataFrame(columns=["aging_bucket", "invoice_count", "total_outstanding"])
    def _bucket(d):
        if d <= 30:   return "0-30 Days"
        elif d <= 60: return "31-60 Days"
        elif d <= 90: return "61-90 Days"
        else:          return "90+ Days"
    open_ar["aging_bucket"] = open_ar["days_outstanding"].apply(_bucket)
    order = {"0-30 Days": 0, "31-60 Days": 1, "61-90 Days": 2, "90+ Days": 3}
    result = open_ar.groupby("aging_bucket").agg(
        invoice_count=("balance_outstanding", "count"),
        total_outstanding=("balance_outstanding", "sum"),
    ).reset_index()
    result["_order"] = result["aging_bucket"].map(order)
    return result.sort_values("_order").drop(columns="_order")

def expense_breakdown(gl, exp_codes):
    sub = gl[gl["account_code"].isin(exp_codes) & (gl["debit"] > 0)].copy()
    sub["month"] = pd.to_datetime(sub["date"]).dt.to_period("M").astype(str)
    return sub.groupby(["month", "account_name"]).agg(
        total_expense=("debit", "sum")
    ).reset_index().sort_values("month")

def top_customers(ar):
    open_ar = ar[ar["status"].isin(["Open", "Overdue", "Partial"])].copy()
    if open_ar.empty:
        return pd.DataFrame(columns=["customer_name", "open_invoices", "total_outstanding"])
    return (
        open_ar.groupby("customer_name")
        .agg(open_invoices=("balance_outstanding", "count"),
             total_outstanding=("balance_outstanding", "sum"))
        .reset_index()
        .sort_values("total_outstanding", ascending=False)
        .head(10)
    )

# ══════════════════════════════════════════════════════════════════════════════
# AUTO-DETECT COLUMN MAPPING
# ══════════════════════════════════════════════════════════════════════════════

GL_KW = {
    "date":         ["date", "txn", "trans", "posting", "entry", "period"],
    "account_code": ["code", "acct", "account", "gl", "ledger", "no.", "num"],
    "account_name": ["account name", "acc name", "account description"],
    "debit":        ["debit", " dr", "dr.", "charge", "paid out", "amount dr"],
    "credit":       ["credit", " cr", "cr.", "receipt", "paid in", "amount cr"],
    "department":   ["dept", "department", "division", "cost centre", "branch"],
}

AR_KW = {
    "invoice_date":  ["invoice date", "inv date", "issue date", "date"],
    "customer_name": ["customer", "client", "debtor", "name", "party"],
    "amount_due":    ["amount due", "invoice amount", "total", "gross", "amount"],
    "amount_paid":   ["amount paid", "paid", "payment", "received", "settled"],
    "due_date":      ["due date", "payment due", "maturity"],
    "status":        ["status", "state", "stage", "payment status"],
}

def auto_detect(columns, kw_map):
    cols_l = {c: c.lower() for c in columns}
    result = {}
    for field, kws in kw_map.items():
        for col, col_l in cols_l.items():
            if any(kw in col_l for kw in kws):
                result[field] = col
                break
    return result

# ══════════════════════════════════════════════════════════════════════════════
# DEMO DATA
# ══════════════════════════════════════════════════════════════════════════════

DEMO_REV_CODES = ["4000", "4100"]
DEMO_EXP_CODES = ["5000", "5100", "5200", "5300", "5400"]

@st.cache_data
def load_demo():
    gl = pd.read_csv(os.path.join(CLEAN, "general_ledger_clean.csv"))
    ar = pd.read_csv(os.path.join(CLEAN, "accounts_receivable_clean.csv"))
    gl.columns = gl.columns.str.lower()
    ar.columns = ar.columns.str.lower()
    gl["account_code"] = gl["account_code"].astype(str).str.strip()
    ar["days_outstanding"] = (
        pd.Timestamp.today() - pd.to_datetime(ar["invoice_date"])
    ).dt.days
    return gl, ar

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.title("⚙️ Dashboard Setup")
    st.divider()

    mode = st.radio(
        "Data source",
        ["📊 Demo Data", "📁 Upload My Data"],
        index=0,
        help="Demo loads the sample Northgate dataset instantly. Upload uses your own CSV exports.",
    )
    st.divider()

    # ── DEMO MODE ────────────────────────────────────────────────────────────
    if mode == "📊 Demo Data":
        gl, ar = load_demo()
        rev_codes = DEMO_REV_CODES
        exp_codes = DEMO_EXP_CODES
        data_ready = True
        st.success("Sample data loaded (FY 2024)")
        st.caption(
            "Simulates a QuickBooks/Sage export for a 12-person "
            "accounting firm. Switch to **Upload My Data** to use your own."
        )

    # ── UPLOAD MODE ──────────────────────────────────────────────────────────
    else:
        data_ready = False
        gl, ar = None, empty_ar()
        rev_codes, exp_codes = [], []

        # ── Step 1: Upload ────────────────────────────────────────────────
        st.markdown("**Step 1 — Upload your CSV exports**")
        gl_file = st.file_uploader(
            "General Ledger CSV  *(required)*",
            type=["csv"],
            help="Export from QuickBooks: Reports → Accountant → General Ledger. "
                 "Sage: Nominal Ledger export. Xero: General Ledger Detail report.",
        )
        ar_file = st.file_uploader(
            "Accounts Receivable CSV  *(optional)*",
            type=["csv"],
            help="Export the aged debtors / outstanding invoices report from your system.",
        )

        if gl_file is None:
            st.info("Upload your GL CSV above to continue setup.")

        else:
            gl_raw = pd.read_csv(gl_file, dtype=str)
            ar_raw = pd.read_csv(ar_file, dtype=str) if ar_file else None
            st.success(f"GL: {len(gl_raw)} rows · {len(gl_raw.columns)} columns")
            if ar_raw is not None:
                st.success(f"AR: {len(ar_raw)} rows · {len(ar_raw.columns)} columns")

            # ── Step 2: Column Mapping ────────────────────────────────────
            st.divider()
            st.markdown("**Step 2 — Map your column names**")
            st.caption(
                "We've auto-detected the most likely matches. "
                "Adjust any that are wrong."
            )

            gl_cols   = gl_raw.columns.tolist()
            auto_gl   = auto_detect(gl_cols, GL_KW)
            NONE      = "— not in my file —"

            def _idx(lst, key, fallback=0):
                return lst.index(key) if key in lst else fallback

            with st.expander("📋 General Ledger columns", expanded=True):
                gl_map = {}
                gl_map["date"] = st.selectbox(
                    "Date *", gl_cols,
                    index=_idx(gl_cols, auto_gl.get("date", gl_cols[0])),
                    key="gl_date",
                )
                gl_map["account_code"] = st.selectbox(
                    "Account Code *", gl_cols,
                    index=_idx(gl_cols, auto_gl.get("account_code", gl_cols[0])),
                    key="gl_code",
                )
                gl_map["debit"] = st.selectbox(
                    "Debit *", gl_cols,
                    index=_idx(gl_cols, auto_gl.get("debit", gl_cols[0])),
                    key="gl_debit",
                )
                gl_map["credit"] = st.selectbox(
                    "Credit *", gl_cols,
                    index=_idx(gl_cols, auto_gl.get("credit", gl_cols[0])),
                    key="gl_credit",
                )
                opts = [NONE] + gl_cols
                an = st.selectbox("Account Name", opts, index=_idx(opts, auto_gl.get("account_name", NONE)), key="gl_an")
                dp = st.selectbox("Department",   opts, index=_idx(opts, auto_gl.get("department", NONE)),   key="gl_dp")
                if an != NONE: gl_map["account_name"] = an
                if dp != NONE: gl_map["department"]   = dp

            ar_map = None
            if ar_raw is not None:
                ar_cols  = ar_raw.columns.tolist()
                auto_ar  = auto_detect(ar_cols, AR_KW)
                ar_opts  = [NONE] + ar_cols
                with st.expander("📋 Accounts Receivable columns", expanded=True):
                    ar_map = {}
                    ar_map["invoice_date"]  = st.selectbox("Invoice Date *",   ar_cols, index=_idx(ar_cols, auto_ar.get("invoice_date",  ar_cols[0])), key="ar_date")
                    ar_map["customer_name"] = st.selectbox("Customer Name *",  ar_cols, index=_idx(ar_cols, auto_ar.get("customer_name", ar_cols[0])), key="ar_cust")
                    ar_map["amount_due"]    = st.selectbox("Amount Due *",      ar_cols, index=_idx(ar_cols, auto_ar.get("amount_due",    ar_cols[0])), key="ar_amt")
                    for fld, lbl, key in [
                        ("amount_paid", "Amount Paid",  "ar_paid"),
                        ("status",      "Status",       "ar_status"),
                    ]:
                        sel = st.selectbox(lbl, ar_opts, index=_idx(ar_opts, auto_ar.get(fld, NONE)), key=key)
                        if sel != NONE: ar_map[fld] = sel

            # ── Step 3: Account Categories ────────────────────────────────
            st.divider()
            st.markdown("**Step 3 — Categorise your accounts**")
            st.caption(
                "Tick which account codes represent money coming IN "
                "(Revenue) and money going OUT (Expenses). "
                "Leave everything else unticked — it won't affect the charts."
            )

            # Build code → label map
            raw_codes = gl_raw[gl_map["account_code"]].astype(str).str.strip().str.upper().dropna().unique().tolist()
            raw_codes.sort()

            if gl_map.get("account_name"):
                pair_df = gl_raw[[gl_map["account_code"], gl_map["account_name"]]].drop_duplicates()
                pair_df.columns = ["code", "name"]
                pair_df["code"]  = pair_df["code"].astype(str).str.strip().str.upper()
                pair_df["name"]  = pair_df["name"].astype(str).str.strip().str.title()
                code_to_label = dict(zip(pair_df["code"], pair_df["code"] + " — " + pair_df["name"]))
            else:
                code_to_label = {c: c for c in raw_codes}

            display = [code_to_label.get(c, c) for c in raw_codes]
            label_to_code = {v: k for k, v in code_to_label.items()}

            with st.expander("💰 Account categories", expanded=True):
                rev_sel = st.multiselect(
                    "Revenue accounts  (income / fees / sales)",
                    options=display,
                    help="All credit entries in these accounts count as revenue.",
                )
                exp_sel = st.multiselect(
                    "Expense accounts  (costs / salaries / overheads)",
                    options=display,
                    help="All debit entries in these accounts count as expenses.",
                )
                rev_codes = [label_to_code[l] for l in rev_sel]
                exp_codes = [label_to_code[l] for l in exp_sel]

            # ── Process button ────────────────────────────────────────────
            st.divider()
            process = st.button(
                "▶ Process & View Dashboard",
                type="primary",
                use_container_width=True,
                disabled=(not rev_codes),
                help="Select at least one Revenue account first.",
            )

            if process:
                st.session_state["_processed"] = {
                    "gl_raw": gl_raw, "ar_raw": ar_raw,
                    "gl_map": gl_map, "ar_map": ar_map,
                    "rev_codes": rev_codes, "exp_codes": exp_codes,
                }

            if st.session_state.get("_processed") and mode == "📁 Upload My Data":
                p = st.session_state["_processed"]
                try:
                    gl       = clean_gl(p["gl_raw"], p["gl_map"])
                    ar       = clean_ar(p["ar_raw"], p["ar_map"]) if p["ar_raw"] is not None and p["ar_map"] else empty_ar()
                    rev_codes = p["rev_codes"]
                    exp_codes = p["exp_codes"]
                    data_ready = True
                    st.success(f"✓ {len(gl)} GL rows · {len(ar)} AR rows ready")
                except Exception as e:
                    st.error(f"Processing failed: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN AREA
# ══════════════════════════════════════════════════════════════════════════════

# ── Welcome screen (no data yet) ─────────────────────────────────────────────
if not data_ready:
    st.title("📊 Financial ETL Executive Dashboard")
    st.markdown(
        "Upload your General Ledger and Accounts Receivable CSV exports using the "
        "**sidebar on the left**, map your column names, categorise your accounts, "
        "and hit **Process** — the full dashboard builds in seconds.\n\n"
        "Or switch to **Demo Data** to explore the sample dataset instantly."
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**📂 Step 1**\nUpload GL + AR CSVs from QuickBooks, Sage, Xero, or Excel")
    with col2:
        st.info("**🗂 Step 2**\nMap your column names — auto-detected, fully editable")
    with col3:
        st.info("**✅ Step 3**\nTick your Revenue and Expense accounts, click Process")
    st.stop()

# ── Compute analytics ─────────────────────────────────────────────────────────
rev_df  = monthly_revenue(gl, rev_codes)
mom_df  = mom_variance(rev_df)
cf_df   = rolling_cashflow(gl)
aging_df = ar_aging(ar)
exp_df  = expense_breakdown(gl, exp_codes)
cust_df = top_customers(ar)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📊 Northgate Advisory Partners" if mode == "📊 Demo Data" else "📊 Financial Dashboard")
st.subheader("Executive Financial Dashboard — FY 2024" if mode == "📊 Demo Data" else "Executive Financial Dashboard")

if mode == "📊 Demo Data":
    st.caption("Pipeline: Raw QuickBooks/Sage export → Python ETL (pandas) → Analytics SQL → Streamlit  |  AI: Claude + Google Gemini")
else:
    data_range = f"{gl['date'].min()}  →  {gl['date'].max()}"
    st.caption(f"Your data: {len(gl):,} GL transactions · {len(ar):,} AR invoices · Date range: {data_range}")

st.divider()

# ── KPI CARDS ────────────────────────────────────────────────────────────────
total_rev  = rev_df["total_revenue"].sum()
total_exp  = gl[gl["account_code"].isin(exp_codes) & (gl["debit"] > 0)]["debit"].sum() if exp_codes else 0
net_cf     = cf_df["net_cash_flow"].sum()
outstanding = ar[ar["status"].isin(["Open", "Overdue", "Partial"])]["balance_outstanding"].sum() if not ar.empty else 0

last_pct   = mom_df["mom_variance_pct"].dropna().iloc[-1] if not mom_df["mom_variance_pct"].dropna().empty else 0

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("💰 Total Revenue", f"${total_rev:,.0f}")
with k2:
    st.metric("💸 Total Expenses", f"${total_exp:,.0f}" if exp_codes else "N/A — select expense accounts")
with k3:
    st.metric("📈 Net Cash Flow", f"${net_cf:,.0f}", delta=f"{last_pct:+.1f}% vs prior month")
with k4:
    flag = "Needs follow-up" if outstanding > 10000 else "On track"
    st.metric("🔴 Outstanding AR", f"${outstanding:,.0f}" if not ar.empty else "No AR data", delta=flag if not ar.empty else None, delta_color="inverse")

st.divider()

# ── ROW 1: Monthly Revenue  |  MoM Variance ──────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Monthly Revenue")
    if rev_df.empty:
        st.warning("No revenue data found. Check your Revenue account selection.")
    else:
        fig = px.bar(rev_df, x="month", y="total_revenue",
                     labels={"month": "Month", "total_revenue": "Revenue"},
                     color_discrete_sequence=["#2563EB"], text_auto=".2s")
        fig.update_layout(plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
                          xaxis={**AXIS_STYLE, "tickangle": -45}, yaxis=AXIS_STYLE)
        fig.update_traces(textfont_size=12)
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Month-over-Month Revenue Variance")
    clean_mom = mom_df.dropna(subset=["mom_variance"])
    if clean_mom.empty:
        st.info("Need at least 2 months of data to show variance.")
    else:
        colors = ["#16A34A" if v >= 0 else "#DC2626" for v in clean_mom["mom_variance"]]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=clean_mom["month"], y=clean_mom["mom_variance"],
            marker_color=colors, name="MoM Variance",
            text=[f"{v:+,.0f}" for v in clean_mom["mom_variance"]],
            textposition="outside",
            textfont=dict(size=12),
        ))
        fig.update_layout(
            plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
            xaxis={**AXIS_STYLE, "tickangle": -45, "title": "Month"},
            yaxis={**AXIS_STYLE, "title": "Variance"},
        )
        st.plotly_chart(fig, use_container_width=True)

# ── ROW 2: Cash Flow  |  AR Aging ────────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("Net Cash Flow vs 3-Month Rolling Average")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cf_df["month"], y=cf_df["net_cash_flow"],
                             mode="lines+markers", name="Net Cash Flow",
                             line=dict(color="#2563EB", width=2), marker=dict(size=6)))
    fig.add_trace(go.Scatter(x=cf_df["month"], y=cf_df["rolling_3m_avg"],
                             mode="lines", name="3-Month Rolling Avg",
                             line=dict(color="#F59E0B", width=2, dash="dash")))
    fig.add_hline(y=0, line_dash="dot", line_color="red", opacity=0.4)
    fig.update_layout(
        plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
        xaxis={**AXIS_STYLE, "tickangle": -45},
        yaxis=AXIS_STYLE,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

with col4:
    st.subheader("AR Aging Buckets")
    if ar.empty or aging_df.empty:
        st.info("No open AR data available. Upload an Accounts Receivable CSV to see aging.")
    else:
        color_map = {"0-30 Days": "#16A34A", "31-60 Days": "#F59E0B",
                     "61-90 Days": "#EA580C", "90+ Days": "#DC2626"}
        fig = px.bar(aging_df, x="total_outstanding", y="aging_bucket",
                     orientation="h",
                     labels={"total_outstanding": "Outstanding", "aging_bucket": "Aging"},
                     color="aging_bucket", color_discrete_map=color_map, text_auto=".2s")
        fig.update_layout(plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
                          showlegend=False, xaxis=AXIS_STYLE, yaxis=AXIS_STYLE)
        fig.update_traces(textfont_size=12)
        st.plotly_chart(fig, use_container_width=True)

# ── ROW 3: Expense Breakdown  |  Top Customers ───────────────────────────────
col5, col6 = st.columns(2)

with col5:
    st.subheader("Monthly Expense Breakdown by Category")
    if exp_df.empty:
        st.info("No expense data. Select Expense accounts in the sidebar to see this chart.")
    else:
        fig = px.bar(exp_df, x="month", y="total_expense", color="account_name",
                     labels={"month": "Month", "total_expense": "Expense", "account_name": "Category"},
                     barmode="stack")
        fig.update_layout(
            plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
            xaxis={**AXIS_STYLE, "tickangle": -45}, yaxis=AXIS_STYLE,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)

with col6:
    st.subheader("Top Customers — Outstanding AR")
    if cust_df.empty:
        st.info("No open AR data available.")
    else:
        st.dataframe(
            cust_df.rename(columns={
                "customer_name":    "Customer",
                "open_invoices":    "Open Invoices",
                "total_outstanding": "Outstanding",
            }).style.format({"Outstanding": "${:,.2f}"}),
            use_container_width=True, hide_index=True,
        )

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Portfolio project — **Arun Prabakar Vadaseri Rajendran** · "
    "MABA, Carleton University · "
    "linkedin.com/in/arun-prabakar-vadaseri-rajendran"
)
