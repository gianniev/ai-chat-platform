# AI Chat Platform

## 🌎 Languages

- English (this document)
- [Español](README.es.md)

## Live Demo

Frontend: [https://ai-chat-platform.netlify.app](https://ai-chat-platform.netlify.app)

Backend API: [https://ai-chat-platform-production-e316.up.railway.app](https://ai-chat-platform-production-e316.up.railway.app)

API Docs: [https://ai-chat-platform-production-e316.up.railway.app/docs](https://ai-chat-platform-production-e316.up.railway.app/docs)

AI chat application for a portfolio project, built with Next.js, FastAPI, PostgreSQL, and Hugging Face.

The main experience works as a private demo per visitor: chats are stored in the browser's `localStorage` and are not mixed between users. PostgreSQL is used for anonymous metrics and feedback, not for storing private conversations.

## Stack

### Frontend

- Next.js 15
- React 19
- TypeScript
- Hugeicons
- Light/dark theme with preference stored in `localStorage`
- Local chats per browser
- Response feedback
- Favicon/logo based on `AiBrain01Icon`

### Backend

- Python 3.11
- FastAPI + Pydantic
- PostgreSQL + psycopg2
- Hugging Face Inference API
- Model: `meta-llama/Llama-3.1-8B-Instruct`
- Uvicorn

## Project Structure

```text
aichatbox/
├── ai-chat-backend/
├── ai-chat-frontend/
├── docker-compose.yml
├── README.md
└── README.es.md
```

## Ports

- Frontend Docker: `http://localhost:3003`
- Alternative local dev frontend: `http://localhost:3004`
- Backend: `http://localhost:18000`
- PostgreSQL: `localhost:15432`

## Run Everything With Docker

From the project root:

```bash
docker compose up -d --build
```

Next runs without rebuilding:

```bash
docker compose up -d
```

Stop services:

```bash
docker compose down
```

Rebuild only the backend after Python changes:

```bash
docker compose up -d --build backend
```

Rebuild only the frontend after Next.js changes:

```bash
docker compose up -d --build frontend
```

## Local Frontend Development

```bash
cd ai-chat-frontend
npm install
npm run dev
```

By default, the frontend runs on `3003`. If that port is already in use, run Next directly on another port:

```bash
./node_modules/.bin/next dev -p 3004
```

In local development, the Next API routes use this backend by default:

```text
http://localhost:18000
```

In Docker, `docker-compose.yml` defines:

```text
BACKEND_URL=http://backend:8000
```

## Backend Environment Variables

Expected file:

```text
ai-chat-backend/.env
```

Example:

```env
DATABASE_URL=postgresql://user:password@postgres:5432/chatdb
HF_TOKEN=your_huggingface_token
```

Do not commit real tokens to public repositories.

## Portfolio/Demo Mode

The frontend sends messages to `/api/chat` with:

```json
{
  "persist": false
}
```

With `persist: false`, the backend:

- generates the Hugging Face response through SSE streaming
- records anonymous metrics when the stream finishes
- does not create conversations in PostgreSQL
- does not store user messages
- does not store assistant responses

Visitor chats are stored only in:

```text
localStorage
```

This prevents different visitors from seeing or mixing each other's conversations.

## PostgreSQL Usage

PostgreSQL is used for anonymous portfolio data:

### `anonymous_chat_metrics`

Stores technical response data:

- mode (`demo`)
- model used
- estimated input tokens
- estimated output tokens
- latency
- whether the response was persisted
- date

It does not store chat text.

### `anonymous_feedback`

Stores anonymous feedback:

- rating: `up` or `down`
- anonymous local message id
- anonymous local chat id
- model
- optional comment
- date

It does not store prompts or responses.

## Main Endpoints

## API Endpoints

- `GET /` - API status
- `GET /health` - Health check
- `GET /health/db` - Database health check
- `POST /chat` - Send a chat message
- `POST /feedback` - Submit feedback
- `GET /analytics/summary` - Get usage analytics
- `GET /docs` - Swagger API documentation


### Chat

```text
POST /chat
```

Returns an SSE response (`text/event-stream`) with events:

```text
data: {"token": "fragment"}

data: [DONE]
```

Relevant body:

```json
{
  "message": "Hello",
  "history": [],
  "persist": false
}
```

### Anonymous Feedback

```text
POST /feedback
```

Body:

```json
{
  "rating": "up",
  "client_message_id": "local-message-id",
  "client_thread_id": "local-thread-id",
  "model": "meta-llama/Llama-3.1-8B-Instruct"
}
```

### Analytics Summary

```text
GET /analytics/summary
```

Returns anonymous totals:

```json
{
  "total_responses": 10,
  "avg_latency_ms": 1200,
  "tokens_in_est": 500,
  "tokens_out_est": 900,
  "positive_feedback": 4,
  "negative_feedback": 1
}
```

### Persistent Conversations

The backend keeps persistent conversation endpoints in case this mode is enabled later:

```text
POST /conversations
GET /conversations
PATCH /conversations/{conversation_id}
DELETE /conversations/{conversation_id}
GET /conversations/{conversation_id}/messages
```

The current portfolio frontend does not use these endpoints to store chats.

## Next API Endpoints

The frontend uses Next API routes as a proxy:

```text
POST /api/chat
POST /api/feedback
GET /api/conversations
PATCH /api/conversations/{conversationId}
DELETE /api/conversations/{conversationId}
GET /api/conversations/{conversationId}/messages
```

## Current UI

- Full-screen layout
- Independent left sidebar
- Separate scroll areas for sidebar and chat
- Local chats with `...` menu
- Options: rename chat and delete chat
- Letter-by-letter SSE response streaming
- `Procesando` spinner until the first token arrives
- Auto-scroll to the latest message
- Response feedback with thumbs up / thumbs down
- Signature: `by Gianni Etcheverry`
- Logo/favicon based on `AiBrain01Icon`

## Deployment Notes

## Screenshots

Recommended review screenshots to add when available:

- Chat working: `docs/screenshots/chat-demo.png`
- Swagger API docs: `docs/screenshots/swagger-docs.png`


This project is dockerized for local development and container-based deployments.

### Local Development With Docker

Use Docker Compose to run the frontend and backend together:

```bash
docker compose up --build
```

This starts both services using the versions and environment defined in the Docker configuration.

### Netlify Deployment

The frontend is deployed separately on Netlify:

[https://ai-chat-platform.netlify.app](https://ai-chat-platform.netlify.app)

Netlify does not use the Docker configuration. Instead, it builds the Next.js frontend directly:

```bash
cd ai-chat-frontend
npm install
npm run build
```

Netlify configuration:

- Base directory: `ai-chat-frontend`
- Build command: `npm run build`
- Publish directory: `.next`
- Next.js plugin: `@netlify/plugin-nextjs`

Environment variable needed by the frontend API routes:

```text
BACKEND_URL=https://ai-chat-platform-production-e316.up.railway.app
```

### Backend Deployment

The backend is deployed separately on Railway:

[https://ai-chat-platform-production-e316.up.railway.app](https://ai-chat-platform-production-e316.up.railway.app)

FastAPI documentation is available at:

[https://ai-chat-platform-production-e316.up.railway.app/docs](https://ai-chat-platform-production-e316.up.railway.app/docs)

Netlify does not deploy the backend. The frontend points to the Railway backend through `BACKEND_URL`.

## Useful Checks

Frontend build:

```bash
cd ai-chat-frontend
npm run build
```

Validate backend syntax:

```bash
python3 -m py_compile ai-chat-backend/schemas.py ai-chat-backend/db.py ai-chat-backend/routers/chat.py ai-chat-backend/routers/analytics.py ai-chat-backend/app.py
```

Test backend:

```bash
curl http://localhost:18000/analytics/summary
```

## Commit And Push Changes

```bash
git add README.md README.es.md
git commit -m "Add deployment notes"
git push
```

## Deployment Note

For a public portfolio deployment, keeping `persist: false` in the frontend prevents private conversations from being stored. The database still provides technical value through anonymous metrics and feedback.
