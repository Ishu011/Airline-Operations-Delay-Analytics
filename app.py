
# ✈️ Airline Operations & Delay Analytics Dashboard

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
@st.cache_data(ttl=3600)  # Cache data for 1 hour
def load_and_process_data():
    try:
        # Load datasets
        flight_df = pd.read_csv("clean_flight_data.csv")
        pnr_df = pd.read_csv("clean_pnr.csv")
        bag_df = pd.read_csv("clean_bag.csv")
        remark_df = pd.read_csv("clean_remark.csv")
        airport_df = pd.read_csv("clean_airport.csv")

        # Merge datasets
        merged_df = pd.merge(flight_df, pnr_df, on=["company_id", "flight_number", "scheduled_departure_date_local"], how="left")
        merged_df = pd.merge(merged_df, bag_df, on=["company_id", "flight_number", "scheduled_departure_date_local"], how="left")
        merged_df = merged_df.drop_duplicates()

        # Convert datetime columns
        datetime_cols = [
            "scheduled_departure_datetime_local",
            "actual_departure_datetime_local",
            "scheduled_arrival_datetime_local",
            "actual_arrival_datetime_local"
        ]
        for col in datetime_cols:
            if col in merged_df.columns:
                merged_df[col] = pd.to_datetime(merged_df[col], errors="coerce", utc=True)

        # Calculate delays
        merged_df["departure_delay_mins"] = (
            (merged_df["actual_departure_datetime_local"] - merged_df["scheduled_departure_datetime_local"])
            .dt.total_seconds() / 60
        ).fillna(0)
        merged_df["arrival_delay_mins"] = (
            (merged_df["actual_arrival_datetime_local"] - merged_df["scheduled_arrival_datetime_local"])
            .dt.total_seconds() / 60
        ).fillna(0)

        # Handle flight difficulty
        difficulty_cols = [c for c in merged_df.columns if 'difficulty' in c.lower() or 'score' in c.lower()]
        if difficulty_cols:
            merged_df.rename(columns={difficulty_cols[0]: 'flight_difficulty_score'}, inplace=True)
            st.info(f" Detected difficulty column: `{difficulty_cols[0]}` `flight_difficulty_score`")
        else:
            merged_df['flight_difficulty_score'] = np.random.randint(1, 100, merged_df.shape[0])
            st.warning("⚠️ No difficulty column detected.")

        return flight_df, pnr_df, bag_df, remark_df, airport_df, merged_df

    except FileNotFoundError as e:
        st.error(f" Error: Missing file - {e}. Please upload all required CSV files.")
        return None, None, None, None, None, None
    except Exception as e:
        st.error(f" Unexpected error loading data: {e}")
        return None, None, None, None, None, None

flight_df, pnr_df, bag_df, remark_df, airport_df, df = load_and_process_data()

# -----------------------------------------------
# 3️⃣ Sidebar Filters
# -----------------------------------------------
st.sidebar.header(" Filters")

# Carrier filter
if df is not None and "carrier" in df.columns:
    carriers = ["All"] + sorted(df["carrier"].dropna().unique().tolist())
    selected_carrier = st.sidebar.selectbox("Carrier", carriers, index=0)
    if selected_carrier != "All":
        df = df[df["carrier"] == selected_carrier]

# Date range filter
if df is not None and "scheduled_departure_date_local" in df.columns:
    dates = pd.to_datetime(df["scheduled_departure_date_local"]).dt.date
    min_date, max_date = dates.min(), dates.max()
    date_range = st.sidebar.date_input("Date Range", [min_date, max_date])
    if len(date_range) == 2:
        mask = (pd.to_datetime(df["scheduled_departure_date_local"]).dt.date >= date_range[0]) & \
               (pd.to_datetime(df["scheduled_departure_date_local"]).dt.date <= date_range[1])
        df = df[mask]

if df is not None:
    st.sidebar.write(f"📊 Total Flights: {len(df)}")
else:
    st.sidebar.write("📊 Total Flights: N/A")

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
    col2.metric("🛬 Avg Arrival Delay (min)", f"{avg_arr_delay:.1f}" if not np.isnan(avg_arr_delay) else "N/A")
    col3.metric("⏱ Avg Ground Time (min)", f"{avg_ground_time:.1f}" if not np.isnan(avg_ground_time) else "N/A")
    col4.metric("✅ On-Time Flights (%)", f"{on_time_pct:.1f}%" if not np.isnan(on_time_pct) else "N/A")
else:
    st.warning("⚠️ No data available to display KPIs.")

st.markdown("---")

# -----------------------------------------------
# 5️⃣ Visual Analytics Tabs
# -----------------------------------------------
if df is not None:
    tab1, tab2, tab3, tab4 = st.tabs(["Delay Analysis", "Ground Operations", "Route Patterns", "Flight Difficulty"])

    # --- TAB 1: Delay Analysis ---
    with tab1:
        st.subheader("📊 Delay Distribution")
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
            color="carrier", points="all"
        )
        st.plotly_chart(fig3, use_container_width=True)

        avg_ground = df.groupby("scheduled_departure_station_code")["actual_ground_time_minutes"].mean().reset_index()
        fig4 = px.line(
            avg_ground, x="scheduled_departure_station_code", y="actual_ground_time_minutes",
            title="Average Ground Time per Departure Station",
            markers=True
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
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig5, use_container_width=True)

    # --- TAB 4: Flight Difficulty ---
    with tab4:
        st.subheader(" Flight Difficulty Analysis")
        fig6 = px.histogram(
            df, x="flight_difficulty_score", nbins=30,
            title="Flight Difficulty Distribution",
            color_discrete_sequence=["#EF553B"],
            labels={"flight_difficulty_score": "Difficulty Score"}
        )
        st.plotly_chart(fig6, use_container_width=True)

        avg_difficulty = df.groupby("carrier")["flight_difficulty_score"].mean().reset_index()
        fig7 = px.bar(
            avg_difficulty, x="carrier", y="flight_difficulty_score",
            title="Average Difficulty by Carrier", color="carrier",
            color_discrete_sequence=["#1f77b4", "#ff7f0e"]
        )
        st.plotly_chart(fig7, use_container_width=True)
else:
    st.warning(" No data available to display visualizations.")

# -----------------------------------------------
# 6️⃣ Footer
# -----------------------------------------------
st.markdown("""
---
 *Developed by ISHU , Parul || TEAM_NAME : Code2Data * | Flight Analytics for Hackathon 2025  
 Powered by Streamlit, Plotly, and Pandas | ©05-10-2025}
""")