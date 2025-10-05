# Render Deployment Configuration

## ⚠️ IMPORTANT: Manual Configuration Required

After merging this PR, the following Render settings must be updated manually:

### Backend Service Configuration

**Service Name:** concrete-agent (or your service name)

**Build Settings:**
- **Build Command:** 
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command:** 
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
- **Root Directory:** `/` (leave empty or set to project root)

### Environment Variables

No changes required to environment variables. Existing variables remain the same:
- `DATABASE_URL`
- `API_HOST`
- `API_PORT`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `SECRET_KEY`
- `CORS_ORIGINS`
- etc.

### Docker Settings (if using Docker on Render)

**Dockerfile Path:** `./Dockerfile` (root level)

The Dockerfile now builds from root with:
```dockerfile
COPY app /app/app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Service Configuration

**Service Name:** concrete-agent-frontend (or your service name)

**Build Settings:**
- **Build Command:** 
  ```bash
  cd frontend && npm install && npm run build
  ```
- **Start Command:** 
  ```bash
  cd frontend && npm run preview
  ```
- **Root Directory:** `/` (project root)

**Important:** The frontend's `vite.config.ts` is configured to bind to `0.0.0.0` and use the `$PORT` environment variable, which is required for Render to detect the open port.

**Preview Configuration (already set in vite.config.ts):**
```typescript
preview: {
  host: '0.0.0.0',
  port: Number(process.env.PORT) || 4173,
}
```

## Verification Steps

After deployment, verify the following endpoints:

1. **Health Check:**
   ```bash
   curl https://concrete-agent.onrender.com/health
   ```
   Expected: `{"status": "healthy", "database": "connected", ...}`

2. **Status:**
   ```bash
   curl https://concrete-agent.onrender.com/status
   ```
   Expected: `{"status": "operational", "agents": [...], ...}`

3. **API Documentation:**
   - Visit: https://concrete-agent.onrender.com/docs
   - Should display FastAPI Swagger UI

## Troubleshooting

### Issue: ModuleNotFoundError: No module named 'app'

**Solution:** Ensure the start command is exactly:
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Issue: Import errors in logs

**Check:**
1. Root directory is set to `/` (project root)
2. All files were pushed to the repository
3. The `app/` directory exists at root level

### Issue: Build fails

**Check:**
1. `requirements.txt` is at root level
2. Build command is correct
3. Check build logs for specific package errors

### Issue: Frontend - "No open ports detected on 0.0.0.0"

**Symptoms:**
- Deployment logs show: "Port scan timeout reached, no open ports detected on 0.0.0.0"
- Preview server shows: "Local: http://localhost:4173/" and "Network: use --host to expose"

**Solution:** 
This has been fixed in `frontend/vite.config.ts` with:
```typescript
preview: {
  host: '0.0.0.0',
  port: Number(process.env.PORT) || 4173,
}
```

**Verification:**
After deployment, the preview server should show:
```
➜  Local:   http://localhost:10000/
➜  Network: http://[IP_ADDRESS]:10000/
```

The presence of a Network address confirms the server is binding to 0.0.0.0.

## Rollback Plan

If deployment fails and rollback is needed:

1. Go to Render dashboard
2. Click on the service
3. Go to "Deploys" tab
4. Find the previous working deploy
5. Click "Redeploy" on that version

Alternatively, revert this PR in GitHub:
```bash
git revert <commit-hash>
git push origin main
```

## Cache Clearing (if needed)

The render_purge.yml workflow can be used to clear Render cache:

```bash
# Manually trigger via GitHub Actions
# Or use Render API:
curl -X DELETE https://api.render.com/v1/services/$SERVICE_ID/builds \
  -H "Authorization: Bearer $RENDER_API_KEY" \
  -H "Accept: application/json"
```

## Support

For issues, check:
1. GitHub Actions logs (render_deploy.yml workflow)
2. Render build logs
3. Render runtime logs
4. The RESTRUCTURE_SUMMARY.md file

---

**Last Updated:** 2025-01-05  
**Migration PR:** #[PR_NUMBER]
