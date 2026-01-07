# Stellar Frontend

React.js frontend for the Stellar Instagram Highlight Downloader application.

## Tech Stack

- **React 18** with TypeScript
- **React Router** for routing
- **React Query** for server state management
- **Axios** for HTTP requests
- **WebSockets** for real-time progress updates
- **Context API** for global state (auth, toast, WebSocket)

## Project Structure

```
src/
├── api/              # API client layer
│   ├── client.ts     # Axios instance with interceptors
│   ├── auth.ts       # Auth API calls
│   ├── highlights.ts # Highlights API calls
│   ├── users.ts      # Users API calls
│   └── websocket.ts  # WebSocket client
├── components/       # React components (to be added in Phase 6-7)
├── context/          # React Context providers
│   ├── AuthContext.tsx
│   ├── ToastContext.tsx
│   └── WebSocketContext.tsx
├── hooks/            # Custom React hooks
│   ├── useAuth.ts
│   ├── useToast.ts
│   └── useWebSocket.ts
├── pages/            # Page components (to be added in Phase 6-7)
├── types/            # TypeScript type definitions
│   ├── auth.ts
│   ├── highlight.ts
│   ├── user.ts
│   └── websocket.ts
├── utils/            # Utility functions
│   ├── storage.ts    # localStorage utilities
│   └── formatters.ts # Formatting functions
├── App.tsx           # Main app component with routing
├── App.css           # App styles
├── index.tsx         # React entry point
└── index.css         # Global styles
```

## Environment Variables

Create a `.env` file in the `frontend/` directory:

```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
REACT_APP_API_PREFIX=/api/v1
```

## Getting Started

### Prerequisites

- Node.js 16+ and npm

### Installation

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Create `.env` file (see above)

3. Start development server:
```bash
npm start
```

The app will open at [http://localhost:3000](http://localhost:3000)

## Available Scripts

- `npm start` - Run development server
- `npm build` - Build for production
- `npm test` - Run tests
- `npm run eject` - Eject from Create React App (not recommended)

## Development Notes

### Phase 5 Status (Complete)

✅ Project structure created
✅ TypeScript configuration
✅ API client with Axios interceptors
✅ Context providers (Auth, Toast, WebSocket)
✅ Custom hooks
✅ Basic routing setup
✅ Global styles with CSS variables

### Next Steps (Phase 6-7)

- Sign In page and 2FA page
- Dashboard with Link and Username tabs
- User detail page
- Component library (buttons, inputs, cards, etc.)
- Toast notification UI

## API Integration

The frontend communicates with the FastAPI backend at `http://localhost:8000`:

### Authentication Flow

1. User enters credentials → `POST /api/v1/auth/login`
2. If 2FA required → `POST /api/v1/auth/verify-2fa`
3. JWT token stored in localStorage
4. All subsequent requests include `Authorization: Bearer <token>` header
5. WebSocket connects with token: `ws://localhost:8000/ws/progress?token=<token>`

### Real-time Updates

The WebSocket connection receives progress updates:

```typescript
{
  type: "download_progress" | "export_progress" | "task_complete" | "error",
  project_id: "uuid",
  progress: 0.0-1.0,  // Optional
  status: "downloading" | "building" | "downloaded" | "exported",  // Optional
  message: "Error message"  // Optional
}
```

## Architecture

### State Management

- **Server State**: React Query for API data (projects, users, highlights)
- **Global State**: Context API for auth, toast, WebSocket
- **Local State**: useState for component-specific state

### API Client

Axios instance with interceptors:
- Request: Automatically adds JWT token to headers
- Response: Handles 401 errors (redirect to sign in)

### WebSocket Client

Custom WebSocket client with:
- Auto-reconnect with exponential backoff
- Subscription-based messaging
- Project-specific and global listeners

### Authentication

JWT-based authentication:
- Token stored in localStorage
- Auth context provides login/logout/session restoration
- Protected routes redirect to sign in if not authenticated

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

Private project
