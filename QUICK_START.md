# Stav Agent - Quick Start Guide

Get the Stav Agent MVP up and running in 5 minutes.

## Prerequisites

- Python 3.9+ (for backend)
- Node.js 18+ (for frontend)
- npm 8+ (for frontend)

## 🚀 Quick Start

### 1. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### 3. Start Backend Server

```bash
python app/main.py
```

Backend will be available at: http://localhost:8000

- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 4. Start Frontend Dev Server

In a new terminal:

```bash
cd frontend
npm run dev
```

Frontend will be available at: http://localhost:5173

## 🎯 Try It Out

1. **Open the app**: http://localhost:5173
2. **Change language**: Click the language dropdown (🇬🇧 🇨🇿 🇷🇺)
3. **Upload files**: Drag & drop files into any of the 3 upload panels
4. **View results**: Results appear automatically with 4 tabs
5. **Go to dashboard**: Click "My Account" to see your analysis history

## 🧪 Test the API

```bash
# Upload files for analysis
curl -X POST http://localhost:8000/api/v1/analysis/unified \
  -F "technical_files=@document.pdf" \
  -F "quantities_files=@budget.xlsx"

# Health check
curl http://localhost:8000/health
```

## 🔑 Authentication

The unified endpoint accepts an optional `Authorization: Bearer <token>` header for user identification. If not provided, files are stored under user_id=0.

**Mock Token:** `mock_jwt_token_12345`

## 🌍 Available Languages

- 🇬🇧 **English** (default)
- 🇨🇿 **Čeština** (Czech with diacritics)
- 🇷🇺 **Русский** (Russian with Cyrillic)

Language preference is saved automatically.

## 📱 Responsive Design

Try resizing your browser window to see:
- **Desktop view** (1024px+): Full navigation
- **Tablet view** (768px-1023px): Adapted layout
- **Mobile view** (<768px): Hamburger menu

## 🎨 Features to Explore

### Upload Page (/)
- Three specialized upload panels
- Drag & drop support
- Results with 4 tabs:
  - Summary
  - By Agents
  - **Resource & Work Schedule** (new!)
  - JSON

### My Account (/account)
- **Profile**: Edit user info and language
- **My Analyses**: View upload history
- **Settings**: Future configuration options

### Export Options
- JSON (fully functional)
- PDF (mock)
- Word (mock)
- Excel (mock)

## 🛠️ Build for Production

### Frontend Build

```bash
cd frontend
npm run build
```

Built files will be in `frontend/dist/`

### Backend Production

```bash
# Using gunicorn (recommended)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Or using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📝 Environment Variables

### Backend (.env)
```env
APP_NAME=Stav Agent
APP_VERSION=1.0.0
STORAGE_PATH=storage
MAX_FILE_SIZE_MB=50
ENABLE_CHAT=false
PORT=8000
```

### Frontend (.env.development)
```env
VITE_API_URL=http://localhost:8000
```

### Frontend (.env.production)
```env
VITE_API_URL=https://your-production-api.com
```

## 📚 Documentation

- **Frontend README**: `frontend/README.md`
- **Implementation Summary**: `STAV_AGENT_MVP_SUMMARY.md`
- **API Docs**: http://localhost:8000/docs
- **Main README**: `README.md`

## 🐛 Troubleshooting

### Backend won't start
```bash
# Make sure dependencies are installed
pip install -r requirements.txt

# Check Python version
python --version  # Should be 3.9+
```

### Frontend won't start
```bash
# Make sure dependencies are installed
cd frontend
npm install

# Check Node version
node --version  # Should be 18+
```

### Port already in use
```bash
# Backend (port 8000)
lsof -ti:8000 | xargs kill -9

# Frontend (port 5173)
lsof -ti:5173 | xargs kill -9
```

### CORS errors
Make sure both servers are running:
- Backend: http://localhost:8000
- Frontend: http://localhost:5173

## 🎯 What to Test

1. ✅ Upload files (drag & drop)
2. ✅ Switch languages (header dropdown)
3. ✅ View results (all 4 tabs)
4. ✅ Export JSON (download works)
5. ✅ Navigate to My Account
6. ✅ View analysis history
7. ✅ Edit profile info
8. ✅ Try mobile view (resize browser)

## 🚀 Next Steps

- Deploy to production
- Add real authentication
- Implement actual PDF/Word/Excel generation
- Connect to PostgreSQL database
- Add real-time updates with WebSocket

## 💡 Tips

- **Language persists**: Your language choice is saved in localStorage
- **Mock data**: The history shows 3 mock analyses for demo
- **Auto-login**: The app logs you in automatically with mock credentials
- **Responsive**: Try the mobile menu by resizing to <768px
- **Live reload**: Both frontend and backend support hot reload

## 📞 Support

For issues or questions, check:
- API Documentation: http://localhost:8000/docs
- Implementation Summary: `STAV_AGENT_MVP_SUMMARY.md`
- Frontend README: `frontend/README.md`

## ✅ Success Indicators

You'll know it's working when you see:
- ✅ Backend logs show "Server started successfully"
- ✅ Frontend shows "Stav Agent" in the header
- ✅ Language switcher displays 3 flags
- ✅ Upload page shows 3 panels
- ✅ API docs show "Stav Agent API"

---

**Happy testing! 🎉**

© 2025 Stav Agent
