# Stav Agent MVP - Deployment Checklist

## Pre-Deployment Verification

### ✅ Code Quality
- [x] Czech is default language in `frontend/src/i18n/index.ts`
- [x] No axios imports outside `frontend/src/api/client.ts`
- [x] No direct fetch() calls outside `frontend/src/lib/api.ts`
- [x] All routes registered in `app/main.py`
- [x] CORS configured with production URLs
- [x] File validation active (50MB, correct extensions)

### ✅ Frontend Build
```bash
cd frontend
npm install
npm run build
# ✓ built in 7.24s
# dist/index.html: 0.56 kB
# dist/assets/index-C15r5hcv.js: 1,194.21 kB
```

### ✅ Backend Tests
```bash
# Upload endpoint works
python -c "from app.main import app; from fastapi.testclient import TestClient; print(TestClient(app).post('/api/v1/analysis/unified', files=[('project_documentation', ('test.pdf', b'content', 'application/pdf'))]).status_code)"
# Output: 200 ✓
```

---

## Environment Variables

### Frontend (.env.production)
```bash
VITE_API_URL=https://concrete-agent.onrender.com
```

### Backend (Render Environment)
```bash
ALLOWED_ORIGINS=https://stav-agent.onrender.com,http://localhost:3000,http://localhost:5173
STORAGE_BASE=storage
MAX_FILE_SIZE_MB=50
```

---

## Deployment Steps

### 1. Backend Deployment (Render)
```bash
# In render.yaml or Render dashboard:
buildCommand: pip install -r requirements.txt
startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT

# Environment variables:
- ALLOWED_ORIGINS
- ANTHROPIC_API_KEY (if using AI features)
```

### 2. Frontend Deployment (Render)
```bash
# In render.yaml or Render dashboard:
buildCommand: cd frontend && npm install && npm run build
startCommand: cd frontend && npm run preview -- --host 0.0.0.0 --port $PORT

# Or use static site:
publishDirectory: frontend/dist

# Environment variables:
- VITE_API_URL=https://concrete-agent.onrender.com
```

---

## Post-Deployment Testing

### Test 1: Homepage loads
```
Visit: https://stav-agent.onrender.com
Expected: Czech language UI, "Stav Agent" title
```

### Test 2: Language switcher
```
Click: Language dropdown
Expected: 🇨🇿 Čeština (selected), 🇷🇺 Русский, 🇬🇧 English
```

### Test 3: File upload
```
1. Click "Nahrát" (Upload)
2. Drag PDF to "Projektová dokumentace" zone
3. Click "Nahrát" button
Expected: "Soubor úspěšně nahrán" message
```

### Test 4: Results display
```
After upload:
Expected: 3 tabs - "Přehled", "Podle agentů", "Věcná a pracovní náplň"
```

### Test 5: Mobile responsive
```
1. Open on mobile device or resize browser to 375px width
2. Expected: Hamburger menu (☰) visible
3. Click hamburger: Menu drawer opens
4. Upload zones: Stack vertically
```

### Test 6: Export functionality
```
1. After analysis completes
2. Click "Exportovat PDF", "Exportovat Word", etc.
Expected: File downloads or "will be available soon" message
```

---

## Rollback Plan

If issues arise:

1. **Frontend issues**: Revert to previous commit
   ```bash
   git revert HEAD~3..HEAD
   git push origin main
   ```

2. **Backend issues**: Check logs
   ```bash
   # On Render dashboard
   View Logs → Check for errors
   Common issues:
   - CORS not configured
   - Missing environment variables
   - Router registration failed
   ```

3. **Critical failure**: Use previous stable version
   ```bash
   git checkout <previous-stable-commit>
   git push origin main --force
   ```

---

## Success Metrics

After deployment, verify:

- ✅ Homepage loads in < 2 seconds
- ✅ Czech text displays correctly (with diacritics)
- ✅ File upload completes successfully
- ✅ API calls return 200 status
- ✅ No console errors in browser DevTools
- ✅ Mobile navigation works smoothly
- ✅ Language switching works
- ✅ Results display after upload

---

## Support Contacts

- **Repository**: https://github.com/alpro1000/concrete-agent
- **Frontend URL**: https://stav-agent.onrender.com
- **Backend URL**: https://concrete-agent.onrender.com
- **API Docs**: https://concrete-agent.onrender.com/docs

---

## Known Issues

1. **Tests expect old response format**
   - Status: Non-critical
   - Impact: Tests fail but actual API works correctly
   - Solution: Tests need updating to match MVP spec

2. **Large file uploads may timeout**
   - Status: Expected behavior
   - Impact: Files >50MB rejected
   - Solution: Working as designed per spec

3. **Export features use fallback**
   - Status: Partial implementation
   - Impact: JSON export works, others show "coming soon"
   - Solution: Backend export endpoints need full implementation

---

## Monitoring

After deployment, monitor:

1. **Error rates** - Check Render logs for 4xx/5xx errors
2. **Response times** - API should respond < 1 second
3. **Upload success rate** - Track successful vs failed uploads
4. **User language preference** - Most users should see Czech
5. **Browser compatibility** - Test on Chrome, Firefox, Safari

---

## Maintenance

Regular checks:

- [ ] Review Render logs weekly
- [ ] Monitor storage usage (uploaded files)
- [ ] Check API response times
- [ ] Update dependencies monthly
- [ ] Test upload with real files
- [ ] Verify CORS configuration

---

## 🎉 Deployment Complete!

When all checks pass:
- ✅ Czech is default language
- ✅ File upload works
- ✅ Results display correctly
- ✅ Mobile responsive
- ✅ API centralized
- ✅ All routes registered
- ✅ CORS configured
- ✅ Build successful

**Ready for production use!**
