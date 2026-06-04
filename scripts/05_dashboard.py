"""
Script 05: Executive Financial Dashboard
==========================================
Purpose : Interactive Streamlit dashboard that reads the analytics CSVs
          and displays an executive-ready financial summary.

How to run
----------
  streamlit run scripts/05_dashboard.py

How to share (free)
-------------------
  1. Push project to GitHub.
  2. Go to https://share.streamlit.io
  3. Connect your repo → select this file → Deploy.
  Your dashboard will have a public URL you can add to your portfolio/LinkedIn.

Visuals included
-----------------
  • KPI cards  : Total Revenue | Total Expenses | Net Cash Flow | Outstanding AR
  • Chart 1    : Monthly Revenue bar chart
  • Chart 2    : Month-over-Month Variance (+ rolling 3m avg overlay)
  • Chart 3    : Net Cash Flow vs 3-Month Rolling Average (line chart)
  • Chart 4    : AR Aging buckets (horizontal bar)
  • Chart 5    : Expense breakdown by category (stacked bar)
  • Table      : Top customers by outstanding balance

AI Credit: Dashboard layout and chart logic written with Claude.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# ── Page configuration ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Northgate Advisory Partners — Executive Dashboard",
    page_icon="📊",
    layout="wide",
)

# ── Paths ──────────────────────────────────────────────────────────────────────
# Works whether you run from the project root or from the scripts/ folder
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(BASE, "data", "clean")

# ── Load data ──────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    rev   = pd.read_csv(os.path.join(CLEAN, "monthly_revenue.csv"))
    mom   = pd.read_csv(os.path.join(CLEAN, "mom_variance.csv"))
    cf    = pd.read_csv(os.path.join(CLEAN, "rolling_cashflow.csv"))
    aging = pd.read_csv(os.path.join(CLEAN, "ar_aging.csv"))
    exp   = pd.read_csv(os.path.join(CLEAN, "expense_breakdown.csv"))
    cust  = pd.read_csv(os.path.join(CLEAN, "top_customers.csv"))
    ar    = pd.read_csv(os.path.join(CLEAN, "accounts_receivable_clean.csv"))
    gl    = pd.read_csv(os.path.join(CLEAN, "general_ledger_clean.csv"))
    # Normalize to lowercase — the cleaning script saves title-case columns
    ar.columns = ar.columns.str.lower()
    gl.columns = gl.columns.str.lower()
    return rev, mom, cf, aging, exp, cust, ar, gl

rev, mom, cf, aging, exp, cust, ar, gl = load_data()

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("📊 Northgate Advisory Partners")
st.subheader("Executive Financial Dashboard — FY 2024")
st.caption(
    "Pipeline: Raw QuickBooks/Sage export → Python ETL (pandas) → "
    "SQLite → Analytics SQL → Streamlit  |  AI: Claude + Google Gemini"
)
st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# KPI CARDS
# ══════════════════════════════════════════════════════════════════════════════

total_revenue  = rev["total_revenue"].sum()
total_expenses = gl[gl["debit"] > 0]["debit"].sum()
net_cash_flow  = cf["net_cash_flow"].sum()
outstanding_ar = ar[ar["status"].isin(["Open", "Overdue", "Partial"])]["balance_outstanding"].sum()

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.metric(
        label="💰 Total Revenue (FY24)",
        value=f"${total_revenue:,.0f}",
    )
with k2:
    st.metric(
        label="💸 Total Expenses (FY24)",
        value=f"${total_expenses:,.0f}",
    )
with k3:
    last_mom = mom["mom_variance_pct"].dropna().iloc[-1] if not mom["mom_variance_pct"].dropna().empty else 0
    st.metric(
        label="📈 Net Cash Flow (FY24)",
        value=f"${net_cash_flow:,.0f}",
        delta=f"{last_mom:+.1f}% vs prior month",
    )
with k4:
    st.metric(
        label="🔴 Outstanding AR",
        value=f"${outstanding_ar:,.0f}",
        delta="Needs follow-up" if outstanding_ar > 10000 else "On track",
        delta_color="inverse",
    )

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# ROW 1: Monthly Revenue  |  MoM Variance
# ══════════════════════════════════════════════════════════════════════════════

col1, col2 = st.columns(2)

with col1:
    st.subheader("Monthly Revenue")
    fig_rev = px.bar(
        rev,
        x="month",
        y="total_revenue",
        labels={"month": "Month", "total_revenue": "Revenue (CAD)"},
        color_discrete_sequence=["#2563EB"],
        text_auto=".2s",
    )
    fig_rev.update_layout(plot_bgcolor="white", xaxis_tickangle=-45)
    st.plotly_chart(fig_rev, use_container_width=True)

with col2:
    st.subheader("Month-over-Month Revenue Variance")
    mom_clean = mom.dropna(subset=["mom_variance"])
    colors    = ["#16A34A" if v >= 0 else "#DC2626" for v in mom_clean["mom_variance"]]
    fig_mom   = go.Figure()
    fig_mom.add_trace(go.Bar(
        x=mom_clean["month"],
        y=mom_clean["mom_variance"],
        marker_color=colors,
        name="MoM Variance",
        text=[f"{v:+,.0f}" for v in mom_clean["mom_variance"]],
        textposition="outside",
    ))
    fig_mom.update_layout(
        plot_bgcolor="white",
        xaxis_tickangle=-45,
        yaxis_title="Variance (CAD)",
        xaxis_title="Month",
    )
    st.plotly_chart(fig_mom, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# ROW 2: Cash Flow + Rolling Avg  |  AR Aging
# ══════════════════════════════════════════════════════════════════════════════

col3, col4 = st.columns(2)

with col3:
    st.subheader("Net Cash Flow vs 3-Month Rolling Average")
    fig_cf = go.Figure()
    fig_cf.add_trace(go.Scatter(
        x=cf["month"], y=cf["net_cash_flow"],
        mode="lines+markers",
        name="Net Cash Flow",
        line=dict(color="#2563EB", width=2),
        marker=dict(size=6),
    ))
    fig_cf.add_trace(go.Scatter(
        x=cf["month"], y=cf["rolling_3m_avg"],
        mode="lines",
        name="3-Month Rolling Avg",
        line=dict(color="#F59E0B", width=2, dash="dash"),
    ))
    fig_cf.add_hline(y=0, line_dash="dot", line_color="red", opacity=0.4)
    fig_cf.update_layout(
        plot_bgcolor="white",
        xaxis_tickangle=-45,
        yaxis_title="Amount (CAD)",
        xaxis_title="Month",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_cf, use_container_width=True)

with col4:
    st.subheader("AR Aging Buckets")
    if aging.empty:
        st.info("No open/overdue invoices found.")
    else:
        fig_aging = px.bar(
            aging,
            x="total_outstanding",
            y="aging_bucket",
            orientation="h",
            labels={"total_outstanding": "Outstanding (CAD)", "aging_bucket": "Aging"},
            color="aging_bucket",
            color_discrete_map={
                "0-30 Days": "#16A34A",
                "31-60 Days": "#F59E0B",
                "61-90 Days": "#EA580C",
                "90+ Days": "#DC2626",
            },
            text_auto=".2s",
        )
        fig_aging.update_layout(plot_bgcolor="white", showlegend=False)
        st.plotly_chart(fig_aging, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# ROW 3: Expense Breakdown  |  Top Customers
# ══════════════════════════════════════════════════════════════════════════════

col5, col6 = st.columns(2)

with col5:
    st.subheader("Monthly Expense Breakdown by Category")
    fig_exp = px.bar(
        exp,
        x="month",
        y="total_expense",
        color="account_name",
        labels={"month": "Month", "total_expense": "Expense (CAD)", "account_name": "Category"},
        barmode="stack",
    )
    fig_exp.update_layout(
        plot_bgcolor="white",
        xaxis_tickangle=-45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_exp, use_container_width=True)

with col6:
    st.subheader("Top Customers — Outstanding AR")
    st.dataframe(
        cust.rename(columns={
            "customer_name"    : "Customer",
            "open_invoices"    : "Open Invoices",
            "total_outstanding": "Outstanding (CAD)",
        }).style.format({"Outstanding (CAD)": "${:,.2f}"}),
        use_container_width=True,
        hide_index=True,
    )

st.divider()
st.caption(
    "Portfolio project by **Arun Prabakar Vadaseri Rajendran** — "
    "MABA, Carleton University  |  "
    "LinkedIn: linkedin.com/in/arun-prabakar-vadaseri-rajendran"
)
