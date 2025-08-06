# backend/app.py - Complete Flask Application with Database
import flask

from flask import Flask, request, jsonify, send_file
import sqlite3
import logging
import os
os.makedirs('data/logs', exist_ok=True)
from datetime import datetime, timedelta
from database import DatabaseManager
from config import Config
import csv
import io

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database manager
db_manager = DatabaseManager(app.config['DATABASE_PATH'])

# Configure logging
logging.basicConfig(
    level=getattr(logging, app.config['LOG_LEVEL']),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/flask_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@app.route('/meter', methods=['GET', 'POST'])
def receive_meter_data():
    """Receive and store energy meter data"""
    try:
        # Log incoming request details
        logger.info("=== INCOMING REQUEST ===")
        logger.info(f"Method: {request.method}")
        logger.info(f"Full URL: {request.url}")
        logger.info(f"Remote IP: {request.remote_addr}")
        logger.info(f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
        
        # Get parameters from GET query string or POST form data
        if request.method == 'GET':
            params = request.args
        else:
            params = request.form
            
        # Extract meter data parameters
        voltage = params.get('v')
        current = params.get('c')
        power_factor = params.get('pf')
        load_kw = params.get('l')
        kwh = params.get('k')
        frequency = params.get('f')
        datetime_str = params.get('d')
        retry_count = params.get('r', '0')
        source = params.get('s', '')
        
        # Log raw parameters
        logger.info(f"Raw params: {dict(params)}")
        
        # Handle boot notifications
        if source and 'boot' in source.lower():
            logger.info(f"Boot notification from device: {source}")
            print("\n" + "🚀"*20)
            print("🔄 SYSTEM BOOT NOTIFICATION")
            print("🚀"*20)
            print(f"📱 Device: {source}")
            print(f"🕒 Boot Time: {datetime_str}")
            print(f"🔄 Previous Failures: {retry_count}")
            print(f"🌐 From IP: {request.remote_addr}")
            print(f"⏰ Server Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("🚀"*20 + "\n")
            return jsonify({"status": "BOOT_ACK", "message": "Boot notification received"}), 200
        
        # Validate required fields
        missing_fields = []
        if not voltage: missing_fields.append('v (voltage)')
        if not current: missing_fields.append('c (current)')
        if not kwh: missing_fields.append('k (kWh)')
        
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            logger.error(error_msg)
            return jsonify({"error": error_msg}), 400
        
        # Display meter data with enhanced formatting
        print("\n" + "⚡"*60)
        print("🔌 SMART ENERGY METER DATA RECEIVED")
        print("⚡"*60)
        print(f"📊 Voltage      : {voltage}V")
        print(f"⚡ Current      : {current}A") 
        print(f"📈 Power Factor : {power_factor}")
        print(f"🔋 Load         : {load_kw}kW")
        print(f"📋 Total kWh    : {kwh}")
        print(f"🌊 Frequency    : {frequency}Hz")
        print(f"🕒 DateTime     : {datetime_str}")
        print(f"🔄 Retry Count  : {retry_count}")
        print(f"🏷️  Source       : {source}")
        print(f"🌐 From IP      : {request.remote_addr}")
        print(f"⏰ Server Time  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("⚡"*60)
        
        # Validate and convert numeric data
        try:
            # Voltage validation (0-500V)
            volt_val = float(voltage) if voltage else None
            if volt_val is not None and (volt_val < 0 or volt_val > 500):
                raise ValueError(f"Voltage {volt_val}V out of range (0-500V)")
                
            # Current validation (0-1000A)
            curr_val = float(current) if current else None
            if curr_val is not None and (curr_val < 0 or curr_val > 1000):
                raise ValueError(f"Current {curr_val}A out of range (0-1000A)")
                
            # Power factor validation (0-1)
            pf_val = float(power_factor) if power_factor else None
            if pf_val is not None and (pf_val < 0 or pf_val > 1):
                raise ValueError(f"Power Factor {pf_val} out of range (0-1)")
                
            # Load validation (>= 0)
            load_val = float(load_kw) if load_kw else None
            if load_val is not None and load_val < 0:
                raise ValueError(f"Load {load_val}kW cannot be negative")
                
            # kWh validation (>= 0)
            kwh_val = float(kwh) if kwh else None
            if kwh_val is not None and kwh_val < 0:
                raise ValueError(f"kWh {kwh_val} cannot be negative")
                
            # Frequency validation (45-65Hz)
            freq_val = float(frequency) if frequency else None
            if freq_val is not None and (freq_val < 45 or freq_val > 65):
                raise ValueError(f"Frequency {freq_val}Hz out of range (45-65Hz)")
            
            # Retry count validation
            retry_val = int(retry_count) if retry_count else 0
            
            print("✅ Data validation PASSED")
            logger.info("Data validation successful")
            
        except (ValueError, TypeError) as e:
            error_msg = f"Invalid data format: {str(e)}"
            print(f"❌ Data validation FAILED: {error_msg}")
            logger.error(error_msg)
            return jsonify({"error": error_msg}), 400
        
        # Save to database
        try:
            reading_id = db_manager.insert_reading(
                voltage=volt_val,
                current=curr_val,
                power_factor=pf_val,
                load_kw=load_val,
                kwh=kwh_val,
                frequency=freq_val,
                datetime_str=datetime_str,
                retry_count=retry_val,
                source=source
            )
            
            print(f"💾 Data saved to database with ID: {reading_id}")
            logger.info(f"Data saved successfully with ID: {reading_id}")
            
        except Exception as e:
            error_msg = f"Database error: {str(e)}"
            print(f"🔥 DATABASE ERROR: {error_msg}")
            logger.error(error_msg)
            return jsonify({"error": error_msg}), 500
        
        # Success response
        print("✅ Data processed and stored successfully\n")
        logger.info("Request processed successfully")
        
        return jsonify({
            "status": "OK",
            "message": "Data received and stored",
            "reading_id": reading_id,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        error_msg = f"Server error: {str(e)}"
        print(f"🔥 EXCEPTION: {error_msg}")
        logger.error(f"Unexpected error: {error_msg}")
        return jsonify({"error": error_msg}), 500

@app.route('/api/data', methods=['GET'])
def get_data():
    """Retrieve stored meter readings as JSON"""
    try:
        # Get query parameters for filtering
        source = request.args.get('source')
        limit = request.args.get('limit', 1000, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Fetch data from database
        readings = db_manager.get_readings(
            source=source,
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify({
            "status": "success",
            "count": len(readings),
            "data": readings
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/export', methods=['GET'])
def export_data():
    """Export meter readings as CSV"""
    try:
        # Get query parameters
        source = request.args.get('source')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Fetch data
        readings = db_manager.get_readings(
            source=source,
            start_date=start_date,
            end_date=end_date
        )
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'id', 'voltage', 'current', 'power_factor', 'load_kw', 'kwh',
            'frequency', 'datetime_str', 'retry_count', 'source', 'received_at'
        ])
        
        writer.writeheader()
        for reading in readings:
            writer.writerow(reading)
        
        # Create file-like object for download
        output.seek(0)
        
        # Generate filename with timestamp
        filename = f"meter_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get database statistics and system info"""
    try:
        stats = db_manager.get_statistics()
        return jsonify({
            "status": "success",
            "statistics": stats,
            "server_time": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """System health check"""
    try:
        # Check database connection
        db_status = db_manager.health_check()
        
        # Get system info
        uptime = datetime.now() - app.config.get('START_TIME', datetime.now())
        
        return jsonify({
            "status": "healthy" if db_status else "degraded",
            "timestamp": datetime.now().isoformat(),
            "server": "Smart Energy Meter Data Receiver",
            "version": "1.0.0",
            "uptime_seconds": int(uptime.total_seconds()),
            "database": "connected" if db_status else "error",
            "endpoints": {
                "/meter": "POST/GET - Receive meter data",
                "/api/data": "GET - Retrieve stored data",
                "/api/export": "GET - Export data as CSV",
                "/api/stats": "GET - Database statistics",
                "/health": "GET - Health check",
                "/test": "GET - Test endpoint"
            },
            "expected_params": {
                "v": "voltage (float) - Volts",
                "c": "current (float) - Amperes", 
                "pf": "power_factor (float) - 0-1",
                "l": "load_kw (float) - Kilowatts",
                "k": "kwh (float) - Kilowatt-hours",
                "f": "frequency (float) - Hertz",
                "d": "datetime (string) - Device timestamp",
                "r": "retry_count (integer) - Retry attempts",
                "s": "source (string) - Device identifier"
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }), 500

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint with sample data"""
    return jsonify({
        "message": "Smart Energy Meter Server is running",
        "timestamp": datetime.now().isoformat(),
        "sample_urls": {
            "GET": "/meter?v=230.5&c=8.750&pf=0.92&l=2.01560&k=1250.75&f=50.2&d=26-07-2025%2013:05:30&r=0&s=atmega328pb",
            "POST": "/meter (with form data)"
        },
        "api_endpoints": {
            "data": "/api/data?source=atmega328pb&limit=100",
            "export": "/api/export?start_date=2025-07-01&end_date=2025-07-31",
            "stats": "/api/stats"
        }
    }), 200

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 error: {request.url}")
    return jsonify({
        "error": "Endpoint not found",
        "message": "Use GET /meter with query parameters or POST /meter with form data",
        "available_endpoints": ["/meter", "/api/data", "/api/export", "/health", "/test"],
        "example": "/meter?v=230&c=8.5&k=1250&pf=0.92&l=2.0&f=50.2&d=26-07-2025%2013:05:30&r=0&s=atmega328pb"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    logger.warning(f"405 error: {request.method} to {request.url}")
    return jsonify({
        "error": f"Method {request.method} not allowed",
        "message": "Check the documentation for allowed methods",
        "allowed_methods": ["GET", "POST"]
    }), 405

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"500 error: {str(error)}")
    return jsonify({
        "error": "Internal server error",
        "message": "Please check the server logs for more details"
    }), 500

if __name__ == '__main__':
    # Set start time for uptime calculation
    app.config['START_TIME'] = datetime.now()
    
    # Ensure directories exist
    os.makedirs('data/logs', exist_ok=True)
    
    # Initialize database
    db_manager.init_database()
    
    print("🚀 Starting Smart Energy Meter Data Server...")
    print("📡 Listening for meter data on /meter endpoint (GET/POST)")
    print("🔗 API endpoints available:")
    print("   📊 /api/data - Retrieve stored data")
    print("   📤 /api/export - Export data as CSV")
    print("   📈 /api/stats - Database statistics")
    print("   🏥 /health - Health check")
    print("   🧪 /test - Test endpoint")
    print("💡 Expected URL format:")
    print("   /meter?v=230.5&c=8.750&pf=0.92&l=2.01560&k=1250.75&f=50.2&d=26-07-2025%2013:05:30&r=0&s=atmega328pb")
    print("⚙️  Parameter mapping:")
    print("   v  = voltage (V)")
    print("   c  = current (A)")
    print("   pf = power factor")
    print("   l  = load (kW)")
    print("   k  = kWh total")
    print("   f  = frequency (Hz)")
    print("   d  = datetime")
    print("   r  = retry count") 
    print("   s  = source device")
    print(f"🌐 Server starting on http://0.0.0.0:{app.config['PORT']}")
    
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )