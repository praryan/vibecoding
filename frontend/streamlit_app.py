import os
from datetime import date, timedelta

import plotly.express as px
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="AWS Cost Intelligence Dashboard", layout="wide")
st.title("AWS Cost Intelligence Dashboard (MVP)")

with st.sidebar:
    st.subheader("API Settings")
    backend_url = st.text_input("Backend URL", BACKEND_URL)
    st.caption("Endpoints used: /health, /cost/summary, /cost/forecast")

    st.subheader("Filters")
    end = st.date_input("End date", value=date.today())
    start = st.date_input("Start date", value=date.today() - timedelta(days=30))
    group_by = st.selectbox("Group by", ["service", "account", "region"], index=0)
    limit = st.slider("Top N", min_value=5, max_value=100, value=20, step=5)

# Health check
try:
    r = requests.get(f"{backend_url}/health", timeout=5)
    r.raise_for_status()
    st.success("Backend reachable")
except Exception as e:
    st.error(f"Backend not reachable: {e}")

col1, col2 = st.columns(2)

# Cost summary chart
with col1:
    st.subheader("Cost by group")
    try:
        params = {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "group_by": group_by,
            "limit": limit,
        }
        resp = requests.get(f"{backend_url}/cost/summary", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json().get("results", [])
        if data:
            fig = px.bar(data, x="group", y="cost", title=f"Cost by {group_by}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data returned")
    except Exception as e:
        st.error(f"Failed to load cost summary: {e}")

# Forecast chart
with col2:
    st.subheader("Forecast (baseline)")
    try:
        params = {"horizon_days": 14, "history_days": 60}
        resp = requests.get(f"{backend_url}/cost/forecast", params=params, timeout=60)
        resp.raise_for_status()
        payload = resp.json()
        history = payload.get("history", [])
        forecast = payload.get("forecast", [])

        if history:
            fig_hist = px.line(history, x="date", y="cost", title="Historical daily cost")
            st.plotly_chart(fig_hist, use_container_width=True)
        if forecast:
            fig_fc = px.line(forecast, x="date", y="cost", title="Forecast (naive)")
            st.plotly_chart(fig_fc, use_container_width=True)
        if not history and not forecast:
            st.info("No forecast data returned")
    except Exception as e:
        st.error(f"Failed to load forecast: {e}")
