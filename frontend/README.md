# Stav Agent Frontend

**Intelligent Construction Document Analysis**

Modern React frontend for the Stav Agent construction document analysis platform.

## 🚀 Features

- **Three-Panel Upload System**: Specialized upload areas for technical documents, bills of quantities, and drawings
- **Multi-language Support**: Full internationalization (Czech 🇨🇿, Russian 🇷🇺, English 🇬🇧)
- **User Dashboard**: Profile management, analysis history, and settings
- **Results Visualization**: Interactive tabs showing summary, agent analysis, and resource schedules
- **Export Functionality**: Download results in JSON, PDF, Word, and Excel formats
- **Responsive Design**: Mobile-friendly with hamburger menu and touch controls
- **Mock Authentication**: Demo user login for testing

## 📋 Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **React Router** for navigation
- **Ant Design** for UI components
- **i18next** for internationalization
- **Axios** for API communication

## 🛠️ Installation

```bash
npm install
```

## 🏃 Development

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

## 🏗️ Build

```bash
npm run build
```

Built files will be in the `dist/` directory.

## 🌍 Environment Variables

Create a `.env.development` or `.env.production` file:

```env
VITE_API_URL=http://localhost:8000
```

## 📱 Responsive Design

The application is fully responsive with:
- Desktop: Full navigation and multi-column layouts
- Tablet: Adaptive layouts  
- Mobile: Hamburger menu and stacked layouts

## 🎯 Usage

1. **Select Language**: Use the language dropdown in the header
2. **Upload Files**: Drag and drop or click to browse in the upload panels
3. **View Results**: Results appear automatically after upload
4. **Export**: Download results in your preferred format
5. **My Account**: View your analysis history and manage profile

## 🔐 Authentication

Currently uses mock authentication for development:
- Token: `mock_jwt_token_12345`
- User: demo@stav-agent.com

## 📄 License

© 2025 Stav Agent
