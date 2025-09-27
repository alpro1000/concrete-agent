# Construction Analysis Frontend

A modern React + TypeScript frontend for the Construction Analysis API with multilingual support.

## 🚀 Features

- **Modern Tech Stack**: React 19 + Vite + TypeScript + Ant Design
- **Multilingual Support**: Czech, English, and Russian with react-i18next
- **File Upload**: Drag & drop interface for PDF, DOCX, XLSX files
- **Real-time Analysis**: Live progress indicators and results visualization
- **Data Visualization**: Interactive charts with Recharts
- **Responsive Design**: Mobile-friendly interface
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

By default, the frontend connects to the backend at `http://localhost:8000`. To change this, update `baseURL` in `src/api/client.ts`.

## 🌐 Internationalization

The application supports three languages:

- **Czech (cs)** - Default language
- **English (en)** - Fallback language  
- **Russian (ru)** - Additional language

## 📊 API Integration

The frontend integrates with these backend endpoints:

- `POST /analyze/concrete` - Concrete structure analysis
- `POST /analyze/materials` - Materials analysis  
- `POST /compare/docs` - Document comparison
- `POST /compare/smeta` - Budget comparison
- `POST /upload/files` - File upload utility

## 🚀 Deployment

The built frontend can be deployed to any static hosting service or alongside the backend API.

```bash
npm run build
# Deploy the dist/ directory
```