
"""
Smart Energy Meter - Dashboard Startup Script (No Virtualenv)
Starts the Streamlit dashboard using system Python
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("🌟 Starting Smart Energy Dashboard...")
    print("=" * 60)
    
    # Get project root directory
    project_root = Path(__file__).parent.parent
    dashboard_dir = project_root / "dashboard"
    
    # Change to dashboard directory
    os.chdir(dashboard_dir)
    
    # Create necessary directories
    data_dir = project_root / "data"
    logs_dir = data_dir / "logs"
    data_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)
    
    print("✅ Created data directories")
    
    # Check if Flask API is running
    print("🔍 Checking Flask API connection...")
    try:
        import requests
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            print("✅ Flask API is running and accessible")
        else:
            print("⚠️  Flask API responded with error")
    except Exception:
        print("⚠️  Flask API is not accessible. Please start the backend first.")
        print("   Run: python scripts/start_backend.py")
    
    print("📊 Configuration:")
    print(f"   • Dashboard: http://localhost:8501")
    print(f"   • API Backend: http://localhost:8080")
    print(f"   • Database: {data_dir / 'meter_data.db'}")
    print("=" * 60)
    
    # Start Streamlit using system Python
    try:
        print("🚀 Starting Streamlit dashboard...")
        subprocess.run(["streamlit", "run", "app.py", "--server.port=8501"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Dashboard failed to start: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
