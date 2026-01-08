# Stellar - Quick Start Guide

Get the Stellar Instagram Downloader running in 5 minutes!

## Prerequisites

- Python 3.10+ installed
- Node.js 16+ and npm installed
- Instagram account (for authentication)

## Step 1: Backend Setup (2 minutes)

### 1.1 Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This will install:
- FastAPI (web framework)
- Uvicorn (ASGI server)
- Pydantic (data validation)
- python-jose (JWT tokens)
- aiograpi (Instagram API)
- moviepy (video processing)
- And other dependencies

### 1.2 Create Environment File

Create a `.env` file in the `backend/` directory:

```bash
# backend/.env
SECRET_KEY=your-secret-key-change-in-production-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://localhost:3000
```

**Note**: Generate a secure SECRET_KEY for production:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 1.3 Start the Backend Server

```bash
# Option 1: Using run script (recommended)
python run.py

# Option 2: Direct execution
python main.py

# Option 3: Using uvicorn
python -m uvicorn main:app --reload --port 8000
```

You should see:
```
🚀 Stellar Backend Server
============================================================
Starting server at http://0.0.0.0:8000
API docs: http://localhost:8000/docs
Health check: http://localhost:8000/health
============================================================

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Test it**: Open http://localhost:8000/docs in your browser

---

## Step 2: Frontend Setup (2 minutes)

### 2.1 Install Node Dependencies

Open a **new terminal window** and run:

```bash
cd frontend
npm install
```

This will install:
- React 18
- TypeScript
- React Router
- Axios (HTTP client)
- React Query (server state)
- And other dependencies

### 2.2 Create Environment File

Create a `.env` file in the `frontend/` directory:

```bash
# frontend/.env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
REACT_APP_API_PREFIX=/api/v1
```

### 2.3 Start the Frontend Dev Server

```bash
npm start
```

You should see:
```
Compiled successfully!

You can now view stellar-frontend in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://192.168.1.x:3000

Note that the development build is not optimized.
To create a production build, use npm run build.

webpack compiled successfully
```

The browser will automatically open http://localhost:3000

---

## Step 3: Test the API (1 minute)

### 3.1 Check Health Endpoint

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"healthy"}
```

### 3.2 Explore API Documentation

Open http://localhost:8000/docs in your browser to see:
- Interactive API documentation
- All available endpoints
- Request/response schemas
- Try out endpoints directly

---

## Running Both Servers Together (Optional)

Install `concurrently` to run both servers in one terminal:

```bash
# Install globally
npm install -g concurrently

# From project root
cd ..  # Back to Stellar directory
concurrently "cd backend && python run.py" "cd frontend && npm start"
```

This will start both backend and frontend simultaneously.

---

## Common Issues & Solutions

### Issue: "ModuleNotFoundError: No module named 'fastapi'"

**Solution**: Install backend dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Issue: "npm: command not found"

**Solution**: Install Node.js from https://nodejs.org/

### Issue: "Cannot connect to backend from frontend"

**Solution**:
1. Ensure backend is running on port 8000
2. Check CORS settings in `backend/.env`
3. Verify frontend `.env` has correct API_URL

### Issue: "MoviePy video build fails"

**Solution**: Install ffmpeg
- macOS: `brew install ffmpeg`
- Linux: `sudo apt-get install ffmpeg`
- Windows: Download from https://ffmpeg.org/download.html

### Issue: "Instagram login fails"

**Solution**:
1. Check credentials are correct
2. Enter 2FA code if required
3. Complete any Instagram challenges in browser first
4. Instagram may rate-limit - wait a few minutes

---

## Next Steps

1. **Login to Instagram** via the API
   - POST http://localhost:8000/api/v1/auth/login
   - See docs for request format

2. **Test WebSocket Connection**
   ```bash
   cd backend
   python test_websocket.py <your_jwt_token>
   ```

3. **Try the Frontend** (Phase 6-7 implementation in progress)
   - Sign in page
   - Dashboard
   - Highlight management

---

## Useful Commands

### Backend

```bash
# Run server
python run.py

# Run with custom port
python run.py --port 8080

# Run without auto-reload
python run.py --no-reload

# Run with debug logging
python run.py --log-level debug
```

### Frontend

```bash
# Start dev server
npm start

# Build for production
npm run build

# Run tests
npm test
```

---

## Project Structure Overview

```
Stellar/
├── backend/              # Python FastAPI backend
│   ├── api/             # REST + WebSocket endpoints
│   ├── app/             # Application layer
│   ├── core/            # Config & security
│   ├── main.py          # App entry point
│   ├── run.py           # Startup script
│   └── requirements.txt # Dependencies
├── frontend/            # React TypeScript frontend
│   ├── src/             # Source code
│   ├── public/          # Static files
│   └── package.json     # Dependencies
└── data/                # Data storage
```

---

## Getting Help

- **API Docs**: http://localhost:8000/docs
- **Backend README**: `backend/README.md` (to be created)
- **Frontend README**: `frontend/README.md`
- **Full README**: `README.md`

---

**Happy coding!** 🚀

If you encounter any issues, check the troubleshooting section in the main README.md
