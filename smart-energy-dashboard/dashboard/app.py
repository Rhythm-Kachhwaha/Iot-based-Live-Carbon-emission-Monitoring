# dashboard/app.py - Main Streamlit Dashboard Entry Point
import streamlit as st
import os
import sys
from datetime import datetime

# Add the current directory to the Python path to import utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import load_data, get_system_status

# Configure Streamlit page
st.set_page_config(
    page_title="🔌 Smart Energy Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

#  CSS for green theme
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #0f2315 0%, #1a3e25 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #1a3e25;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #09ab3b;
    }
    .status-online {
        color: #09ab3b;
        font-weight: bold;
    }
    .status-offline {
        color: #ff4444;
        font-weight: bold;
    }
    .sidebar .sidebar-content {
        background-color: #0f2315;
    }
</style>
""", unsafe_allow_html=True)

# Header section
with st.container():
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("# 🔌 Smart Energy Dashboard")
        st.markdown("*Real-time IoT energy monitoring system*")
    
    with col2:
        st.markdown(f"""
        **📅 Current Time**  
        {datetime.now().strftime('%d %b %Y')}  
        {datetime.now().strftime('%H:%M:%S')}
        """)
    
    with col3:
        # System status
        status = get_system_status()
        if status['database_connected']:
            st.markdown('<p class="status-online">🟢 System Online</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="status-offline">🔴 System Offline</p>', unsafe_allow_html=True)

# Sidebar - About and Configuration
with st.sidebar:
    # About Section
    with st.expander("ℹ️ About Carbon Footprint Calculator", expanded=False):
        st.markdown("""
        ### 🔌 Dashboard
        A real-time visualization system for monitoring energy usage from an IoT-based **Smart Energy Meter**, designed to help track power parameters and estimate **carbon footprint** based on electricity usage.

        #### 🧑‍💻 Project Owner:
        - **Name**: Rhythm Kachhwaha
        - **Role**: Machine Learning Engineer, Software Developer & IoT Integrator.
        - **Tech Stack**: AVR ATmega328PB, SIMCOM A7672S, Flask, SQLite3, Streamlit, Python, Embedded C

        #### 📡 Data Source:
        - The system receives energy data every **10 seconds** from an embedded microcontroller using gprs module.
        - Data includes: voltage, current, load (kW), power factor, frequency, kWh, and device source.

        #### 🌱 Carbon Footprint Calculation:
        - Based on the kWh difference between readings (ΔkWh)
        - **Emission Factor: 0.82 kg CO₂ per kWh** (standard Indian grid average)
        - **Instant Emission**: `∆kWh × 0.82`
        - **Cumulative Emission**: `Sum of all emissions over time`

        #### 📊 Features:
        - Real-time metrics & graphs
        - Carbon emission estimator
        - Interactive historical plots
        - Data storage in SQLite
        - CSV export support
        - Multi-device monitoring

        #### 🌍 Goal:
        Enable actionable insights on energy consumption and promote low-carbon living through real-time feedback and data visibility.
        """)
    
    st.divider()
    
    # Global Filters
    st.markdown("### 🔧 Global Filters")
    
    # Device/Source Filter
    try:
        df = load_data()
        if not df.empty:
            sources = ['All'] + sorted(df['source'].dropna().unique().tolist())
            selected_source = st.selectbox(
                "🔎 Select Device/Source",
                options=sources,
                index=0,
                key="global_source_filter"
            )
            
            # Store in session state for use across pages
            st.session_state.selected_source = selected_source
            
            # Show device info
            if selected_source != 'All':
                device_info = df[df['source'] == selected_source]
                if not device_info.empty:
                    latest = device_info.iloc[-1]
                    st.info(f"""
                    **Device Info:**
                    - **Source**: {selected_source}
                    - **Last Seen**: {latest['received_at']}
                    - **Total Readings**: {len(device_info):,}
                    """)
        else:
            st.warning("No data available")
            st.session_state.selected_source = 'All'
            
    except Exception as e:
        st.error(f"Error loading device list: {str(e)}")
        st.session_state.selected_source = 'All'
    
    st.divider()
    
    # System Info
    st.markdown("### 📊 System Status")
    
    try:
        if status['database_connected']:
            st.success("Database: Connected ✅")
            
            # Show basic stats
            total_readings = status.get('total_readings', 0)
            last_24h = status.get('last_24h_readings', 0)
            
            st.metric("Total Readings", f"{total_readings:,}")
            st.metric("Last 24h", f"{last_24h:,}")
            
            if status.get('database_size_mb'):
                st.metric("DB Size", f"{status['database_size_mb']:.1f} MB")
                
        else:
            st.error("Database: Disconnected ❌")
            
    except Exception as e:
        st.error(f"Error getting system status: {str(e)}")
    
    st.divider()
    
    # Quick Actions
    st.markdown("### ⚡ Quick Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        if st.button("📊 Export CSV", use_container_width=True):
            st.switch_page("pages/2_🧾_Raw_Data_Log.py")

# Main content area
st.markdown("---")

# Welcome message and navigation
if not st.session_state.get('page_initialized', False):
    st.markdown("""
    ## 👋 Welcome to the Smart Energy Dashboard!
    
    This dashboard provides real-time monitoring and analysis of your IoT smart energy meter data.
    
    ### 📱 Available Pages:
    - **📊 Live Dashboard**: Real-time metrics, charts, and carbon footprint analysis per household
    - **🧾 Raw Data Log**: Complete data table with search, filter, and export capabilities
    - **📈 Analytics**: Advanced analytics, trends, and insights
    - **⚙️ Settings**: System configuration and preferences
    
    ### 🚀 Getting Started:
    1. Select a device from the sidebar filter
    2. Navigate to the **Live Dashboard** to see real-time data
    3. Explore historical trends in the **Analytics** section
    4. Export data from the **Raw Data Log** page
    
    ### 📡 Data Flow:
    ```
    IoT Device → Flask API → SQLite Database → Streamlit Dashboard
    ```
    """)
    
    # Show recent activity if data exists
    try:
        df = load_data()
        if not df.empty:
            st.markdown("### 📈 Recent Activity")
            
            # Latest readings summary
            latest = df.iloc[-1]
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "🔋 Latest Voltage",
                    f"{latest['voltage']:.1f} V" if latest['voltage'] else "N/A"
                )
            
            with col2:
                st.metric(
                    "⚡ Latest Current", 
                    f"{latest['current']:.2f} A" if latest['current'] else "N/A"
                )
            
            with col3:
                st.metric(
                    "💡 Latest Load",
                    f"{latest['load_kw']:.2f} kW" if latest['load_kw'] else "N/A"
                )
            
            with col4:
                st.metric(
                    "🔢 Total kWh",
                    f"{latest['kwh']:.1f}" if latest['kwh'] else "N/A"
                )
            
            # Show recent readings chart
            if len(df) >= 10:
                st.markdown("#### 📊 Recent Power Consumption (Last 50 readings)")
                recent_data = df.tail(50)
                
                if 'load_kw' in recent_data.columns:
                    st.line_chart(
                        recent_data.set_index('received_at')['load_kw'],
                        height=300
                    )
        else:
            st.info("No meter data available yet. Start your IoT device to begin collecting data!")
            
    except Exception as e:
        st.error(f"Error loading recent activity: {str(e)}")
    
    # Navigation buttons
    st.markdown("### 🧭 Quick Navigation")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Live Dashboard", use_container_width=True, type="primary"):
            st.switch_page("pages/1_📊_Live_Dashboard.py")
    
    with col2:
        if st.button("🧾 Raw Data", use_container_width=True):
            st.switch_page("pages/2_🧾_Raw_Data_Log.py")
    
    with col3:
        if st.button("📈 Analytics", use_container_width=True):
            st.switch_page("pages/3_📈_Analytics.py")
    
    with col4:
        if st.button("⚙️ Settings", use_container_width=True):
            st.switch_page("pages/4_⚙️_Settings.py")

# Auto-refresh every 30 seconds
if st.checkbox("🔄 Auto-refresh (30s)", value=False):
    import time
    time.sleep(30)
    st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>🔌 Carbon footprint Energy Dashboard v1.0 | Built by Rhythm Kachhwaha</p>
    <p>Powered by Streamlit  | Data from IoT Smart Energy Meter 📡</p>
</div>
""", unsafe_allow_html=True)