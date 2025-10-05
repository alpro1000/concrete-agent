import { BrowserRouter, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import AnalysisPage from './pages/AnalysisPage'
import ResultsPage from './pages/ResultsPage'
import './styles/App.css'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <header className="app-header">
          <h1>Concrete Agent</h1>
          <p>Systém pro analýzu stavebních dokumentů</p>
        </header>
        
        <main className="app-main">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/analysis" element={<AnalysisPage />} />
            <Route path="/results" element={<ResultsPage />} />
          </Routes>
        </main>
        
        <footer className="app-footer">
          <p>© 2024 Concrete Agent - Vědecká metoda v analýze stavebních projektů</p>
        </footer>
      </div>
    </BrowserRouter>
  )
}

export default App
