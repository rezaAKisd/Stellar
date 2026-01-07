# Stellar - Instagram Highlight Downloader

Modern client-server application for downloading and managing Instagram highlights with real-time progress updates.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![React](https://img.shields.io/badge/React-18-blue.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5-blue.svg)

## 🏗️ Architecture

**Backend**: Python FastAPI server with Clean Architecture
**Frontend**: React.js SPA with TypeScript
**Communication**: REST API + WebSocket for real-time updates

## ✨ Features

### Completed (Phases 1-5)

✅ **Backend API** (FastAPI)
- Authentication with JWT tokens
- Instagram login with 2FA support
- Link-based highlight management (add, download, build video)
- Username-based user tracking (add, load highlights, download)
- Background tasks for long operations
- Real-time WebSocket progress updates
- Static file serving for media

✅ **Frontend Foundation** (React.js)
- Project structure with TypeScript
- API client with Axios interceptors
- Context providers (Auth, Toast, WebSocket)
- Custom hooks for easy state access
- Basic routing setup
- Global styles with design system

### In Progress

🚧 **Phase 6-7**: Frontend UI components and pages
- Sign in and 2FA pages
- Dashboard with tabs
- Highlight and user management UI
- Real-time progress indicators

### Upcoming

⏳ **Phase 8**: Real-time updates integration
⏳ **Phase 9**: Styling and polish
⏳ **Phase 10**: Testing and error handling
⏳ **Phase 11**: Deployment and DevOps

## 📁 Project Structure

```
Stellar/
├── backend/                 # Python FastAPI backend
│   ├── api/                # API layer (routes, websockets, schemas)
│   │   ├── routes/         # REST endpoints
│   │   ├── websockets/     # WebSocket handlers
│   │   ├── dependencies.py # FastAPI dependencies
│   │   └── schemas.py      # Pydantic models
│   ├── app/                # Application layer
│   │   ├── domain/        # Business entities
│   │   ├── application/   # Use cases
│   │   └── infrastructure/ # External services
│   ├── core/               # Core config
│   │   ├── config.py      # Settings
│   │   ├── security.py    # JWT auth
│   │   └── middleware.py  # CORS, etc.
│   ├── main.py             # FastAPI entry point
│   └── requirements.txt    # Backend dependencies
├── frontend/               # React.js frontend
│   ├── src/
│   │   ├── api/           # API client layer
│   │   ├── components/    # React components
│   │   ├── context/       # Context providers
│   │   ├── hooks/         # Custom hooks
│   │   ├── pages/         # Page components
│   │   ├── types/         # TypeScript types
│   │   └── utils/         # Utilities
│   ├── public/
│   └── package.json
└── data/                   # Data directory (downloads, exports)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 16+ and npm
- Instagram account (for authentication)

### Backend Setup

1. Install Python dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Create `.env` file in `backend/`:
```env
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://localhost:3000
```

3. Run the backend server:
```bash
uvicorn main:app --reload --port 8000
```

Backend will run at **http://localhost:8000**

API docs available at **http://localhost:8000/docs**

### Frontend Setup

1. Install Node dependencies:
```bash
cd frontend
npm install
```

2. Create `.env` file in `frontend/`:
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
REACT_APP_API_PREFIX=/api/v1
```

3. Run the frontend dev server:
```bash
npm start
```

Frontend will open at **http://localhost:3000**

### Run Both Servers (Recommended)

```bash
# Install concurrently globally
npm install -g concurrently

# From project root
concurrently "cd backend && uvicorn main:app --reload" "cd frontend && npm start"
```

## 📡 API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login with Instagram credentials
- `POST /api/v1/auth/verify-2fa` - Verify 2FA code
- `POST /api/v1/auth/logout` - Logout current session
- `GET /api/v1/auth/me` - Get current user info
- `POST /api/v1/auth/restore-session` - Restore Instagram session

### Highlights (Link-based)
- `POST /api/v1/highlights/add-link` - Add highlight by URL
- `GET /api/v1/highlights/projects` - Get all projects
- `GET /api/v1/highlights/{project_id}/status` - Get project status
- `POST /api/v1/highlights/{project_id}/download` - Start download
- `POST /api/v1/highlights/{project_id}/build-video` - Build video
- `DELETE /api/v1/highlights/{project_id}` - Delete project

### Users (Username-based)
- `POST /api/v1/users/add` - Add user to track
- `GET /api/v1/users` - Get all tracked users
- `GET /api/v1/users/{username}/highlights` - Load user highlights
- `POST /api/v1/users/{username}/highlights/{highlight_id}/download` - Download highlight
- `DELETE /api/v1/users/{user_id}` - Delete user

### WebSocket
- `WS /ws/progress?token=<jwt_token>` - Real-time progress updates

## 🧪 Testing

### Backend Testing

Test API endpoints using the interactive docs:
```
http://localhost:8000/docs
```

Test WebSocket connection:
```bash
cd backend
python test_websocket.py <your_jwt_token>
```

Get JWT token by logging in via the API first.

### Frontend Testing

```bash
cd frontend
npm test
```

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation
- **python-jose** - JWT tokens
- **aiograpi** - Instagram API
- **moviepy** - Video processing
- **WebSockets** - Real-time updates

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **React Router** - Routing
- **React Query** - Server state
- **Axios** - HTTP client
- **Context API** - Global state

## 🏛️ Architecture Principles

### Clean Architecture (Backend)

```
API Layer → Application Layer → Domain Layer
              ↓
       Infrastructure Layer
```

- **Domain**: Pure business logic (entities, value objects)
- **Application**: Use cases orchestrating business logic
- **Infrastructure**: External services (Instagram, file storage)
- **API**: HTTP endpoints and WebSocket handlers

### Component-Based (Frontend)

- Pages for routes
- Reusable components
- Custom hooks for logic
- Context for global state
- API client for server communication

## 🔐 Security & Privacy

- **JWT Authentication**: Stateless token-based auth
- **Session Storage**: Instagram sessions saved locally
- **No Password Storage**: Only session tokens, never passwords
- **Local Processing**: All downloads and processing happen locally
- **CORS**: Configured for localhost development

## 🐛 Troubleshooting

### Backend Issues

**Dependencies not installed**:
```bash
cd backend
pip install -r requirements.txt
```

**Instagram login fails**:
- Check credentials
- Enter 2FA code if required
- Complete any Instagram challenges in browser first

**MoviePy video build fails**:
Install ffmpeg:
- macOS: `brew install ffmpeg`
- Linux: `sudo apt-get install ffmpeg`
- Windows: Download from https://ffmpeg.org/download.html

### Frontend Issues

**Dependencies not installed**:
```bash
cd frontend
npm install
```

**Cannot connect to backend**:
- Ensure backend is running on port 8000
- Check CORS settings in backend
- Verify `.env` file has correct API URL

**WebSocket connection fails**:
- Ensure you're logged in (have JWT token)
- Check WebSocket URL in `.env`
- Backend should be running

## 📝 Development

### Code Style

**Backend**: PEP 8, type hints
**Frontend**: ESLint, Prettier (to be configured)

### Git Workflow

- `main` - Production-ready code
- `dev` - Development branch (current)
- Feature branches - New features

## 📖 Documentation

- **Backend README**: `backend/README.md` (to be created)
- **Frontend README**: `frontend/README.md` (created)
- **API Docs**: http://localhost:8000/docs (auto-generated)

## 🗺️ Migration Plan

This project was migrated from a PyQt desktop application to a modern client-server architecture. See the migration plan in `.claude/plans/` for detailed implementation phases.

**Completed Phases**:
- Phase 1: Backend Foundation
- Phase 2: Authentication API
- Phase 3: Core API Endpoints
- Phase 4: WebSocket Real-time Updates
- Phase 5: Frontend Setup

**Next Phase**: Phase 6 - Frontend Authentication UI

## 🤝 Contributing

This is a private project. For issues or questions, contact the maintainer.

## ⚠️ Disclaimer

This tool is for personal use only. Make sure you have the rights to download any content you access through Instagram. Always respect content creators' rights and Instagram's Terms of Service.

## 📜 License

Private project - Educational/Personal use only

## 🙏 Acknowledgments

- **aiograpi** - Excellent Instagram API client
- **moviepy** - Powerful video editing library
- **FastAPI** - Modern Python web framework
- **React** - UI library

---

**Built with** ❤️ **using Python + FastAPI + React.js**

For questions or issues, please check the troubleshooting section above.
