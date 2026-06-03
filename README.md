# AI Chat Platform

## 🌎 Languages

- English (this document)
- [Español](README.es.md)

## Live Demo

Frontend: [https://ai-chat-platform.netlify.app](https://ai-chat-platform.netlify.app)

Backend API: [https://ai-chat-platform-production-e316.up.railway.app](https://ai-chat-platform-production-e316.up.railway.app)

API Docs: [https://ai-chat-platform-production-e316.up.railway.app/docs](https://ai-chat-platform-production-e316.up.railway.app/docs)

AI chat application for a portfolio project, built with Next.js, FastAPI, PostgreSQL, Hugging Face, OpenRouter, and Gemini.

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
- OpenRouter API
- Gemini API
- Automatic provider fallback: Gemini -> OpenRouter -> Hugging Face
- Default Hugging Face model: `meta-llama/Llama-3.1-8B-Instruct`
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
OPENROUTER_API_KEY=your_openrouter_token
OPENROUTER_DEFAULT_MODEL=deepseek/deepseek-chat-v3-0324:free
GEMINI_API_KEY=your_gemini_token
GEMINI_DEFAULT_MODEL=gemini-2.5-flash
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

- generates the AI response through SSE streaming
- supports Hugging Face, OpenRouter, and Gemini
- automatically falls back to the next provider on rate limits, server errors, or timeouts
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
- requested provider
- actual provider
- whether fallback was used
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

## API Endpoints

- `GET /` - API status
- `GET /health` - Health check
- `GET /health/db` - Database health check
- `POST /chat` - Send a chat message
- `POST /feedback` - Submit feedback
- `GET /analytics/summary` - Get usage analytics
- `GET /analytics/models` - Get usage analytics grouped by provider and model
- `GET /analytics/fallbacks` - Get automatic provider fallback metrics
- `GET /docs` - Swagger API documentation

### Health Check Examples

```bash
curl https://ai-chat-platform-production-e316.up.railway.app/health
```

Expected response:

```json
{"status":"ok","service":"ai-chat-backend"}
```

```bash
curl https://ai-chat-platform-production-e316.up.railway.app/health/db
```

Expected response:

```json
{"status":"ok","database":"connected"}
```

### Chat

```text
POST /chat
```

Returns an SSE response (`text/event-stream`) with events:

```text
data: {"token": "fragment"}

data: {"metadata": {"provider": "openrouter", "model": "openrouter/free", "latency_ms": 2300}}

data: [DONE]
```

Relevant body:

```json
{
  "message": "Hello",
  "history": [],
  "persist": false,
  "provider": "huggingface",
  "model": null
}
```

Provider defaults:

- `huggingface` is used when no provider is sent.
- `openrouter` uses `OPENROUTER_DEFAULT_MODEL` or `deepseek/deepseek-chat-v3-0324:free`.
- `gemini` uses `GEMINI_DEFAULT_MODEL` or `gemini-2.5-flash`.

Automatic fallback order:

1. Gemini
2. OpenRouter
3. Hugging Face

Fallback is only used for retryable provider failures: `429`, `5xx`, or timeout. Validation errors are not retried, and provider error details are not exposed to users.

OpenRouter test:

```bash
curl -X POST https://ai-chat-platform-production-e316.up.railway.app/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","history":[],"persist":false,"provider":"openrouter"}'
```

Gemini test:

```bash
curl -X POST https://ai-chat-platform-production-e316.up.railway.app/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","history":[],"persist":false,"provider":"gemini"}'
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

### Model Analytics

```text
GET /analytics/models
```

Returns anonymous usage grouped by provider and model:

```json
{
  "models": [
    {
      "provider": "openrouter",
      "model": "deepseek/deepseek-chat-v3-0324:free",
      "total_requests": 120,
      "avg_latency_ms": 850
    }
  ]
}
```


### Fallback Analytics

```text
GET /analytics/fallbacks
```

Returns anonymous fallback usage:

```json
{
  "total_fallbacks": 12,
  "fallback_rate": 0.08
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
- Model/provider selector
- Toast confirmation when the model changes
- Letter-by-letter SSE response streaming
- Response metadata below assistant messages: provider, model, and latency
- `Procesando` spinner until the first token arrives
- Auto-scroll to the latest message
- Response feedback with thumbs up / thumbs down
- Analytics dashboard at `/analytics`
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
