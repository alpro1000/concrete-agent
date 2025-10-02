# Stav Agent Frontend

A modern React + TypeScript frontend for construction project analysis with AI-powered document processing and multilingual support.

## 🚀 Features

- **Modern Tech Stack**: React 19 + Vite + TypeScript + Ant Design
- **Multilingual Support**: Czech 🇨🇿, English 🇬🇧, and Russian 🇷🇺 with react-i18next
- **Three-Panel Upload System**: 
  - Technical assignment & project descriptions (PDF, DOCX, TXT)
  - Bill of quantities, budget, work list (Excel, XML, XC4)
  - Drawings (PDF, DWG, DXF, images)
- **File Upload**: Drag & drop interface with file type validation
- **Real-time Analysis**: Live progress indicators and results visualization
- **Results Panel**: JSON output, formatted summary, and export options (PDF, Word, Excel)
- **Data Visualization**: Interactive charts with Recharts
- **Responsive Design**: Mobile-friendly interface with dark teal theme
- **Type Safety**: Full TypeScript coverage
- **Production Ready**: Optimized builds with code splitting

## 🛠️ Development

### Prerequisites

- Node.js 18+ 
- npm 8+

### Installation

```bash
cd frontend
npm install
```

### Development Server

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## 🔧 Configuration

### Backend API

The frontend uses environment variables to configure the backend API URL:

- **Development**: Uses `.env.development` → `http://localhost:8000`
- **Production**: Uses `.env.production` → `https://concrete-agent.onrender.com`

#### Environment Variables

Create a `.env.local` file (ignored by git) to override the default configuration:

```bash
VITE_API_URL=http://your-custom-api-url.com
```

The API client (`src/api/client.ts`) automatically uses `import.meta.env.VITE_API_URL` with fallbacks:
- Production: `https://concrete-agent.onrender.com`
- Development: `http://localhost:8000`

### Vite Configuration

The `vite.config.ts` is configured for Render deployment:

- **Development Server**: Runs on port `5173`
- **Preview Server**: Runs on port `4173` (use `npm run preview` after build)
- **Allowed Hosts**: Configured for `stav-agent.onrender.com` deployment
- **No Proxy**: Direct API calls to backend using environment variables

## 🌐 Internationalization

The application supports three languages:

- **Czech (cs)** - Default language
- **English (en)** - Fallback language  
- **Russian (ru)** - Additional language

## 📊 API Integration

The frontend integrates with these backend endpoints:

- `POST /api/v1/analysis/unified` - Unified analysis endpoint for all file types
- `POST /analyze/concrete` - Concrete structure analysis
- `POST /analyze/materials` - Materials analysis  
- `POST /compare/docs` - Document comparison
- `POST /compare/smeta` - Budget comparison
- `POST /upload/files` - File upload utility

## 🚀 Deployment

### Automatic Deployment to Render

The frontend is automatically deployed to Render on every push to the `main` branch via GitHub Actions (`.github/workflows/deploy-frontend.yml`).

**Requirements:**
- `RENDER_API_KEY` - Render API key (stored in GitHub Secrets)
- `RENDER_SERVICE_ID` - Render service ID (stored in GitHub Secrets)

### Manual Deployment

The built frontend can be deployed to any static hosting service or alongside the backend API.

```bash
npm run build
# Deploy the dist/ directory
```

The production URL is configured as: `https://stav-agent.onrender.com`