# AI Chat Platform

## 🌎 Idiomas

- [English](README.md)
- Español (este documento)

## Demo en vivo

[Ver proyecto desplegado en Netlify](https://ai-chat-platform.netlify.app)

Aplicacion de chat IA para portfolio, construida con Next.js, FastAPI, PostgreSQL y Hugging Face.

La experiencia principal funciona como demo privada por visitante: los chats se guardan en `localStorage` del navegador y no se mezclan entre usuarios. PostgreSQL se usa para metricas anonimas y feedback, no para guardar conversaciones privadas.

## Stack

### Frontend

- Next.js 15
- React 19
- TypeScript
- Hugeicons
- Tema claro/oscuro con preferencia en `localStorage`
- Chats locales por navegador
- Feedback por respuesta
- Favicon/logo con `AiBrain01Icon`

### Backend

- Python 3.11
- FastAPI + Pydantic
- PostgreSQL + psycopg2
- Hugging Face Inference API
- Modelo: `meta-llama/Llama-3.1-8B-Instruct`
- Uvicorn

## Estructura

```text
aichatbox/
├── ai-chat-backend/
├── ai-chat-frontend/
├── docker-compose.yml
├── README.md
└── README.es.md
```

## Puertos

- Frontend Docker: `http://localhost:3003`
- Frontend dev alternativo usado localmente: `http://localhost:3004`
- Backend: `http://localhost:18000`
- PostgreSQL: `localhost:15432`

## Levantar todo con Docker

Desde la raiz del proyecto:

```bash
docker compose up -d --build
```

Siguientes veces, sin rebuild:

```bash
docker compose up -d
```

Apagar:

```bash
docker compose down
```

Reconstruir solo backend despues de cambios Python:

```bash
docker compose up -d --build backend
```

Reconstruir solo frontend despues de cambios Next:

```bash
docker compose up -d --build frontend
```

## Desarrollo local frontend

```bash
cd ai-chat-frontend
npm install
npm run dev
```

Por defecto el frontend corre en `3003`. Si ese puerto esta ocupado, se puede usar Next directamente con otro puerto:

```bash
./node_modules/.bin/next dev -p 3004
```

En desarrollo local, las API routes de Next usan este backend por defecto:

```text
http://localhost:18000
```

En Docker, `docker-compose.yml` define:

```text
BACKEND_URL=http://backend:8000
```

## Variables de entorno backend

Archivo esperado:

```text
ai-chat-backend/.env
```

Ejemplo:

```env
DATABASE_URL=postgresql://user:password@postgres:5432/chatdb
HF_TOKEN=tu_token_huggingface
```

No subas tokens reales a repos publicos.

## Modo portfolio/demo

El frontend envia los mensajes a `/api/chat` con:

```json
{
  "persist": false
}
```

Con `persist: false`, el backend:

- genera respuesta con Hugging Face en streaming SSE
- registra metricas anonimas al finalizar el stream
- no crea conversaciones en PostgreSQL
- no guarda mensajes del usuario
- no guarda respuestas del asistente

Los chats del visitante se guardan solo en:

```text
localStorage
```

Esto evita que distintos visitantes vean o mezclen conversaciones entre si.

## Uso de PostgreSQL

PostgreSQL se usa para datos anonimos de portfolio:

### `anonymous_chat_metrics`

Guarda datos tecnicos por respuesta:

- modo (`demo`)
- modelo usado
- tokens estimados de entrada
- tokens estimados de salida
- latencia
- si fue persistido o no
- fecha

No guarda texto del chat.

### `anonymous_feedback`

Guarda feedback anonimo:

- rating: `up` o `down`
- id local anonimo del mensaje
- id local anonimo del chat
- modelo
- comentario opcional
- fecha

No guarda prompts ni respuestas.

## Endpoints principales

### Chat

```text
POST /chat
```

Devuelve una respuesta SSE (`text/event-stream`) con eventos:

```text
data: {"token": "fragmento"}

data: [DONE]
```

Body relevante:

```json
{
  "message": "Hola",
  "history": [],
  "persist": false
}
```

### Feedback anonimo

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

### Resumen de analytics

```text
GET /analytics/summary
```

Devuelve totales anonimos:

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

### Conversaciones persistentes

El backend conserva endpoints para modo persistente si se quisiera activar en el futuro:

```text
POST /conversations
GET /conversations
PATCH /conversations/{conversation_id}
DELETE /conversations/{conversation_id}
GET /conversations/{conversation_id}/messages
```

El frontend actual de portfolio no los usa para guardar chats.

## Endpoints Next API

El frontend usa API routes como proxy:

```text
POST /api/chat
POST /api/feedback
GET /api/conversations
PATCH /api/conversations/{conversationId}
DELETE /api/conversations/{conversationId}
GET /api/conversations/{conversationId}/messages
```

## UI actual

- Layout full screen
- Sidebar independiente a la izquierda
- Scroll separado para sidebar y chat
- Chats locales con menu `...`
- Opciones: cambiar nombre y eliminar chat
- Streaming de respuesta letra por letra via SSE
- Spinner `Procesando` hasta recibir el primer token
- Auto-scroll al ultimo mensaje
- Feedback por respuesta con pulgar arriba / abajo
- Firma: `by Gianni Etcheverry`
- Logo/fav icon basado en `AiBrain01Icon`

## Deployment notes

This project is dockerized for local development and container-based deployments.

### Local development with Docker

Use Docker Compose to run the frontend and backend together:

```bash
docker compose up --build
```

This starts both services using the versions and environment defined in the Docker configuration.

### Netlify deployment

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
BACKEND_URL=https://your-deployed-backend-url
```

### Backend deployment

The backend is not automatically deployed by Netlify. It should be deployed separately using a backend-friendly platform such as Render, Railway, Fly.io, a VPS, or any container-based hosting provider.

The frontend should point to the deployed backend URL using `BACKEND_URL`.

## Verificaciones utiles

Build frontend:

```bash
cd ai-chat-frontend
npm run build
```

Validar sintaxis backend:

```bash
python3 -m py_compile ai-chat-backend/schemas.py ai-chat-backend/db.py ai-chat-backend/routers/chat.py ai-chat-backend/routers/analytics.py ai-chat-backend/app.py
```

Probar backend:

```bash
curl http://localhost:18000/analytics/summary
```

## Publicar cambios en Git

```bash
git add README.md README.es.md
git commit -m "Add deployment notes"
git push
```

## Nota para despliegue

Para portfolio publico, mantener `persist: false` en el frontend evita que se guarden conversaciones privadas. La base de datos sigue aportando valor tecnico mediante metricas anonimas y feedback.
