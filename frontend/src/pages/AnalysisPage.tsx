import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function AnalysisPage() {
  const navigate = useNavigate()
  const [selectedAgent, setSelectedAgent] = useState('tzd_reader')
  const [file, setFile] = useState<File | null>(null)
  const [textInput, setTextInput] = useState('')
  const [loading, setLoading] = useState(false)

  const agents = [
    { id: 'tzd_reader', name: 'TZD Reader', description: 'Analýza technické zadávací dokumentace' },
    { id: 'boq_parser', name: 'BOQ Parser', description: 'Zpracování výkazu výměr' },
    { id: 'drawing_parser', name: 'Drawing Parser', description: 'Analýza výkresů' },
    { id: 'resource_estimator', name: 'Resource Estimator', description: 'Odhad zdrojů' },
  ]

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!file && !textInput) {
      alert('Vyberte soubor nebo zadejte text')
      return
    }

    setLoading(true)

    try {
      // TODO: Implement API call to execute agent
      console.log('Executing agent:', selectedAgent)
      console.log('File:', file)
      console.log('Text:', textInput)
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      // Navigate to results
      navigate('/results')
    } catch (err) {
      console.error('Analysis failed:', err)
      alert('Analýza selhala')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page analysis-page">
      <h2>Nová analýza</h2>

      <form onSubmit={handleSubmit} className="analysis-form">
        <div className="form-group">
          <label htmlFor="agent">Vyberte agenta</label>
          <select
            id="agent"
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            className="form-control"
          >
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name} - {agent.description}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="file">Nahrát soubor</label>
          <input
            id="file"
            type="file"
            onChange={handleFileChange}
            className="form-control"
            accept=".txt,.pdf,.doc,.docx"
          />
          {file && <p className="file-info">Vybraný soubor: {file.name}</p>}
        </div>

        <div className="form-group">
          <label htmlFor="text">Nebo zadejte text</label>
          <textarea
            id="text"
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            className="form-control"
            rows={10}
            placeholder="Vložte text dokumentu zde..."
          />
        </div>

        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading || (!file && !textInput)}
          >
            {loading ? 'Zpracovávání...' : 'Spustit analýzu'}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => navigate('/')}
          >
            Zpět
          </button>
        </div>
      </form>

      <div className="agent-info">
        <h3>O vybraném agentovi</h3>
        {agents.find(a => a.id === selectedAgent) && (
          <div className="info-card">
            <h4>{agents.find(a => a.id === selectedAgent)?.name}</h4>
            <p>{agents.find(a => a.id === selectedAgent)?.description}</p>
            <p className="info-detail">
              Tento agent používá vědeckou metodu: Hypotéza → Rozumování → Verifikace → Závěr
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default AnalysisPage
