# dashboard/utils.py - Shared Utilities for Streamlit Dashboard
import sqlite3
import pandas as pd
import streamlit as st
import requests
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import os

# Configuration
DB_FILE = "data/meter_data.db"
FLASK_API_URL = "https://iot-carbon-emission-backend.onrender.com"

EMISSION_FACTOR = 0.82  # kg CO₂ per kWh
FREQ_RANGE = (48.0, 52.0)  # Hz

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@st.cache_data(ttl=10)  # Cache for 10 seconds
def load_data(source: str = None, limit: int = 10000) -> pd.DataFrame:
    """Load meter data from SQLite database with optional filtering"""
    
    try:
        # First try to get data from Flask API
        try:
            params = {}
            if source and source != 'All':
                params['source'] = source
            if limit:
                params['limit'] = limit
                
            response = requests.get(f"{FLASK_API_URL}/api/data", params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success' and data['data']:
                    df = pd.DataFrame(data['data'])
                    df['received_at'] = pd.to_datetime(df['received_at'])
                    df['date'] = df['received_at'].dt.date
                    return df.sort_values('received_at')
                    
        except requests.RequestException:
            logger.warning("Flask API not available, falling back to direct DB access")
        
        # Fallback to direct database access
        if not os.path.exists(DB_FILE):
            logger.warning(f"Database file {DB_FILE} not found")
            return pd.DataFrame()
        
        with sqlite3.connect(DB_FILE) as conn:
            query = "SELECT * FROM meter_readings WHERE 1=1"
            params = []
            
            if source and source != 'All':
                query += " AND source = ?"
                params.append(source)
            
            query += " ORDER BY received_at DESC LIMIT ?"
            params.append(limit)
            
            df = pd.read_sql_query(query, conn, params=params)
            
            if not df.empty:
                df['received_at'] = pd.to_datetime(df['received_at'])
                df['date'] = df['received_at'].dt.date
                return df.sort_values('received_at')
            
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def add_emissions(df: pd.DataFrame) -> pd.DataFrame:
    """Add carbon emission calculations to the dataframe"""
    
    if df.empty:
        return df
    
    df = df.copy()
    df = df.sort_values('received_at')
    
    # Calculate delta kWh (difference between consecutive readings)
    df['delta_kwh'] = df['kwh'].diff().fillna(0)
    
    # Handle cases where kWh might reset (negative delta)
    df['delta_kwh'] = df['delta_kwh'].clip(lower=0)
    
    # Calculate instant emission (delta_kwh * emission factor)
    df['instant_emission'] = df['delta_kwh'] * EMISSION_FACTOR
    
    return df

def format_number(value: float, decimals: int = 2) -> str:
    """Format numbers with proper decimal places and thousands separators"""
    
    if value is None or pd.isna(value):
        return "N/A"
    
    try:
        return f"{float(value):,.{decimals}f}"
    except (ValueError, TypeError):
        return "N/A"

def get_system_status() -> Dict:
    """Get system status from Flask API or database"""
    
    status = {
        'database_connected': False,
        'flask_api_connected': False,
        'total_readings': 0,
        'last_24h_readings': 0,
        'database_size_mb': 0,
        'last_reading_time': None
    }
    
    try:
        # Try Flask API first
        response = requests.get(f"{FLASK_API_URL}/health", timeout=5)
        if response.status_code == 200:
            status['flask_api_connected'] = True
            
            # Get statistics
            stats_response = requests.get(f"{FLASK_API_URL}/api/stats", timeout=5)
            if stats_response.status_code == 200:
                stats = stats_response.json().get('statistics', {})
                status.update({
                    'database_connected': True,
                    'total_readings': stats.get('total_readings', 0),
                    'last_24h_readings': stats.get('last_24h_readings', 0),
                    'database_size_mb': stats.get('database_size_mb', 0),
                    'last_reading_time': stats.get('latest_timestamp')
                })
                
    except requests.RequestException:
        pass
    
    # Fallback to direct database check
    if not status['database_connected'] and os.path.exists(DB_FILE):
        try:
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                
                # Test connection
                cursor.execute("SELECT 1")
                status['database_connected'] = True
                
                # Get basic stats
                cursor.execute("SELECT COUNT(*) FROM meter_readings")
                status['total_readings'] = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM meter_readings 
                    WHERE datetime(received_at) >= datetime('now', '-1 day')
                """)
                status['last_24h_readings'] = cursor.fetchone()[0]
                
                # Get database size
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                status['database_size_mb'] = (page_count * page_size) / (1024 * 1024)
                
        except Exception as e:
            logger.error(f"Database check failed: {str(e)}")
    
    return status

def check_frequency_alert(frequency: float) -> Tuple[bool, str]:
    """Check if frequency is within normal range and return alert status"""
    
    if frequency is None or pd.isna(frequency):
        return False, ""
    
    if not (FREQ_RANGE[0] <= frequency <= FREQ_RANGE[1]):
        return True, f"⚠️ Frequency out of range: {frequency:.2f} Hz (Normal: {FREQ_RANGE[0]}-{FREQ_RANGE[1]} Hz)"
    
    return False, ""

def get_carbon_metrics(df: pd.DataFrame) -> Dict:
    """Calculate carbon footprint metrics"""
    
    if df.empty:
        return {
            'instant_emission': 0,
            'daily_emission': 0,
            'total_emission': 0,
            'avg_daily_emission': 0
        }
    
    df = add_emissions(df)
    
    # Get latest reading for instant emission
    latest = df.iloc[-1]
    instant_emission = latest.get('instant_emission', 0)
    
    # Today's emissions
    today = date.today()
    today_df = df[df['date'] == today]
    daily_emission = today_df['instant_emission'].sum() if not today_df.empty else 0
    
    # Total emissions
    total_emission = df['instant_emission'].sum()
    
    # Average daily emission
    unique_dates = df['date'].nunique()
    avg_daily_emission = total_emission / unique_dates if unique_dates > 0 else 0
    
    return {
        'instant_emission': instant_emission,
        'daily_emission': daily_emission,
        'total_emission': total_emission,
        'avg_daily_emission': avg_daily_emission
    }

def get_power_quality_metrics(df: pd.DataFrame) -> Dict:
    """Calculate power quality metrics"""
    
    if df.empty:
        return {}
    
    # Remove null values for calculations
    df_clean = df.dropna()
    
    if df_clean.empty:
        return {}
    
    metrics = {}
    
    # Voltage metrics
    if 'voltage' in df_clean.columns:
        metrics['voltage'] = {
            'avg': df_clean['voltage'].mean(),
            'min': df_clean['voltage'].min(),
            'max': df_clean['voltage'].max(),
            'std': df_clean['voltage'].std()
        }
    
    # Current metrics
    if 'current' in df_clean.columns:
        metrics['current'] = {
            'avg': df_clean['current'].mean(),
            'min': df_clean['current'].min(),
            'max': df_clean['current'].max(),
            'std': df_clean['current'].std()
        }
    
    # Frequency metrics
    if 'frequency' in df_clean.columns:
        metrics['frequency'] = {
            'avg': df_clean['frequency'].mean(),
            'min': df_clean['frequency'].min(),
            'max': df_clean['frequency'].max(),
            'std': df_clean['frequency'].std(),
            'out_of_range': len(df_clean[
                (df_clean['frequency'] < FREQ_RANGE[0]) | 
                (df_clean['frequency'] > FREQ_RANGE[1])
            ])
        }
    
    # Power factor metrics
    if 'power_factor' in df_clean.columns:
        metrics['power_factor'] = {
            'avg': df_clean['power_factor'].mean(),
            'min': df_clean['power_factor'].min(),
            'max': df_clean['power_factor'].max(),
            'std': df_clean['power_factor'].std()
        }
    
    return metrics

def export_data_to_csv(df: pd.DataFrame, filename: str = None) -> bytes:
    """Export dataframe to CSV format"""
    
    if filename is None:
        filename = f"smart_meter_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Add emission calculations before export
    df = add_emissions(df)
    
    # Convert to CSV
    csv_data = df.to_csv(index=False)
    return csv_data.encode('utf-8')

def get_time_series_data(df: pd.DataFrame, column: str, resample_freq: str = None) -> pd.Series:
    """Get time series data for plotting"""
    
    if df.empty or column not in df.columns:
        return pd.Series()
    
    df = df.dropna(subset=[column])
    
    if df.empty:
        return pd.Series()
    
    # Set datetime as index
    df_ts = df.set_index('received_at')[column]
    
    # Resample if requested
    if resample_freq:
        df_ts = df_ts.resample(resample_freq).mean()
    
    return df_ts

def validate_data_quality(df: pd.DataFrame) -> Dict:
    """Validate data quality and return quality metrics"""
    
    if df.empty:
        return {'status': 'no_data', 'issues': ['No data available']}
    
    issues = []
    warnings = []
    
    # Check for missing values
    missing_cols = df.columns[df.isnull().any()].tolist()
    if missing_cols:
        warnings.append(f"Missing values in columns: {', '.join(missing_cols)}")
    
    # Check for duplicate timestamps
    if df['received_at'].duplicated().any():
        issues.append("Duplicate timestamps detected")
    
    # Check for unrealistic values
    if 'voltage' in df.columns:
        extreme_voltage = df[(df['voltage'] < 100) | (df['voltage'] > 300)]
        if not extreme_voltage.empty:
            warnings.append(f"{len(extreme_voltage)} readings with extreme voltage values")
    
    if 'frequency' in df.columns:
        freq_issues = df[(df['frequency'] < FREQ_RANGE[0]) | (df['frequency'] > FREQ_RANGE[1])]
        if not freq_issues.empty:
            issues.append(f"{len(freq_issues)} readings with frequency out of range")
    
    # Check data freshness
    if not df.empty:
        latest_reading = pd.to_datetime(df['received_at'].max())
        time_since_last = datetime.now() - latest_reading
        
        if time_since_last > timedelta(minutes=5):
            warnings.append(f"Latest reading is {time_since_last} old")
        
        if time_since_last > timedelta(hours=1):
            issues.append("No recent data received (> 1 hour)")
    
    # Determine overall status
    if issues:
        status = 'poor'
    elif warnings:
        status = 'fair'
    else:
        status = 'good'
    
    return {
        'status': status,
        'issues': issues,
        'warnings': warnings,
        'total_readings': len(df),
        'date_range': (df['received_at'].min(), df['received_at'].max()) if not df.empty else None
    }

def get_device_list() -> List[str]:
    """Get list of available devices/sources"""
    
    try:
        df = load_data()
        if not df.empty and 'source' in df.columns:
            return sorted(df['source'].dropna().unique().tolist())
        return []
    except Exception as e:
        logger.error(f"Error getting device list: {str(e)}")
        return []

def create_summary_metrics(df: pd.DataFrame) -> Dict:
    """Create summary metrics for dashboard"""
    
    if df.empty:
        return {}
    
    latest = df.iloc[-1]
    
    # Basic metrics from latest reading
    metrics = {
        'voltage': latest.get('voltage'),
        'current': latest.get('current'),
        'power_factor': latest.get('power_factor'),
        'load_kw': latest.get('load_kw'),
        'kwh': latest.get('kwh'),
        'frequency': latest.get('frequency'),
        'retry_count': latest.get('retry_count', 0),
        'source': latest.get('source'),
        'received_at': latest.get('received_at')
    }
    
    # Carbon metrics
    carbon_metrics = get_carbon_metrics(df)
    metrics.update(carbon_metrics)
    
    # Data quality
    quality = validate_data_quality(df)
    metrics['data_quality'] = quality['status']
    
    return metrics