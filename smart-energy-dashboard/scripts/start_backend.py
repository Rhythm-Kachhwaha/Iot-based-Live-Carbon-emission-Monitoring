# scripts/start_backend.py - Flask Backend Startup Script

"""
Smart Energy Meter - Backend Server Startup Script
Starts the Flask API server with proper configuration
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("🚀 Starting Smart Energy Meter Backend Server...")
    print("=" * 60)
    
    # Get project root directory
    project_root = Path(__file__).parent.parent
    backend_dir = project_root / "backend"
    
    # Change to backend directory
    os.chdir(backend_dir)

    # Create necessary directories
    data_dir = project_root / "data"
    logs_dir = data_dir / "logs"
    
    data_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)
    
    print("✅ Created data directories")
    
    print("📊 Configuration:")
    print(f"   • Database path: {data_dir / 'meter_data.db'}")
    print(f"   • Server: http://localhost:8080")
    print("=" * 60)
    
    # Start the Flask server using system Python
    try:
        print("🔥 Starting Flask server...")
        subprocess.run(["python", "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
