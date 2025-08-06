# Smart Energy Dashboard - Complete Project Structure

## 📁 Project Folder Structure

```
smart-energy-dashboard/
├── 📁 backend/                    # Flask API server
│   ├── app.py                     # Main Flask application
│   ├── database.py                # Database utilities
│   ├── config.py                  # Configuration settings
│   └── requirements.txt           # Python dependencies
│
├── 📁 dashboard/                  # Streamlit dashboard
│   ├── app.py                     # Main dashboard entry point
│   ├── utils.py                   # Shared utilities
│   ├── pages/                     # Dashboard pages
│   │   ├── 1_📊_Live_Dashboard.py
│   │   ├── 2_🧾_Raw_Data_Log.py
│   │   ├── 3_📈_Analytics.py
│   │   └── 4_⚙️_Settings.py
│   ├── .streamlit/                # Streamlit configuration
│   │   └── config.toml            # Green theme
│   └── requirements.txt           # Streamlit dependencies
│
├── 📁 data/                       # Database and logs
│   ├── meter_data.db              # SQLite database (auto-created)
│   └── logs/                      # Application logs
│       ├── flask_app.log
│       └── dashboard.log
│
├── 📁 docs/                       # Documentation
│   ├── README.md                  # Project documentation
│   ├── API.md                     # API documentation
│   └── DEPLOYMENT.md              # Deployment guide
│
├── 📁 scripts/                    # Utility scripts
│   ├── start_backend.py           # Start Flask server
│   ├── start_dashboard.py         # Start Streamlit dashboard
│   ├── test_data_generator.py     # Generate test data
│   └── backup_database.py         # Database backup utility
│
├── 📁 config/                     # Configuration files
│   ├── development.conf
│   ├── production.conf
│   └── logging.conf
│
├── docker-compose.yml             # Docker setup (optional)
├── Dockerfile                     # Docker image (optional)
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore rules
└── requirements.txt               # Root dependencies
```

## 🚀 Quick Start

### 1. Backend Setup (Flask API)
```bash
cd backend/
pip install -r requirements.txt
python app.py
```

### 2. Dashboard Setup (Streamlit)
```bash
cd dashboard/
pip install -r requirements.txt
streamlit run app.py
```

### 3. Access Points
- **Flask API**: http://localhost:8080
- **Streamlit Dashboard**: http://localhost:8501
- **Health Check**: http://localhost:8080/health
- **Test Endpoint**: http://localhost:8080/test

## 📊 API Endpoints

### POST/GET `/meter`
Receive energy meter data with parameters:
- `v` - Voltage (V)
- `c` - Current (A)  
- `pf` - Power Factor
- `l` - Load (kW)
- `k` - Total kWh
- `f` - Frequency (Hz)
- `d` - DateTime string
- `r` - Retry count
- `s` - Source device

### GET `/health`
System health check and status

### GET `/test`
Test endpoint with sample data URL

### GET `/api/data`
Retrieve stored meter readings (JSON)

### GET `/api/export`
Export data as CSV

## 🛡️ Security Features

- Input validation and sanitization
- SQL injection prevention
- Rate limiting (configurable)
- Error handling and logging
- Data backup utilities

## 📈 Dashboard Features

- **Live Metrics**: Real-time energy parameters
- **Carbon Footprint**: Emission calculations
- **Interactive Charts**: Historical trends
- **Data Export**: CSV download
- **Multi-device Support**: Source filtering
- **Auto-refresh**: 10-second updates
- **Responsive Design**: Mobile-friendly

## 🔧 Configuration

Environment variables in `.env`:
```bash
FLASK_ENV=development
DATABASE_PATH=data/meter_data.db
LOG_LEVEL=INFO
REFRESH_INTERVAL=10
EMISSION_FACTOR=0.82
```

## 📱 IoT Device Integration

Compatible with ATmega328PB + SIMCOM A7672S setup.
Expected data format:
```
/meter?v=230.5&c=8.750&pf=0.92&l=2.01560&k=1250.75&f=50.2&d=26-07-2025%2013:05:30&r=0&s=atmega328pb
```