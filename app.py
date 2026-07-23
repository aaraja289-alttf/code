import streamlit as st
import pandas as pd
import time

# Page configuration for a wider layout
st.set_page_config(page_title="Live Deal Logs Dashboard", layout="wide")
st.title("⚡ Live Team Performance Dashboard")

# Sidebar for Auto-Refresh Settings
st.sidebar.header("⚙️ Settings")
refresh_rate = st.sidebar.slider("Auto-Refresh Interval (Seconds)", min_value=10, max_value=300, value=60)

# Connect to Supabase using Streamlit's native SQL connection
conn = st.connection("postgresql", type="sql")

# ----------------------------------------------------
# 1. QUERY: TODAY'S TOTAL POSTS PER EMPLOYEE
# ----------------------------------------------------
# Note: Removed the "- 1" so it shows TODAY'S live data instead of yesterday's
query_totals = """
SELECT 
    employee_name,
    SUM(links_converted) AS total_links_posted
FROM 
    deal_logs
WHERE 
    (created_at AT TIME ZONE 'Asia/Karachi')::date = (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Karachi')::date
GROUP BY 
    employee_name
ORDER BY 
    total_links_posted DESC;
"""

# ----------------------------------------------------
# 2. QUERY: HOUR-BY-HOUR BREAKDOWN
# ----------------------------------------------------
query_hourly = """
SELECT 
    EXTRACT(HOUR FROM created_at AT TIME ZONE 'Asia/Karachi') AS hour_of_day,
    employee_name,
    SUM(links_converted) AS links_posted
FROM 
    deal_logs
WHERE 
    (created_at AT TIME ZONE 'Asia/Karachi')::date = (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Karachi')::date
GROUP BY 
    hour_of_day, employee_name
ORDER BY 
    hour_of_day ASC;
"""

# Fetch data directly from Supabase (ttl=0 ensures it doesn't cache and always fetches fresh data)
df_totals = conn.query(query_totals, ttl=0)
df_hourly = conn.query(query_hourly, ttl=0)

# ----------------------------------------------------
# DASHBOARD UI
# ----------------------------------------------------
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📊 Today's Total Output")
    if not df_totals.empty:
        st.dataframe(
            df_totals, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "employee_name": "Employee Name",
                "total_links_posted": st.column_config.NumberColumn("Total Links", format="%d")
            }
        )
    else:
        st.info("No logs found for today yet.")

with col2:
    st.subheader("📈 Hour-by-Hour Performance")
    if not df_hourly.empty:
        # Pivot the table so hours are on the X-axis and employees are separate lines/bars
        pivot_df = df_hourly.pivot(index='hour_of_day', columns='employee_name', values='links_posted').fillna(0)
        st.bar_chart(pivot_df, use_container_width=True)
    else:
        st.info("No hourly data available yet.")

# Show last updated time for confirmation
st.sidebar.markdown("---")
st.sidebar.text(f"Last updated: {pd.Timestamp.now('Asia/Karachi').strftime('%I:%M:%S %p')}")

# ----------------------------------------------------
# AUTO-REFRESH TRIGGER
# ----------------------------------------------------
time.sleep(refresh_rate)
st.rerun()
