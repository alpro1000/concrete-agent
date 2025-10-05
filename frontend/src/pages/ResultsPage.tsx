import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

interface Analysis {
  id: number
  title: string
  agent: string
  status: string
  created_at: string
}

function ResultsPage() {
  const [analyses, setAnalyses] = useState<Analysis[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadResults()
  }, [])

  const loadResults = async () => {
    try {
      setLoading(true)
      // TODO: Implement API call
      // For now, use mock data
      const mockData: Analysis[] = [
        {
          id: 1,
          title: 'TZD Analýza - Projekt A',
          agent: 'tzd_reader',
          status: 'completed',
          created_at: new Date().toISOString(),
        },
        {
          id: 2,
          title: 'BOQ Analýza - Projekt B',
          agent: 'boq_parser',
          status: 'processing',
          created_at: new Date(Date.now() - 3600000).toISOString(),
        },
      ]
      
      setAnalyses(mockData)
      setError(null)
    } catch (err) {
      setError('Nepodařilo se načíst výsledky')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      pending: 'Čeká',
      processing: 'Zpracovává se',
      completed: 'Dokončeno',
      failed: 'Chyba',
    }
    return labels[status] || status
  }

  const getStatusClass = (status: string) => {
    return `status-badge status-${status}`
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('cs-CZ')
  }

  return (
    <div className="page results-page">
      <div className="page-header">
        <h2>Výsledky analýz</h2>
        <Link to="/analysis" className="btn btn-primary">
          Nová analýza
        </Link>
      </div>

      {loading && <div className="loading">Načítání výsledků...</div>}
      
      {error && <div className="error">{error}</div>}
      
      {!loading && !error && analyses.length === 0 && (
        <div className="empty-state">
          <p>Zatím nebyly provedeny žádné analýzy</p>
          <Link to="/analysis" className="btn btn-primary">
            Vytvořit první analýzu
          </Link>
        </div>
      )}

      {!loading && analyses.length > 0 && (
        <div className="results-list">
          {analyses.map((analysis) => (
            <div key={analysis.id} className="result-card">
              <div className="result-header">
                <h3>{analysis.title}</h3>
                <span className={getStatusClass(analysis.status)}>
                  {getStatusLabel(analysis.status)}
                </span>
              </div>
              
              <div className="result-meta">
                <span className="meta-item">
                  <strong>Agent:</strong> {analysis.agent}
                </span>
                <span className="meta-item">
                  <strong>Vytvořeno:</strong> {formatDate(analysis.created_at)}
                </span>
              </div>

              <div className="result-actions">
                <button className="btn btn-secondary">Zobrazit detail</button>
                <button className="btn btn-secondary">Stáhnout</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ResultsPage
