import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import urllib.parse
import xml.etree.ElementTree as ET
import email.utils
from datetime import datetime, timedelta
import html
import requests
import numpy as np

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="TireIntel Pro: Market & Forecast",
    page_icon="🛞",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Mobile Optimization
st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; max-width: 900px; }
        .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINES ---

@st.cache_data(ttl=3600)
def get_combined_market_data():
    """Generates monthly historical data, 18-month forecast, and Michelin benchmarks."""
    # Timeline: 2024-01 to 2027-06 (18 months past Dec 2025)
    hist_months = pd.date_range(start="2024-01-01", end="2025-12-01", freq="MS")
    fore_months = pd.date_range(start="2026-01-01", periods=18, freq="MS")
    
    # Industry Seasonality (Q1 Dips, Q3/Q4 Peaks)
    seasonality = [0.88, 0.85, 0.92, 1.02, 1.08, 1.05, 1.10, 1.22, 1.28, 1.25, 1.18, 1.12]
    
    # Base Values
    base_size = 1.61 # Billion per month (~$19.3B / 12)
    base_price = 545
    
    # 1. Historical Data
    data_list = []
    for i, date in enumerate(hist_months):
        weight = seasonality[date.month - 1]
        growth = 1 + (0.004 * i) # Steady monthly growth
        data_list.append({
            "Date": date,
            "Market_Size_B": base_size * weight * growth,
            "Avg_Price": base_price * growth,
            "Status": "Historical",
            "Michelin_Ref": 0.501 if date.year == 2025 else np.nan # €6.02B/12 converted
        })
    
    # 2. Forecast Data (2026-2027)
    for i, date in enumerate(fore_months):
        weight = seasonality[date.month - 1]
        # 5.8% Annual Growth Trend
        trend = 1 + (0.058 / 12 * (i + 24)) 
        data_list.append({
            "Date": date,
            "Market_Size_B": base_size * weight * trend,
            "Avg_Price": base_price * trend,
            "Status": "Forecast",
            "Michelin_Ref": np.nan
        })
        
    return pd.DataFrame(data_list)

@st.cache_data(ttl=1800)
def fetch_news_safe(query):
    """Resilient News Scraper (Free/No Key)"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-CA&gl=CA&ceid=CA:en"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(response.content)
        articles = []
        for item in root.findall('./channel/item')[:6]:
            raw_title = html.unescape(item.find('title').text)
            articles.append({
                'title': raw_title.split(" - ")[0],
                'source': raw_title.split(" - ")[1] if " - " in raw_title else "News",
                'link': item.find('link').text,
                'date': item.find('pubDate').text[:16]
            })
        return articles, None
    except Exception as e:
        return None, str(e)

# --- 3. APP UI ---
st.title("🛞 TireIntel Pro")
st.caption(f"Last Intelligence Sync: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

tab1, tab2, tab3 = st.tabs(["📊 Market Forecast", "🏭 Competitor Watch", "📰 Live News"])

df = get_combined_market_data()

with tab1:
    st.subheader("18-Month Long-Haul Forecast")
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Historical Bars
    hist = df[df["Status"] == "Historical"]
    fig.add_trace(go.Bar(x=hist["Date"], y=hist["Market_Size_B"], name="Hist. Size ($B)", marker_color='#1E88E5', opacity=0.7), secondary_y=False)
    
    # Forecast Bars
    fore = df[df["Status"] == "Forecast"]
    fig.add_trace(go.Bar(x=fore["Date"], y=fore["Market_Size_B"], name="Fore. Size ($B)", marker_color='#90CAF9', opacity=0.4), secondary_y=False)
    
    # Pricing Line
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Avg_Price"], name="Avg Price ($)", line=dict(color='#FF4B4B', width=3)), secondary_y=True)
    
    fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.1), margin=dict(l=0, r=0, t=30, b=0), xaxis=dict(rangeslider=dict(visible=True)))
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Michelin Benchmark (RS2 Segment)")
    st.write("Based on Michelin's Feb 11, 2026 Annual Report:")
    
    c1, c2 = st.columns(2)
    c1.metric("Michelin RS2 Margin", "4.7%", "-4.3 pts")
    c2.metric("NA OE Truck Market", "-20%", "Historical Low")
    
    st.markdown("""
    **Strategic Takeaways:**
    * **OE Collapse:** Michelin's 20% volume drop in North American Class 8 OE confirms massive manufacturer de-stocking.
    * **Replacement Opportunity:** Michelin reported Replacement sales "rose slightly," showing fleets are retreading and repairing rather than buying new trucks.
    * **Cost Pressure:** US Tariffs impacted Michelin by **€230M** in 2025; expect aggressive pricing in 2026 to recover margins.
    """)

with tab3:
    news_q = '("tire" OR "tyre") AND ("merger" OR "acquisition" OR "Michelin" OR "Bridgestone" OR "Canada")'
    news, err = fetch_news_safe(news_q)
    if err: st.error(f"Feed Offline: {err}")
    elif news:
        for a in news:
            with st.container(border=True):
                st.markdown(f"**[{a['title']}]({a['link']})**")
                st.caption(f"{a['date']} | {a['source']}")

if st.button("🔄 Clear Cache & Refresh", use_container_width=True):
    st.cache_data.clear()
    st.rerun()