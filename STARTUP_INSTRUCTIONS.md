# How to Start the Stellar Backend Server

## ✅ Fixed Import Issues

The import errors have been resolved. The backend can now be run directly.

## 🚀 Three Ways to Start the Server

### Method 1: Using run.py (Recommended)

```bash
cd /Users/rezaakbari/PycharmProjects/Stellar/backend
python run.py
```

**Benefits**:
- Clean startup with banner
- Configurable via command-line arguments
- Shows API docs URL

**Options**:
```bash
python run.py --port 8080        # Custom port
python run.py --no-reload        # Disable auto-reload
python run.py --log-level debug  # Debug logging
python run.py --help             # Show all options
```

---

### Method 2: Direct Execution

```bash
cd /Users/rezaakbari/PycharmProjects/Stellar/backend
python main.py
```

**Benefits**:
- Simple and direct
- Uses settings from .env file

---

### Method 3: Using Uvicorn Module

```bash
cd /Users/rezaakbari/PycharmProjects/Stellar/backend
python -m uvicorn main:app --reload --port 8000
```

**Benefits**:
- Standard uvicorn approach
- Full uvicorn command-line options

---

## 📋 Prerequisites

Before running the server, ensure:

1. **Dependencies are installed**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Environment file exists** (`backend/.env`):
   ```env
   SECRET_KEY=your-secret-key-change-in-production
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   CORS_ORIGINS=http://localhost:3000
   ```

---

## ✅ Verify It's Working

### 1. Check the console output:
```
🚀 Stellar Backend Server
============================================================
Starting server at http://0.0.0.0:8000
API docs: http://localhost:8000/docs
Health check: http://localhost:8000/health
============================================================

INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Test health endpoint:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"healthy"}
```

### 3. Open API docs in browser:
```
http://localhost:8000/docs
```

---

## 🔧 What Was Fixed

### Problem:
```python
from .core.config import settings  # Relative imports failed
```

### Solution:
```python
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from core.config import settings  # Now works!
```

**Changed**:
- ✅ Updated `main.py` to use absolute imports
- ✅ Added Python path setup at the top of `main.py`
- ✅ Created `run.py` startup script with better UX
- ✅ Updated README with correct commands
- ✅ Created QUICKSTART.md guide

---

## 📁 Updated Files

1. **backend/main.py** - Fixed imports, now works as standalone script
2. **backend/run.py** - New startup script with CLI options
3. **README.md** - Updated with correct startup commands
4. **QUICKSTART.md** - New comprehensive setup guide

---

## 🎯 Next Steps

1. **Start the backend**:
   ```bash
   cd backend
   python run.py
   ```

2. **Start the frontend** (in another terminal):
   ```bash
   cd frontend
   npm install  # First time only
   npm start
   ```

3. **Test the API**:
   - Open http://localhost:8000/docs
   - Try the `/health` endpoint
   - Login with Instagram credentials

---

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'fastapi'"
**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Error: "No module named 'core'"
**Solution**: Make sure you're in the `backend` directory when running
```bash
cd /Users/rezaakbari/PycharmProjects/Stellar/backend
python run.py
```

### Error: Port 8000 already in use
**Solution**: Use a different port
```bash
python run.py --port 8080
```

---

## 📚 Documentation

- **Quick Start**: `QUICKSTART.md`
- **Full README**: `README.md`
- **Frontend README**: `frontend/README.md`
- **API Docs**: http://localhost:8000/docs (when server is running)

---

**You're all set!** 🎉

The server is ready to run. Just execute `python run.py` from the backend directory.
