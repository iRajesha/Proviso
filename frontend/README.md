# Proviso React Frontend

React implementation of the Proviso wireframe:
- Chat-driven infrastructure requirement capture
- Terraform editor
- Backend integration with Proviso FastAPI

## Tech

- React 18
- Vite 5

## Run

From repository root:

```bash
cd frontend
npm install
npm run dev
```

App URL:
- `http://localhost:5173`

Backend expectation:
- FastAPI backend running on `http://localhost:8000`
- Vite proxy forwards `/api/*` calls to backend

## Implemented API Integration

- `POST /api/v1/chat/sessions`
  - Creates an inline-memory chat session
  - Stores temporary context on backend (process-local)

- `GET /api/v1/chat/sessions/{session_id}`
  - Fetches current session state (messages + generated artifacts)

- `POST /api/v1/chat/sessions/{session_id}/messages`
  - Sends user message with intent (`auto`, `generate`, `refine`, `review`, `cleanup`, `chat`)
  - `generate`: full Crew run
  - `refine`: updates existing Terraform draft
  - `review`: runs reviewer agent only when requested
  - `cleanup`: runs cleanup agent only when requested
  - `chat`: conversational OCI chat response with session context
  - Returns updated session state and optional clarification questions

- `POST /api/v1/review/diff`
  - Compares reviewed baseline and current editor content
  - Displays unified diff output and stats

## Notes

- Inline memory is temporary and resets when backend process restarts.
- Editor supports quick format and reset-to-reviewed actions.
