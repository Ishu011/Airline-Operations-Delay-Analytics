# ===============================================
# ✈️ Airline Operations & Delay Analytics Dashboard
# ===============================================

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime

# -----------------------------------------------
# 1️⃣ Page Configuration
# -----------------------------------------------
st.set_page_config(
    page_title="Flight Operations Analytics Dashboard",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("✈️ Airline Operations & Delay Analytics Dashboard")
st.markdown("### Real-Time Insights from Flight, PNR, Bag, and Airport Data")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST")

# -----------------------------------------------
# 2️⃣ Data Loading and Processing
# -----------------------------------------------
@st.cache_data(ttl=600)
def load_and_process_data():
    try:
        flight_df = pd.read_csv("clean_flight_data.csv")
        if len(flight_df) > 10000:
            flight_df = flight_df.sample(n=10000, random_state=42).reset_index(drop=True)
        
        pnr_df = pd.read_csv("clean_pnr.csv")
        if len(pnr_df) > 10000:
            pnr_df = pnr_df.sample(n=10000, random_state=42).reset_index(drop=True)
        
        bag_df = pd.read_csv("clean_bag.csv")
        if len(bag_df) > 10000:
            bag_df = bag_df.sample(n=10000, random_state=42).reset_index(drop=True)
        
        remark_df = pd.read_csv("clean_remark.csv")
        airport_df = pd.read_csv("clean_airport.csv")

        with st.spinner("Merging datasets..."):
            merged_df = pd.merge(flight_df, pnr_df, on=["company_id", "flight_number", "scheduled_departure_date_local"], how="left")
            merged_df = pd.merge(merged_df, bag_df, on=["company_id", "flight_number", "scheduled_departure_date_local"], how="left")
            merged_df = merged_df.drop_duplicates()

        datetime_cols = [
            "scheduled_departure_datetime_local",
            "actual_departure_datetime_local",
            "scheduled_arrival_datetime_local",
            "actual_arrival_datetime_local"
        ]
        for col in datetime_cols:
            if col in merged_df.columns:
                merged_df[col] = pd.to_datetime(merged_df[col], errors="coerce", utc=True)

        merged_df["departure_delay_mins"] = (
            (merged_df["actual_departure_datetime_local"] - merged_df["scheduled_departure_datetime_local"])
            .dt.total_seconds() / 60
        ).fillna(0)
        merged_df["arrival_delay_mins"] = (
            (merged_df["actual_arrival_datetime_local"] - merged_df["scheduled_arrival_datetime_local"])
            .dt.total_seconds() / 60
        ).fillna(0)

        difficulty_cols = [c for c in merged_df.columns if 'difficulty' in c.lower() or 'score' in c.lower()]
        if difficulty_cols:
            merged_df.rename(columns={difficulty_cols[0]: 'flight_difficulty_score'}, inplace=True)
            st.info(f"Detected difficulty column: `{difficulty_cols[0]}` renamed to `flight_difficulty_score`")
        else:
            merged_df['flight_difficulty_score'] = np.random.randint(1, 100, merged_df.shape[0])
            st.warning("No difficulty column detected. Using random demo values.")

        return flight_df, pnr_df, bag_df, remark_df, airport_df, merged_df

    except FileNotFoundError as e:
        st.error(f"Error: Missing file - {e}. Please ensure all CSV files are uploaded.")
        return None, None, None, None, None, pd.DataFrame()
    except Exception as e:
        st.error(f"Unexpected error loading data: {e}")
        return None, None, None, None, None, pd.DataFrame()

with st.spinner("Loading data..."):
    flight_df, pnr_df, bag_df, remark_df, airport_df, df = load_and_process_data()

# -----------------------------------------------
# 3️⃣ Sidebar Filters with Session State
# -----------------------------------------------
st.sidebar.header("Filters")

if "filter_state" not in st.session_state:
    st.session_state.filter_state = {"carrier": "All", "date_range": None}

if df is not None and "carrier" in df.columns:
    carriers = ["All"] + sorted(df["carrier"].dropna().unique().tolist())
    selected_carrier = st.sidebar.selectbox("Carrier", carriers, index=carriers.index(st.session_state.filter_state["carrier"]))
    if selected_carrier != st.session_state.filter_state["carrier"]:
        st.session_state.filter_state["carrier"] = selected_carrier
        if selected_carrier != "All":
            df = df[df["carrier"] == selected_carrier]

if df is not None and "scheduled_departure_date_local" in df.columns:
    dates = pd.to_datetime(df["scheduled_departure_date_local"]).dt.date
    min_date, max_date = dates.min(), dates.max()
    date_range = st.sidebar.date_input("Date Range", value=(min_date, max_date) if st.session_state.filter_state["date_range"] is None else st.session_state.filter_state["date_range"], min_value=min_date, max_value=max_date)
    if len(date_range) == 2 and date_range != st.session_state.filter_state["date_range"]:
        st.session_state.filter_state["date_range"] = date_range
        mask = (pd.to_datetime(df["scheduled_departure_date_local"]).dt.date >= date_range[0]) & \
               (pd.to_datetime(df["scheduled_departure_date_local"]).dt.date <= date_range[1])
        df = df[mask]

if df is not None:
    st.sidebar.write(f"Total Flights: {len(df)}")
else:
    st.sidebar.write("Total Flights: N/A")

if st.sidebar.button("Clear Cache & Refresh"):
    st.cache_data.clear()
    st.rerun()

# -----------------------------------------------
# 4️⃣ KPI Metrics
# -----------------------------------------------
if df is not None:
    col1, col2, col3, col4 = st.columns(4)
    
    avg_dep_delay = df["departure_delay_mins"].mean()
    avg_arr_delay = df["arrival_delay_mins"].mean()
    avg_ground_time = df["actual_ground_time_minutes"].mean()
    on_time_pct = (df["departure_delay_mins"] <= 15).mean() * 100

    col1.metric("✈️ Avg Departure Delay (min)", f"{avg_dep_delay:.1f}" if not np.isnan(avg_dep_delay) else "N/A")
    col2.metric("Avg Arrival Delay (min)", f"{avg_arr_delay:.1f}" if not np.isnan(avg_arr_delay) else "N/A")
    col3.metric("🧳 Avg Ground Time (min)", f"{avg_ground_time:.1f}" if not np.isnan(avg_ground_time) else "N/A")
    col4.metric("On-Time Flights (%)", f"{on_time_pct:.1f}%" if not np.isnan(on_time_pct) else "N/A")
else:
    st.warning("No data available to display KPIs.")

st.markdown("---")

# -----------------------------------------------
# 5️⃣ Visual Analytics Tabs
# -----------------------------------------------
if df is not None:
    tab1, tab2, tab3, tab4 = st.tabs(["Delay Analysis", "Ground Operations", "Route Patterns", "Flight Difficulty"])

    # --- TAB 1: Delay Analysis ---
    with tab1:
        st.subheader("Delay Distribution")
        fig1 = px.histogram(
            df, x="departure_delay_mins", nbins=40,
            title="Departure Delay Distribution",
            color_discrete_sequence=["#636EFA"],
            labels={"departure_delay_mins": "Delay (minutes)"}
        )
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.scatter(
            df, x="departure_delay_mins", y="arrival_delay_mins",
            color="carrier", title="Departure vs Arrival Delay",
            labels={"departure_delay_mins": "Departure Delay (min)", "arrival_delay_mins": "Arrival Delay (min)"}
        )
        st.plotly_chart(fig2, use_container_width=True)

    # --- TAB 2: Ground Operations ---
    with tab2:
        st.subheader("🧳 Ground Time Performance")
        fig3 = px.box(
            df, x="carrier", y="actual_ground_time_minutes",
            title="Ground Time Distribution by Carrier",
            color="carrier", points="all",
            notched=True
        )
        st.plotly_chart(fig3, use_container_width=True)

        avg_ground = df.groupby("scheduled_departure_station_code")["actual_ground_time_minutes"].mean().reset_index()
        fig4 = px.line(
            avg_ground, x="scheduled_departure_station_code", y="actual_ground_time_minutes",
            title="Average Ground Time per Departure Station",
            markers=True,
            line_shape="spline"
        )
        st.plotly_chart(fig4, use_container_width=True)

    # --- TAB 3: Route Patterns ---
    with tab3:
        st.subheader("🌍 Route Performance Analysis")
        top_routes = (
            df.groupby(["scheduled_departure_station_code", "scheduled_arrival_station_code"])
            .agg({"departure_delay_mins": "mean", "flight_number": "count"})
            .reset_index()
            .rename(columns={"flight_number": "num_flights"})
            .sort_values("num_flights", ascending=False)
            .head(15)
        )
        fig5 = px.bar(
            top_routes, x="num_flights", y="scheduled_departure_station_code",
            color="departure_delay_mins", orientation="h",
            title="Top 15 Busiest Routes by Delay",
            color_continuous_scale="Viridis",
            hover_data=["departure_delay_mins"]
        )
        st.plotly_chart(fig5, use_container_width=True)

    # --- TAB 4: Flight Difficulty ---
    with tab4:
        st.subheader("Flight Difficulty Analysis")
        fig6 = px.histogram(
            df, x="flight_difficulty_score", nbins=30,
            title="Flight Difficulty Distribution",
            color_discrete_sequence=["#EF553B"],
            labels={"flight_difficulty_score": "Difficulty Score"},
            marginal="box"
        )
        st.plotly_chart(fig6, use_container_width=True)

        avg_difficulty = df.groupby("carrier")["flight_difficulty_score"].mean().reset_index()
        fig7 = px.bar(
            avg_difficulty, x="carrier", y="flight_difficulty_score",
            title="Average Difficulty by Carrier", color="carrier",
            color_discrete_sequence=["#1f77b4", "#ff7f0e"],
            text=avg_difficulty["flight_difficulty_score"].round(1),
            text_auto=True
        )
        st.plotly_chart(fig7, use_container_width=True)
else:
    st.warning("No data available to display visualizations.")

# -----------------------------------------------
# 6️⃣ Footer
# -----------------------------------------------
st.markdown(f"""
---
Developed by ISHU & Parul | Team Name: Code2Data | Flight Analytics for Hackathon 2025  
Powered by Streamlit, Plotly, and Pandas | © {datetime.now().year}
""")
