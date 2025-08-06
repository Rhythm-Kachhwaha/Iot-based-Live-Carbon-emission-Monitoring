# dashboard/pages/2_🧾_Raw_Data_Log.py - Complete Data Table with Export
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_data, add_emissions, format_number, export_data_to_csv

st.set_page_config(
    page_title="🧾 Raw Data Log",
    page_icon="🧾",
    layout="wide"
)

st.markdown("# 🧾 Raw Data Log")
st.markdown("*Complete energy meter data with search, filter, and export capabilities*")

# Get selected source from session state
selected_source = st.session_state.get('selected_source', 'All')

# Load data
try:
    df = load_data(source=selected_source)
    
    if df.empty:
        st.warning("📊 No meter data available.")
        st.stop()
    
    # Add emissions calculations
    df = add_emissions(df)
    
    # Filter Controls
    st.markdown("## 🔧 Data Filters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Date range filter
        min_date = df['date'].min()
        max_date = df['date'].max()
        
        date_range = st.date_input(
            "📅 Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    with col2:
        # Retry count filter
        show_errors_only = st.checkbox("🔄 Show only errors (retry > 0)", value=False)
        if show_errors_only:
            df = df[df['retry_count'] > 0]
    
    with col3:
        # Row limit
        row_limit = st.selectbox(
            "📊 Rows to display",
            options=[100, 500, 1000, 5000, 10000],
            index=2
        )
        
        if len(df) > row_limit:
            df = df.tail(row_limit)
    
    with col4:
        # Search functionality
        search_term = st.text_input("🔍 Search in source", placeholder="Enter device name...")
        if search_term:
            df = df[df['source'].str.contains(search_term, case=False, na=False)]
    
    # Display summary info
    st.info(f"📊 Showing **{len(df):,}** readings | Latest: **{df['received_at'].max()}**")
    
    # Highlight problematic readings
    if not df.empty:
        error_count = len(df[df['retry_count'] > 0])
        freq_issues = len(df[(df['frequency'] < 48) | (df['frequency'] > 52)])
        
        if error_count > 0:
            st.warning(f"⚠️ Found {error_count} readings with retry count > 0")
        
        if freq_issues > 0:
            st.warning(f"⚠️ Found {freq_issues} readings with frequency issues")
    
    # Data Table
    st.markdown("## 📋 Energy Meter Readings")
    
    if not df.empty:
        # Prepare display dataframe
        display_df = df.copy()
        
        # Format numeric columns for display
        numeric_cols = ['voltage', 'current', 'power_factor', 'load_kw', 'kwh', 'frequency', 'instant_emission']
        for col in numeric_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: format_number(x, 3) if pd.notna(x) else 'N/A')
        
        # Format datetime columns
        display_df['received_at'] = pd.to_datetime(display_df['received_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Color code retry counts
        def highlight_retry_count(row):
            if row['retry_count'] > 0:
                return ['background-color: #4a1a1a'] * len(row)
            return [''] * len(row)
        
        # Display the table with styling
        styled_df = display_df.style.apply(highlight_retry_count, axis=1)
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            height=600,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "voltage": st.column_config.TextColumn("Voltage (V)", width="small"),
                "current": st.column_config.TextColumn("Current (A)", width="small"),
                "power_factor": st.column_config.TextColumn("Power Factor", width="small"),
                "load_kw": st.column_config.TextColumn("Load (kW)", width="small"),
                "kwh": st.column_config.TextColumn("kWh", width="small"),
                "frequency": st.column_config.TextColumn("Freq (Hz)", width="small"),
                "instant_emission": st.column_config.TextColumn("Emission (kg CO₂)", width="medium"),
                "retry_count": st.column_config.NumberColumn("Retries", width="small"),
                "source": st.column_config.TextColumn("Source", width="medium"),
                "received_at": st.column_config.TextColumn("Received At", width="large"),
            }
        )
    
    # Export Section
    st.markdown("## 📤 Data Export")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export Current View (CSV)", use_container_width=True, type="primary"):
            if not df.empty:
                csv_data = export_data_to_csv(df)
                filename = f"energy_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
                st.download_button(
                    label="💾 Download CSV File",
                    data=csv_data,
                    file_name=filename,
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.error("No data to export")
    
    with col2:
        if st.button("📈 Export with Analytics", use_container_width=True):
            if not df.empty:
                # Add additional calculated columns for analytics export
                analytics_df = df.copy()
                analytics_df['power_consumption_rate'] = analytics_df['load_kw'] / analytics_df['load_kw'].shift(1)
                analytics_df['efficiency_score'] = analytics_df['power_factor'] * 100
                analytics_df['carbon_intensity'] = analytics_df['instant_emission'] / analytics_df['load_kw']
                
                csv_data = analytics_df.to_csv(index=False).encode('utf-8')
                filename = f"energy_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
                st.download_button(
                    label="💾 Download Analytics CSV",
                    data=csv_data,
                    file_name=filename,
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.error("No data to export")
    
    with col3:
        if st.button("📋 Export Summary Report", use_container_width=True):
            if not df.empty:
                # Create summary report
                summary_data = {
                    'Metric': [
                        'Total Readings',
                        'Date Range',
                        'Average Voltage (V)',
                        'Average Current (A)',
                        'Average Load (kW)',
                        'Average Power Factor',
                        'Average Frequency (Hz)',
                        'Total Energy (kWh)',
                        'Total Carbon Emissions (kg CO₂)',
                        'Readings with Errors',
                        'Frequency Issues',
                        'Data Sources'
                    ],
                    'Value': [
                        len(df),
                        f"{df['date'].min()} to {df['date'].max()}",
                        format_number(df['voltage'].mean(), 2),
                        format_number(df['current'].mean(), 3),
                        format_number(df['load_kw'].mean(), 3),
                        format_number(df['power_factor'].mean(), 3),
                        format_number(df['frequency'].mean(), 2),
                        format_number(df['kwh'].max() - df['kwh'].min(), 2),
                        format_number(df['instant_emission'].sum(), 3),
                        len(df[df['retry_count'] > 0]),
                        len(df[(df['frequency'] < 48) | (df['frequency'] > 52)]),
                        df['source'].nunique()
                    ]
                }
                
                summary_df = pd.DataFrame(summary_data)
                csv_data = summary_df.to_csv(index=False).encode('utf-8')
                filename = f"energy_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
                st.download_button(
                    label="💾 Download Summary CSV",
                    data=csv_data,
                    file_name=filename,
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.error("No data to export")
    
    # Quick Statistics
    if not df.empty:
        st.markdown("## 📊 Quick Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Total Readings", f"{len(df):,}")
            st.metric("🔄 Error Readings", f"{len(df[df['retry_count'] > 0]):,}")
        
        with col2:
            avg_voltage = df['voltage'].mean() if 'voltage' in df.columns else 0
            avg_current = df['current'].mean() if 'current' in df.columns else 0
            st.metric("🔋 Avg Voltage", f"{format_number(avg_voltage, 1)} V")
            st.metric("⚡ Avg Current", f"{format_number(avg_current, 2)} A")
        
        with col3:
            total_kwh = df['kwh'].max() - df['kwh'].min() if 'kwh' in df.columns else 0
            avg_load = df['load_kw'].mean() if 'load_kw' in df.columns else 0
            st.metric("🔢 Energy Consumed", f"{format_number(total_kwh, 2)} kWh")
            st.metric("💡 Avg Load", f"{format_number(avg_load, 3)} kW")
        
        with col4:
            total_emission = df['instant_emission'].sum()
            avg_pf = df['power_factor'].mean() if 'power_factor' in df.columns else 0
            st.metric("🌱 Total Emissions", f"{format_number(total_emission, 3)} kg CO₂")
            st.metric("🧮 Avg Power Factor", f"{format_number(avg_pf, 3)}")

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.info("Please ensure:")
    st.info("1. The Flask API server is running")
    st.info("2. The database contains meter data")
    st.info("3. Your IoT device is sending data")

# Auto-refresh toggle
if st.checkbox("🔄 Auto-refresh every 30 seconds", value=False):
    import time
    time.sleep(30)
    st.rerun()