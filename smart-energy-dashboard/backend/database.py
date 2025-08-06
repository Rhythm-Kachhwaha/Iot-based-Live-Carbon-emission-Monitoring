# backend/database.py - Database Manager
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional
import threading

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles all database operations for the smart energy meter system"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.Lock()
        
    def init_database(self):
        """Initialize database and create tables if they don't exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create meter_readings table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS meter_readings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        voltage REAL,
                        current REAL,
                        power_factor REAL,
                        load_kw REAL,
                        kwh REAL,
                        frequency REAL,
                        datetime_str TEXT,
                        retry_count INTEGER DEFAULT 0,
                        source TEXT,
                        received_at TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for better query performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_meter_readings_received_at 
                    ON meter_readings(received_at)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_meter_readings_source 
                    ON meter_readings(source)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_meter_readings_datetime 
                    ON meter_readings(datetime_str)
                ''')
                
                # Create system_logs table for application logs
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        level TEXT NOT NULL,
                        message TEXT NOT NULL,
                        module TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create device_status table to track device health
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS device_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source TEXT NOT NULL,
                        last_seen TIMESTAMP,
                        status TEXT DEFAULT 'online',
                        boot_count INTEGER DEFAULT 0,
                        error_count INTEGER DEFAULT 0,
                        UNIQUE(source)
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def insert_reading(self, voltage=None, current=None, power_factor=None, 
                      load_kw=None, kwh=None, frequency=None, datetime_str=None,
                      retry_count=0, source=None) -> int:
        """Insert a new meter reading into the database"""
        
        with self.lock:
            try:
                received_at = datetime.now().isoformat()
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT INTO meter_readings 
                        (voltage, current, power_factor, load_kw, kwh, frequency, 
                         datetime_str, retry_count, source, received_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        voltage, current, power_factor, load_kw, kwh, frequency,
                        datetime_str, retry_count, source, received_at
                    ))
                    
                    reading_id = cursor.lastrowid
                    
                    # Update device status
                    cursor.execute('''
                        INSERT OR REPLACE INTO device_status 
                        (source, last_seen, status, error_count)
                        VALUES (?, ?, 'online', 
                                COALESCE((SELECT error_count FROM device_status WHERE source = ?), 0))
                    ''', (source, received_at, source))
                    
                    conn.commit()
                    logger.info(f"Inserted reading with ID: {reading_id}")
                    
                    return reading_id
                    
            except Exception as e:
                logger.error(f"Failed to insert reading: {str(e)}")
                raise
    
    def get_readings(self, source=None, limit=1000, start_date=None, end_date=None) -> List[Dict]:
        """Retrieve meter readings with optional filtering"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row  # Enable dict-like access
                cursor = conn.cursor()
                
                # Build query with filters
                query = "SELECT * FROM meter_readings WHERE 1=1"
                params = []
                
                if source and source != 'All':
                    query += " AND source = ?"
                    params.append(source)
                
                if start_date:
                    query += " AND date(received_at) >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND date(received_at) <= ?"
                    params.append(end_date)
                
                query += " ORDER BY received_at DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                readings = [dict(row) for row in rows]
                
                logger.info(f"Retrieved {len(readings)} readings")
                return readings
                
        except Exception as e:
            logger.error(f"Failed to get readings: {str(e)}")
            raise
    
    def get_latest_reading(self, source=None) -> Optional[Dict]:
        """Get the most recent reading, optionally filtered by source"""
        
        try:
            readings = self.get_readings(source=source, limit=1)
            return readings[0] if readings else None
            
        except Exception as e:
            logger.error(f"Failed to get latest reading: {str(e)}")
            return None
    
    def get_statistics(self) -> Dict:
        """Get database and system statistics"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total readings count
                cursor.execute("SELECT COUNT(*) FROM meter_readings")
                total_readings = cursor.fetchone()[0]
                
                # Readings by source
                cursor.execute("""
                    SELECT source, COUNT(*) as count 
                    FROM meter_readings 
                    GROUP BY source
                """)
                sources = dict(cursor.fetchall())
                
                # Readings in last 24 hours
                cursor.execute("""
                    SELECT COUNT(*) FROM meter_readings 
                    WHERE datetime(received_at) >= datetime('now', '-1 day')
                """)
                last_24h = cursor.fetchone()[0]
                
                # Latest reading timestamp
                cursor.execute("SELECT MAX(received_at) FROM meter_readings")
                latest_timestamp = cursor.fetchone()[0]
                
                # Average readings per hour (last 24h)
                avg_per_hour = round(last_24h / 24, 2) if last_24h > 0 else 0
                
                # Device status
                cursor.execute("SELECT source, status, last_seen FROM device_status")
                device_statuses = [
                    {"source": row[0], "status": row[1], "last_seen": row[2]}
                    for row in cursor.fetchall()
                ]
                
                # Database file size
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                db_size = cursor.fetchone()[0]
                
                return {
                    "total_readings": total_readings,
                    "sources": sources,
                    "last_24h_readings": last_24h,
                    "latest_timestamp": latest_timestamp,
                    "avg_readings_per_hour": avg_per_hour,
                    "device_statuses": device_statuses,
                    "database_size_bytes": db_size,
                    "database_size_mb": round(db_size / (1024 * 1024), 2)
                }
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {str(e)}")
            return {}
    
    def cleanup_old_data(self, days_to_keep=30):
        """Remove readings older than specified days"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM meter_readings 
                    WHERE datetime(received_at) < datetime('now', '-{} days')
                """.format(days_to_keep))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_count} old readings")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {str(e)}")
            raise
    
    def get_readings_by_date_range(self, start_date: str, end_date: str, source=None) -> List[Dict]:
        """Get readings within a specific date range"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM meter_readings 
                    WHERE date(received_at) BETWEEN ? AND ?
                """
                params = [start_date, end_date]
                
                if source and source != 'All':
                    query += " AND source = ?"
                    params.append(source)
                
                query += " ORDER BY received_at ASC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get readings by date range: {str(e)}")
            raise
    
    def log_system_event(self, level: str, message: str, module: str = None):
        """Log system events to database"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO system_logs (level, message, module)
                    VALUES (?, ?, ?)
                ''', (level, message, module))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to log system event: {str(e)}")
    
    def update_device_status(self, source: str, status: str, increment_boot=False, increment_error=False):
        """Update device status information"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current values
                cursor.execute("SELECT boot_count, error_count FROM device_status WHERE source = ?", (source,))
                result = cursor.fetchone()
                
                boot_count = (result[0] if result else 0) + (1 if increment_boot else 0)
                error_count = (result[1] if result else 0) + (1 if increment_error else 0)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO device_status 
                    (source, last_seen, status, boot_count, error_count)
                    VALUES (?, ?, ?, ?, ?)
                ''', (source, datetime.now().isoformat(), status, boot_count, error_count))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update device status: {str(e)}")
    
    def health_check(self) -> bool:
        """Check if database is accessible and healthy"""
        
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
                
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False
    
    def backup_database(self, backup_path: str):
        """Create a backup of the database"""
        
        try:
            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            
            logger.info(f"Database backed up to: {backup_path}")
            
        except Exception as e:
            logger.error(f"Failed to backup database: {str(e)}")
            raise