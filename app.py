import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import urllib.parse
import xml.etree.ElementTree as ET
import email.utils
from datetime import datetime
import html
import requests

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="TireIntel Pro",
    page_icon="🛞",
    layout="centered"
)

# --- 2. DATA CACHING & FETCHING ---
@st.cache_data(ttl=3600)
def get_market_trends():
    """Hardcoded industry forecast data (Free - no API needed)"""
    data = {
        "Year": [2022, 2023, 2024, 2025, 2026],
        "Market_Size_B": [16.2, 17.5, 19.3, 20.6, 21.8],
        "Avg_Price": [485, 510, 545, 580, 615]
    }
    return pd.DataFrame(data)

@st.cache_data(ttl=1800)
def fetch_news_safe(query):
    """Your 'Bulletproof' News Scraper Implementation"""
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-CA&gl=CA&ceid=CA:en"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if b'<rss' not in response.content:
            return None, "Blocked by provider (Captcha/Bot Detection)"
        
        root = ET.fromstring(response.content)
        articles = []
        for item in root.findall('./channel/item')[:8]:
            title = html.unescape(item.find('title').text)
            articles.append({
                'title': title.split(" - ")[0],
                'source': title.split(" - ")[1] if " - " in title else "Industry News",
                'link': item.find('link').text,
                'date': item.find('pubDate').text[:16]
            })
        return articles, None
    except Exception as e:
        return None, str(e)

# --- 3. UI COMPONENTS ---
st.title("🛞 TireIntel Pro")
st.caption(f"Market Intelligence Dashboard | Last Synced: {datetime.now().strftime('%H:%M')}")

tab1, tab2 = st.tabs(["📊 Market Trends", "📰 Industry News"])

with tab1:
    st.subheader("Long Haul Market: Volume vs Pricing")
    df = get_market_trends()
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Volume Bar
    fig.add_trace(go.Bar(x=df["Year"], y=df["Market_Size_B"], name="Market Size ($B)", marker_color='#1E88E5'), secondary_y=False)
    
    # Price Line
    fig.add_trace(go.Scatter(x=df["Year"], y=df["Avg_Price"], name="Avg Price ($)", line=dict(color='#FF4B4B', width=3), mode='lines+markers'), secondary_y=True)
    
    fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.1), margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)
    
    st.info("**2026 Forecast:** Market size expected to hit $21.8B as unit costs rise to ~$615 due to raw material and trade pressures.")

with tab2:
    query = st.text_input("Custom Market Search", '("tire" OR "tyre") AND ("market" OR "merger" OR "Michelin" OR "Bridgestone")')
    news, err = fetch_news_safe(query)
    
    if err:
        st.error(f"Connection Error: {err}")
    elif news:
        for art in news:
            with st.container(border=True):
                st.markdown(f"**[{art['title']}]({art['link']})**")
                st.caption(f"{art['date']} | {art['source']}")

if st.button("🔄 Refresh All Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()