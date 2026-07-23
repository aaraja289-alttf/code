import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import pytz

# Page configuration
st.set_page_config(page_title="Live Deal Logs Dashboard", layout="wide")
st.title("⚡ Team Performance Dashboard")

# Connect to Supabase
conn = st.connection("postgresql", type="sql")

# ----------------------------------------------------
# ⚙️ SIDEBAR: SETTINGS & FILTERS
# ----------------------------------------------------
st.sidebar.header("⚙️ Controls")

# 1. Date Filter (Last 30 Days)
# Get current date in PST to set default values accurately
pst_tz = pytz.timezone('America/Los_Angeles')
current_pst_time = datetime.now(pst_tz)
# If current time is before 4 AM, the "business day" is technically yesterday
if current_pst_time.hour < 4:
    default_business_date = (current_pst_time - timedelta(days=1)).date()
else:
    default_business_date = current_pst_time.date()

min_date = default_business_date - timedelta(days=30)

selected_date = st.sidebar.date_input(
    "📅 Select Shift Date (PST):",
    value=default_business_date,
    min_value=min_date,
    max_value=default_business_date
)

# Auto-Refresh interval
refresh_rate = st.sidebar.slider("Auto-Refresh Interval (Seconds)", min_value=10, max_value=300, value=60)

# ----------------------------------------------------
# 📊 QUERIES (PST Timezone + 4 AM Shift Logic)
# ----------------------------------------------------
target_date_str = str(selected_date)

# Total deals grouped by employee for the selected date
query_totals = f"""
SELECT 
    employee_name,
    SUM(links_converted) AS total_links_posted
FROM 
    deal_logs
WHERE 
    (created_at AT TIME ZONE 'America/Los_Angeles' - INTERVAL '4 hours')::date = '{target_date_str}'
GROUP BY 
    employee_name
ORDER BY 
    total_links_posted DESC;
"""

# Hourly breakdown for the chart
query_hourly = f"""
SELECT 
    EXTRACT(HOUR FROM created_at AT TIME ZONE 'America/Los_Angeles') AS hour_of_day,
    employee_name,
    SUM(links_converted) AS links_posted
FROM 
    deal_logs
WHERE 
    (created_at AT TIME ZONE 'America/Los_Angeles' - INTERVAL '4 hours')::date = '{target_date_str}'
GROUP BY 
    hour_of_day, employee_name
ORDER BY 
    hour_of_day ASC;
"""

# Fetch Dashboard Data
df_totals = conn.query(query_totals, ttl=0)
df_hourly = conn.query(query_hourly, ttl=0)

# ----------------------------------------------------
# 🖥️ DASHBOARD UI
# ----------------------------------------------------
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader(f"📊 Total Output ({selected_date})")
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
        st.info("No logs found for this date.")

with col2:
    st.subheader("📈 Hour-by-Hour Performance (PST)")
    if not df_hourly.empty:
        pivot_df = df_hourly.pivot(index='hour_of_day', columns='employee_name', values='links_posted').fillna(0)
        st.bar_chart(pivot_df, use_container_width=True)
    else:
        st.info("No hourly data available.")

st.markdown("---")

# ----------------------------------------------------
# 🕵️‍♂️ AUDIT TRAIL SECTION
# ----------------------------------------------------
st.subheader("📝 Employee Audit Trail")

# Create a list of employees who worked on this date for the dropdown
if not df_totals.empty:
    employee_list = df_totals['employee_name'].tolist()
    
    # Select employee to view their specific audit log
    selected_employee = st.selectbox("Select an employee to view their detailed log:", employee_list)
    
    # Query specific audit log for the selected employee
    query_audit = f"""
    SELECT 
        employee_name,
        links_converted,
        TO_CHAR(created_at AT TIME ZONE 'America/Los_Angeles', 'YYYY-MM-DD') AS audit_date,
        TO_CHAR(created_at AT TIME ZONE 'America/Los_Angeles', 'HH24:MI:SS') AS audit_time
    FROM 
        deal_logs
    WHERE 
        (created_at AT TIME ZONE 'America/Los_Angeles' - INTERVAL '4 hours')::date = '{target_date_str}'
        AND employee_name = '{selected_employee}'
    ORDER BY 
        created_at ASC;
    """
    
    df_audit = conn.query(query_audit, ttl=0)
    
    # Display the audit log exactly as Chachu requested
    if not df_audit.empty:
        with st.container():
            for index, row in df_audit.iterrows():
                # Format: Nabeel converted 10 deals at 05:12:09 (with date added)
                st.code(f"{row['employee_name']} converted {row['links_converted']} deals on {row['audit_date']} at {row['audit_time']}")
    else:
        st.write("No audit logs found for this employee on this date.")
else:
    st.write("Awaiting data to generate audit trails.")

# Footer timestamp
st.sidebar.markdown("---")
st.sidebar.text(f"Last updated: {datetime.now(pytz.timezone('Asia/Karachi')).strftime('%I:%M:%S %p PKT')}")

# Auto-refresh triggers only if looking at today's data to save resources
if selected_date == default_business_date:
    time.sleep(refresh_rate)
    st.rerun()
