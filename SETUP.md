# Quick Setup Guide

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

## Installation Steps

### 1. Create Virtual Environment

```bash
cd backend
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

```bash
# Copy example file
cp .env.example .env

# Edit .env and add your configuration
# At minimum, set DATABASE_PATH
```

### 4. Initialize Database

```bash
python scripts/init_db.py
```

This will create the SQLite database with all required tables.

### 5. Run the Server

```bash
python run.py
```

Or using uvicorn directly:

```bash
uvicorn api.main:app --reload --port 8000
```

The API will be available at `http://127.0.0.1:8000`

### 6. Test the API

Open your browser or use curl:

```bash
# Health check
curl http://127.0.0.1:8000/api/v1/health

# List datasets (will be empty initially)
curl http://127.0.0.1:8000/api/v1/datasets
```

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Next Steps

1. Upload a CSV file via the `/api/v1/datasets` endpoint
2. Query analytics endpoints to see computed metrics
3. Check the `data/` directory for database and cache files

## Troubleshooting

### Database errors
- Make sure `data/` directory exists and is writable
- Run `python scripts/init_db.py` again to reset database

### Import errors
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt` again

### Port already in use
- Change `API_PORT` in `.env` file
- Or kill the process using port 8000
