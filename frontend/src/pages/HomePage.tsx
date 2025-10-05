import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getSystemStatus, getAvailableAgents } from '../api/client'

interface SystemStatus {
  status: string
  agents: string[]
  database: string
  version: string
}

function HomePage() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadStatus()
  }, [])

  const loadStatus = async () => {
    try {
      setLoading(true)
      const data = await getSystemStatus()
      setStatus(data)
      setError(null)
    } catch (err) {
      setError('Nepodařilo se načíst stav systému')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page home-page">
      <h2>Vítejte v Concrete Agent</h2>
      
      <div className="intro">
        <p>
          Moderní systém pro analýzu stavebních dokumentů využívající umělou inteligenci
          a vědeckou metodu.
        </p>
      </div>

      {loading && <div className="loading">Načítání...</div>}
      
      {error && <div className="error">{error}</div>}
      
      {status && (
        <div className="system-status">
          <h3>Stav systému</h3>
          <div className="status-grid">
            <div className="status-item">
              <span className="label">Status:</span>
              <span className={`value ${status.status}`}>{status.status}</span>
            </div>
            <div className="status-item">
              <span className="label">Databáze:</span>
              <span className={`value ${status.database}`}>{status.database}</span>
            </div>
            <div className="status-item">
              <span className="label">Verze:</span>
              <span className="value">{status.version}</span>
            </div>
          </div>

          {status.agents && status.agents.length > 0 && (
            <div className="agents-list">
              <h4>Dostupné agenty ({status.agents.length})</h4>
              <ul>
                {status.agents.map((agent) => (
                  <li key={agent}>{agent}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="actions">
        <Link to="/analysis" className="btn btn-primary">
          Nová analýza
        </Link>
        <Link to="/results" className="btn btn-secondary">
          Zobrazit výsledky
        </Link>
      </div>

      <div className="features">
        <h3>Funkce systému</h3>
        <div className="feature-grid">
          <div className="feature">
            <h4>📄 TZD Reader</h4>
            <p>Analýza technické zadávací dokumentace</p>
          </div>
          <div className="feature">
            <h4>📊 BOQ Parser</h4>
            <p>Zpracování výkazu výměr</p>
          </div>
          <div className="feature">
            <h4>🖼️ Drawing Parser</h4>
            <p>Analýza výkresové dokumentace</p>
          </div>
          <div className="feature">
            <h4>💰 Resource Estimator</h4>
            <p>Odhad zdrojů a nákladů</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HomePage
