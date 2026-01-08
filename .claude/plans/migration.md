# Stellar migration plan (PyQt/QtPy → client/server)

## Goal
Replace the legacy PyQt desktop app workflow with:
- FastAPI backend (auth, highlight/user workflows, background tasks, WebSocket progress)
- React frontend (auth UI, dashboard UI, real-time progress)

## Status
- ✅ Phase 1–5: Backend foundation → WebSockets → Frontend setup (routing, API client, contexts)
- ✅ Phase 6: Frontend authentication UI (sign-in + 2FA + routing guards + toast UX)
- 🚧 Phase 7: Full dashboard/user pages (polish + complete UI coverage)

## Remaining work (recommended next)
1. Dashboard expansion
   - Add “Users” section (track users, list highlights, start downloads)
   - Add project detail view (single project page + progress log)
2. UX polish
   - Consistent component library (buttons/inputs/cards), loading/error states
   - Better empty states and validation
3. Operational cleanup
   - Replace/remove legacy `run.sh` QtPy launcher if no longer needed
   - Confirm backend bind host/port and CORS defaults for local dev

