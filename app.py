st.markdown("---")

# ----------------------------------------------------
# 📥 EXPORT FULL DAY AUDIT TRAIL
# ----------------------------------------------------
st.subheader("📥 Export Full Day Audit")

query_full_day = f"""
SELECT 
    employee_name AS "Employee Name",
    links_converted AS "Links Converted",
    TO_CHAR(
        CASE 
            WHEN created_at < '2026-07-23 00:00:00+00' THEN created_at AT TIME ZONE 'Asia/Karachi'
            ELSE created_at AT TIME ZONE 'Europe/London'
        END, 'YYYY-MM-DD'
    ) AS "Date",
    TO_CHAR(
        CASE 
            WHEN created_at < '2026-07-23 00:00:00+00' THEN created_at AT TIME ZONE 'Asia/Karachi'
            ELSE created_at AT TIME ZONE 'Europe/London'
        END, 'HH12:MI:SS AM'
    ) AS "Time"
FROM 
    deal_logs
WHERE 
    (CASE 
        WHEN created_at < '2026-07-23 00:00:00+00' THEN created_at AT TIME ZONE 'Asia/Karachi'
        ELSE created_at AT TIME ZONE 'Europe/London'
    END)::date = '{target_date_str}'
ORDER BY 
    created_at ASC;
"""

df_full_day = conn.query(query_full_day, ttl=0)

if not df_full_day.empty:
    # Convert dataframe to CSV
    csv_data = df_full_day.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label=f"📥 Download Full Day Audit Trail for {selected_date} (CSV)",
        data=csv_data,
        file_name=f"full_day_audit_{selected_date}.csv",
        mime="text/csv",
        use_container_width=True
    )
else:
    st.info("No data available to download for this date.")
