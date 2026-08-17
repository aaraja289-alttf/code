import streamlit as st
import pandas as pd
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
# 🕵️‍♂️ BOTH AUDIT TRAILS (Side-by-Side)
# ----------------------------------------------------
col_audit1, col_audit2 = st.columns(2)

# --- 1. EMPLOYEE AUDIT TRAIL (Restored) ---
with col_audit1:
    st.subheader("📝 Employee Audit Trail")

    if not df_totals.empty:
        employee_list = df_totals['employee_name'].tolist()
        selected_employee = st.selectbox("Select an employee to view their log:", employee_list)
        
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
                END, 'HH12:MI:SS AM'
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
            st.write("No audit logs found for this employee.")
    else:
        st.write("Awaiting data to generate audit trails.")


# --- 2. HOUR-BY-HOUR AUDIT TRAIL (Easier Formatting) ---
with col_audit2:
    st.subheader("⏰ Hour-by-Hour Audit Trail")

    if not df_hourly.empty:
        hour_list = sorted(df_hourly['hour_of_day'].unique().astype(int).tolist())
        
        # Helper function to turn "21" into "09:00 PM to 10:00 PM"
        def format_hour_simple(h):
            start_time = datetime.strptime(str(h), "%H").strftime("%I:00 %p")
            end_h = 0 if h == 23 else h + 1
            end_time = datetime.strptime(str(end_h), "%H").strftime("%I:00 %p")
            return f"{start_time} to {end_time} (UK Time)"

        selected_hour = st.selectbox(
            "Select working hour:", 
            hour_list,
            format_func=format_hour_simple
        )
        
        # Extract logs explicitly using UK Time
        query_hour_audit = f"""
        SELECT 
            employee_name,
            links_converted,
            TO_CHAR(created_at AT TIME ZONE 'Europe/London', 'HH12:MI:SS AM') AS audit_time
        FROM 
            deal_logs
        WHERE 
            (CASE 
                WHEN created_at < '2026-07-23 00:00:00+00' THEN created_at AT TIME ZONE 'Asia/Karachi'
                ELSE created_at AT TIME ZONE 'Europe/London'
            END)::date = '{target_date_str}'
            AND EXTRACT(HOUR FROM created_at AT TIME ZONE 'Europe/London') = {selected_hour}
        ORDER BY 
            created_at ASC;
        """
        
        df_hour_audit = conn.query(query_hour_audit, ttl=0)
        
        if not df_hour_audit.empty:
            hr_audit_text = f"--- Logs for {format_hour_simple(selected_hour)} ---\n\n"
            for index, row in df_hour_audit.iterrows():
                hr_audit_text += f"[{row['audit_time']}] {row['employee_name']} converted {row['links_converted']} deals\n"
            
            st.code(hr_audit_text, language="bash")
        else:
            st.write("No audit logs found for this specific hour.")
    else:
        st.write("Awaiting data to generate audit trails.")

# Footer timestamp
st.sidebar.markdown("---")
st.sidebar.text(f"Last updated: {datetime.now(uk_tz).strftime('%I:%M:%S %p UK Time')}")
