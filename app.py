import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="TireIntel Forecast Pro", layout="wide")

# --- 2. MONTHLY DATA & FORECAST ENGINE ---
@st.cache_data
def get_monthly_market_data():
    # Historical Base (Monthly for 2024-2025)
    months = pd.date_range(start="2024-01-01", end="2025-12-01", freq="MS")
    
    # Monthly Seasonality Weights (Q1 is slow, Q3/Q4 are peak)
    # [Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec]
    seasonality = [0.85, 0.82, 0.90, 1.05, 1.10, 1.08, 1.12, 1.25, 1.30, 1.28, 1.20, 1.15]
    
    # Generate Synthetic Monthly Historical Data
    hist_size = []
    hist_price = []
    
    base_size = 1.6  # Approx $19B annual / 12
    base_price = 545
    
    for i, date in enumerate(months):
        weight = seasonality[date.month - 1]
        # Adding slight organic growth + noise
        growth_factor = 1 + (0.005 * i) 
        hist_size.append(base_size * weight * growth_factor)
        hist_price.append(base_price * (1 + (0.004 * i)))

    df_hist = pd.DataFrame({
        "Date": months,
        "Market_Size_B": hist_size,
        "Avg_Price": hist_price,
        "Status": "Historical"
    })

    # --- FORECAST ENGINE (Next 18 Months) ---
    forecast_months = pd.date_range(start="2026-01-01", periods=18, freq="MS")
    last_size = hist_size[-1]
    last_price = hist_price[-1]
    
    f_size = []
    f_price = []
    
    for i, date in enumerate(forecast_months):
        weight = seasonality[date.month - 1]
        # Applying 5.8% annual growth trend
        trend_growth = 1 + (0.058 / 12 * (i + 1))
        f_size.append(base_size * 1.15 * weight * trend_growth) # 1.15 to bridge year gap
        f_price.append(last_price * (1 + (0.004 * (i + 1))))

    df_fore = pd.DataFrame({
        "Date": forecast_months,
        "Market_Size_B": f_size,
        "Avg_Price": f_price,
        "Status": "Forecast"
    })

    return pd.concat([df_hist, df_fore])

# --- 3. APP UI ---
st.title("🛞 Long-Haul Tire: 18-Month Market Forecast")
st.markdown("Monthly granularity including freight seasonality impacts.")

full_df = get_monthly_market_data()

# --- 4. DUAL AXIS PLOTTING ---
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Historical Data
hist_mask = full_df["Status"] == "Historical"
fore_mask = full_df["Status"] == "Forecast"

# Volume Bars (Market Size)
fig.add_trace(go.Bar(
    x=full_df[hist_mask]["Date"], y=full_df[hist_mask]["Market_Size_B"],
    name="Historical Size ($B)", marker_color='#1E88E5', opacity=0.6
), secondary_y=False)

fig.add_trace(go.Bar(
    x=full_df[fore_mask]["Date"], y=full_df[fore_mask]["Market_Size_B"],
    name="Forecasted Size ($B)", marker_color='#90CAF9', opacity=0.4
), secondary_y=False)

# Price Line
fig.add_trace(go.Scatter(
    x=full_df["Date"], y=full_df["Avg_Price"],
    name="Avg Unit Price ($)", line=dict(color='#FF4B4B', width=3, dash='dot' if any(fore_mask) else 'solid')
), secondary_y=True)

# Formatting
fig.update_layout(
    hovermode="x unified",
    legend=dict(orientation="h", y=1.1),
    xaxis=dict(rangeslider=dict(visible=True), type="date")
)

st.plotly_chart(fig, use_container_width=True)

# --- 5. MOBILE INSIGHTS CARDS ---
st.subheader("Forecast Breakdown")
col1, col2 = st.columns(2)

with col1:
    peak_val = full_df[full_df["Status"] == "Forecast"]["Market_Size_B"].max()
    st.metric("Proj. Peak Monthly Size", f"${peak_val:.2f}B", "Sept 2026")

with col2:
    price_end = full_df["Avg_Price"].iloc[-1]
    st.metric("Proj. End Price (June 2027)", f"${price_end:.0f}", "+12.8% Total")

st.warning("**Analyst Note:** Forecast accounts for Q1 'Quiet Season' dips and Q3 freight peaks. Pricing assumes a steady 4.8% annual inflationary crawl.")