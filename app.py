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

# Default timezone set to UK Time for new operations
uk_tz = pytz.timezone('Europe/London')
current_date = datetime.now(uk_tz).date()

selected_date = st.sidebar.date_input(
    "📅 Select Shift Date:",
    value=current_date,
    min_value=current_date - timedelta(days=30)
)

refresh_rate = st.sidebar.slider("Auto-Refresh Interval (Seconds)", min_value=10, max_value=300, value=60)

# ----------------------------------------------------
# 📊 SQL QUERIES (Dynamic Timezone Logic)
# ----------------------------------------------------
target_date_str = str(selected_date)

# Total deals (Past data strictly PKT, New data UK Time)
query_totals = f"""
SELECT 
    employee_name,
    SUM(links_converted) AS total_links_posted
FROM 
    deal_logs
WHERE 
    (CASE 
        WHEN created_at < '2026-07-23 00:00:00+00' THEN created_at AT TIME ZONE 'Asia/Karachi'
        ELSE created_at AT TIME ZONE 'Europe/London'
    END)::date = '{target_date_str}'
GROUP BY 
    employee_name
ORDER BY 
    total_links_posted DESC;
"""

# Hourly breakdown using the same dynamic timezone mapping
query_hourly = f"""
SELECT 
    EXTRACT(HOUR FROM 
        CASE 
            WHEN created_at < '2026-07-23 00:00:00+00' THEN created_at AT TIME ZONE 'Asia/Karachi'
            ELSE created_at AT TIME ZONE 'Europe/London'
        END
    ) AS hour_of_day,
    employee_name,
    SUM(links_converted) AS links_posted
FROM 
    deal_logs
WHERE 
    (CASE 
        WHEN created_at < '2026-07-23 00:00:00+00' THEN created_at AT TIME ZONE 'Asia/Karachi'
        ELSE created_at AT TIME ZONE 'Europe/London'
    END)::date = '{target_date_str}'
GROUP BY 
    hour_of_day, employee_name
ORDER BY 
    hour_of_day ASC;
"""

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
    st.subheader("📈 Hour-by-Hour Performance")
    if not df_hourly.empty:
        pivot_df = df_hourly.pivot(index='hour_of_day', columns='employee_name', values='links_posted').fillna(0)
        st.bar_chart(pivot_df, use_container_width=True)
    else:
        st.info("No hourly data available.")

st.markdown("---")

# ----------------------------------------------------
# 🕵️‍♂️ CMD-STYLE AUDIT TRAIL
# ----------------------------------------------------
st.subheader("📝 Employee Audit Trail")

if not df_totals.empty:
    employee_list = df_totals['employee_name'].tolist()
    selected_employee = st.selectbox("Select an employee to view their detailed log:", employee_list)
    
    query_audit = f"""
    SELECT 
        employee_name,
        links_converted,
        TO_CHAR(
            CASE 
                WHEN created_at < '2026-07-23 00:00:00+00' THEN created_at AT TIME ZONE 'Asia/Karachi'
                ELSE created_at AT TIME ZONE 'Europe/London'
            END, 'YYYY-MM-DD'
        ) AS audit_date,
        TO_CHAR(
            CASE 
                WHEN created_at < '2026-07-23 00:00:00+00' THEN created_at AT TIME ZONE 'Asia/Karachi'
                ELSE created_at AT TIME ZONE 'Europe/London'
            END, 'HH24:MI:SS'
        ) AS audit_time
    FROM 
        deal_logs
    WHERE 
        (CASE 
            WHEN created_at < '2026-07-23 00:00:00+00' THEN created_at AT TIME ZONE 'Asia/Karachi'
            ELSE created_at AT TIME ZONE 'Europe/London'
        END)::date = '{target_date_str}'
        AND employee_name = '{selected_employee}'
    ORDER BY 
        created_at ASC;
    """
    
    df_audit = conn.query(query_audit, ttl=0)
    
    if not df_audit.empty:
        audit_text = ""
        for index, row in df_audit.iterrows():
            audit_text += f"{row['employee_name']} converted {row['links_converted']} deals on {row['audit_date']} at {row['audit_time']}\n"
        
        st.code(audit_text, language="bash")
    else:
        st.write("No audit logs found for this employee on this date.")
else:
    st.write("Awaiting data to generate audit trails.")

# Footer timestamp
st.sidebar.markdown("---")
st.sidebar.text(f"Last updated: {datetime.now(uk_tz).strftime('%I:%M:%S %p UK Time')}")

# Auto-refresh
time.sleep(refresh_rate)
st.rerun()
