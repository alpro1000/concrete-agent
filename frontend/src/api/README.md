# Production URLs and CORS (Stav Agent)

- Frontend (prod): https://stav-agent.onrender.com  
- Backend (prod): https://concrete-agent.onrender.com

## Frontend env

Set the backend base URL (Render → frontend service → Environment):

- Vite: `VITE_API_URL=https://concrete-agent.onrender.com`
- Next.js: `NEXT_PUBLIC_API_URL=https://concrete-agent.onrender.com`

Frontend must use absolute API URL from env (see `frontend/src/lib/api.ts`).

## Backend CORS

Set allowed origins (Render → backend service → Environment):

```
ALLOWED_ORIGINS=https://stav-agent.onrender.com,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
```

FastAPI reads `ALLOWED_ORIGINS` and configures `CORSMiddleware` accordingly.

## Quick checks

- Browser DevTools → Network: requests go to `https://concrete-agent.onrender.com` and are not blocked by CORS.
- CLI CORS test:
  ```
  curl -I -H "Origin: https://stav-agent.onrender.com" https://concrete-agent.onrender.com/health
  ```
  Response should include: `Access-Control-Allow-Origin: https://stav-agent.onrender.com`.
