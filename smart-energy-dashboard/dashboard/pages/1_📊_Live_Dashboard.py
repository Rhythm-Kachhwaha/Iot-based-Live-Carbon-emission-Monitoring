# dashboard/pages/1_📊_Live_Dashboard.py - Real-time Energy Monitoring
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (
    load_data, add_emissions, format_number, get_carbon_metrics,
    check_frequency_alert, create_summary_metrics, validate_data_quality
)

st.set_page_config(
    page_title="📊 Live Dashboard",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-container {
        background-color: #1a3e25;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #09ab3b;
        margin: 0.5rem 0;
    }
    .alert-container {
        background-color: #4a1a1a;
        border-left: 4px solid #ff4444;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .carbon-metrics {
        background: linear-gradient(135deg, #0f2315, #1a3e25);
        padding: 1.5rem;
        border-radius: 15px;
        border: 2px solid #09ab3b;
        margin: 1rem 0;
    }
    .chart-container {
        background-color: #0f2315;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("# 📊 Live Energy Dashboard")
st.markdown("*Real-time monitoring of smart energy meter data*")

# Get selected source from session state (set in main app)
selected_source = st.session_state.get('selected_source', 'All')

# Load data
try:
    df = load_data(source=selected_source)
    
    if df.empty:
        st.warning("📊 No meter data available. Please check if your IoT device is sending data.")
        st.stop()
        
    # Add emissions calculations
    df = add_emissions(df)
    
    # Get latest reading
    latest = df.iloc[-1]
    
    # Data quality check
    quality = validate_data_quality(df)
    
    # Show data quality status
    if quality['status'] == 'good':
        st.success(f"✅ Data Quality: Excellent ({quality['total_readings']} readings)")
    elif quality['status'] == 'fair':
        st.warning(f"⚠️ Data Quality: Fair - {', '.join(quality['warnings'])}")
    else:
        st.error(f"❌ Data Quality: Poor - {', '.join(quality['issues'])}")
    
    # Live Metrics Section
    st.markdown("## ⚡ Live Metrics")
    
    # Create 4 columns for main metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        voltage_val = latest['voltage'] if latest['voltage'] is not None else 0
        st.metric(
            "🔋 Voltage",
            f"{format_number(voltage_val, 1)} V",
            delta=None
        )
        
        current_val = latest['current'] if latest['current'] is not None else 0
        st.metric(
            "⚡ Current", 
            f"{format_number(current_val, 2)} A",
            delta=None
        )
    
    with col2:
        load_val = latest['load_kw'] if latest['load_kw'] is not None else 0
        st.metric(
            "💡 Load",
            f"{format_number(load_val, 3)} kW",
            delta=None
        )
        
        pf_val = latest['power_factor'] if latest['power_factor'] is not None else 0
        st.metric(
            "🧮 Power Factor",
            f"{format_number(pf_val, 3)}",
            delta=None
        )
    
    with col3:
        freq_val = latest['frequency'] if latest['frequency'] is not None else 0
        st.metric(
            "⏱️ Frequency",
            f"{format_number(freq_val, 2)} Hz",
            delta=None
        )
        
        kwh_val = latest['kwh'] if latest['kwh'] is not None else 0
        st.metric(
            "🔢 Total kWh",
            f"{format_number(kwh_val, 1)}",
            delta=None
        )
    
    with col4:
        retry_val = int(latest['retry_count']) if latest['retry_count'] is not None else 0
        st.metric(
            "🔄 Retry Count",
            f"{retry_val}",
            delta=None
        )
        
        # Last update time
        last_update = latest['received_at']
        if isinstance(last_update, str):
            last_update = pd.to_datetime(last_update)
        
        time_diff = datetime.now() - last_update
        if time_diff < timedelta(minutes=1):
            st.success("🟢 Live")
        elif time_diff < timedelta(minutes=5):
            st.warning("🟡 Recent")
        else:
            st.error("🔴 Stale")
    
    # Show device info
    st.info(f"📱 **Device**: {latest['source']} | 🕐 **Last Reading**: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Frequency Alert
    freq_alert, freq_msg = check_frequency_alert(latest['frequency'])
    if freq_alert:
        st.markdown(f'<div class="alert-container">{freq_msg}</div>', unsafe_allow_html=True)
    
    # Carbon Footprint Section
    st.markdown("## 🌱 Carbon Footprint Analysis")
    
    carbon_metrics = get_carbon_metrics(df)
    
    with st.container():
        st.markdown('<div class="carbon-metrics">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "♻️ Instant Emission",
                f"{format_number(carbon_metrics['instant_emission'], 4)} kg CO₂",
                help="Carbon emission from the latest power consumption reading"
            )
        
        with col2:
            st.metric(
                "📈 Today's Emissions",
                f"{format_number(carbon_metrics['daily_emission'], 3)} kg CO₂",
                help="Total carbon emissions for today"
            )
        
        with col3:
            st.metric(
                "🧮 Total Emissions",
                f"{format_number(carbon_metrics['total_emission'], 2)} kg CO₂",
                help="Cumulative carbon emissions from all readings"
            )
        
        # Show emission rate
        if carbon_metrics['total_emission'] > 0:
            st.info(f"""
            💡 **Emission Insights:**
            - Average daily emission: **{format_number(carbon_metrics['avg_daily_emission'], 3)} kg CO₂/day**
            - Using emission factor: **0.82 kg CO₂/kWh** (Indian grid average)
            - Total energy consumed: **{format_number(carbon_metrics['total_emission'] / 0.82, 2)} kWh**
            """)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Historical Trends Section
    st.markdown("## 📈 Real-time Trends")
    
    # Time range selector
    time_options = {
        "Last 1 Hour": timedelta(hours=1),
        "Last 6 Hours": timedelta(hours=6),
        "Last 24 Hours": timedelta(hours=24),
        "Last 3 Days": timedelta(days=3),
        "Last Week": timedelta(days=7),
        "All Data": None
    }
    
    selected_range = st.selectbox("📅 Select Time Range", list(time_options.keys()), index=2)
    
    # Filter data based on selection
    if time_options[selected_range] is not None:
        cutoff_time = datetime.now() - time_options[selected_range]
        filtered_df = df[df['received_at'] >= cutoff_time]
    else:
        filtered_df = df
    
    if filtered_df.empty:
        st.warning("No data available for the selected time range.")
    else:
        # Create multiple charts
        
        # Power Consumption Chart
        st.markdown("### 💡 Power Consumption")
        fig_power = go.Figure()
        
        if 'load_kw' in filtered_df.columns:
            fig_power.add_trace(go.Scatter(
                x=filtered_df['received_at'],
                y=filtered_df['load_kw'],
                mode='lines+markers',
                name='Load (kW)',
                line=dict(color='#09ab3b', width=2),
                marker=dict(size=4)
            ))
        
        fig_power.update_layout(
            title="Real-time Power Consumption",
            xaxis_title="Time",
            yaxis_title="Load (kW)",
            template="plotly_dark",
            height=400
        )
        
        st.plotly_chart(fig_power, use_container_width=True)
        
        # Voltage and Current Chart
        st.markdown("### ⚡ Electrical Parameters")
        
        fig_electrical = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Voltage (V)', 'Current (A)'),
            vertical_spacing=0.1
        )
        
        if 'voltage' in filtered_df.columns:
            fig_electrical.add_trace(
                go.Scatter(
                    x=filtered_df['received_at'],
                    y=filtered_df['voltage'],
                    mode='lines',
                    name='Voltage',
                    line=dict(color='#ff6b6b', width=2)
                ),
                row=1, col=1
            )
        
        if 'current' in filtered_df.columns:
            fig_electrical.add_trace(
                go.Scatter(
                    x=filtered_df['received_at'],
                    y=filtered_df['current'],
                    mode='lines',
                    name='Current',
                    line=dict(color='#4ecdc4', width=2)
                ),
                row=2, col=1
            )
        
        fig_electrical.update_layout(
            template="plotly_dark",
            height=500,
            showlegend=False
        )
        
        st.plotly_chart(fig_electrical, use_container_width=True)
        
        # Carbon Emissions Over Time
        st.markdown("### 🌱 Carbon Emissions Timeline")
        
        # Cumulative emissions
        filtered_df = filtered_df.sort_values('received_at')
        filtered_df['cumulative_emission'] = filtered_df['instant_emission'].cumsum()
        
        fig_carbon = go.Figure()
        
        # Instant emissions
        fig_carbon.add_trace(go.Scatter(
            x=filtered_df['received_at'],
            y=filtered_df['instant_emission'],
            mode='lines+markers',
            name='Instant Emission',
            line=dict(color='#09ab3b', width=2),
            marker=dict(size=3),
            yaxis='y'
        ))
        
        # Cumulative emissions
        fig_carbon.add_trace(go.Scatter(
            x=filtered_df['received_at'],
            y=filtered_df['cumulative_emission'],
            mode='lines',
            name='Cumulative Emission',
            line=dict(color='#ff9500', width=2),
            yaxis='y2'
        ))
        
        fig_carbon.update_layout(
            title="Carbon Emissions Over Time",
            xaxis_title="Time",
            yaxis=dict(title="Instant Emission (kg CO₂)", side="left"),
            yaxis2=dict(title="Cumulative Emission (kg CO₂)", side="right", overlaying="y"),
            template="plotly_dark",
            height=400,
            legend=dict(x=0.01, y=0.99)
        )
        
        st.plotly_chart(fig_carbon, use_container_width=True)
        
        # Frequency and Power Factor
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### ⏱️ Frequency Stability")
            fig_freq = go.Figure()
            
            if 'frequency' in filtered_df.columns:
                fig_freq.add_trace(go.Scatter(
                    x=filtered_df['received_at'],
                    y=filtered_df['frequency'],
                    mode='lines+markers',
                    name='Frequency',
                    line=dict(color='#ffd93d', width=2),
                    marker=dict(size=3)
                ))
                
                # Add normal range bands
                fig_freq.add_hline(y=50, line_dash="dash", line_color="green", annotation_text="Nominal")
                fig_freq.add_hrect(y0=48, y1=52, fillcolor="green", opacity=0.1, annotation_text="Normal Range")
            
            fig_freq.update_layout(
                xaxis_title="Time",
                yaxis_title="Frequency (Hz)",
                template="plotly_dark",
                height=300,
                showlegend=False
            )
            
            st.plotly_chart(fig_freq, use_container_width=True)
        
        with col2:
            st.markdown("### 🧮 Power Factor")
            fig_pf = go.Figure()
            
            if 'power_factor' in filtered_df.columns:
                fig_pf.add_trace(go.Scatter(
                    x=filtered_df['received_at'],
                    y=filtered_df['power_factor'],
                    mode='lines+markers',
                    name='Power Factor',
                    line=dict(color='#a8e6cf', width=2),
                    marker=dict(size=3),
                    fill='tonexty'
                ))
            
            fig_pf.update_layout(
                xaxis_title="Time",
                yaxis_title="Power Factor",
                yaxis_range=[0, 1],
                template="plotly_dark",
                height=300,
                showlegend=False
            )
            
            st.plotly_chart(fig_pf, use_container_width=True)
        
        # Summary Statistics
        st.markdown("### 📊 Summary Statistics")
        
        summary_col1, summary_col2, summary_col3 = st.columns(3)
        
        with summary_col1:
            st.markdown("**Power Consumption**")
            if 'load_kw' in filtered_df.columns:
                load_stats = filtered_df['load_kw'].describe()
                st.write(f"• Average: {format_number(load_stats['mean'], 3)} kW")
                st.write(f"• Maximum: {format_number(load_stats['max'], 3)} kW")
                st.write(f"• Minimum: {format_number(load_stats['min'], 3)} kW")
        
        with summary_col2:
            st.markdown("**Electrical Quality**")
            if 'voltage' in filtered_df.columns:
                voltage_stats = filtered_df['voltage'].describe()
                st.write(f"• Avg Voltage: {format_number(voltage_stats['mean'], 1)} V")
            if 'power_factor' in filtered_df.columns:
                pf_stats = filtered_df['power_factor'].describe()
                st.write(f"• Avg Power Factor: {format_number(pf_stats['mean'], 3)}")
            if 'frequency' in filtered_df.columns:
                freq_out_of_range = len(filtered_df[
                    (filtered_df['frequency'] < 48) | (filtered_df['frequency'] > 52)
                ])
                st.write(f"• Freq. Issues: {freq_out_of_range} readings")
        
        with summary_col3:
            st.markdown("**Environmental Impact**")
            period_emission = filtered_df['instant_emission'].sum()
            st.write(f"• Period Emissions: {format_number(period_emission, 3)} kg CO₂")
            if period_emission > 0:
                equivalent_trees = period_emission / 21.77  # kg CO₂ absorbed per tree per year
                st.write(f"• Tree Equivalent: {format_number(equivalent_trees, 2)} trees/year")
            avg_emission_rate = period_emission / max(len(filtered_df), 1)
            st.write(f"• Avg Rate: {format_number(avg_emission_rate, 4)} kg CO₂/reading")

except Exception as e:
    st.error(f"Error loading dashboard data: {str(e)}")
    st.info("Please ensure:")
    st.info("1. The Flask API server is running on http://localhost:8080")
    st.info("2. The database file exists and contains meter data")
    st.info("3. Your IoT device is sending data to the API")

# Auto-refresh option
if st.checkbox("🔄 Auto-refresh every 10 seconds", value=False):
    import time
    time.sleep(10)
    st.rerun()