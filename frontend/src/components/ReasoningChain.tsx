import React from 'react'

interface ReasoningStep {
  step: string
  content: string
  confidence: number
  timestamp: string
}

interface ReasoningChainProps {
  steps: ReasoningStep[]
}

const ReasoningChain: React.FC<ReasoningChainProps> = ({ steps }) => {
  const getStepIcon = (step: string) => {
    const icons: Record<string, string> = {
      hypothesis: '💡',
      reasoning: '🔍',
      verification: '✓',
      conclusion: '📊',
    }
    return icons[step] || '•'
  }

  const getStepTitle = (step: string) => {
    const titles: Record<string, string> = {
      hypothesis: 'Hypotéza',
      reasoning: 'Rozumování',
      verification: 'Verifikace',
      conclusion: 'Závěr',
    }
    return titles[step] || step
  }

  return (
    <div className="reasoning-chain">
      <h4>Řetězec vědecké metody</h4>
      <div className="reasoning-steps">
        {steps.map((step, index) => (
          <div key={index} className="reasoning-step">
            <div className="step-header">
              <span className="step-icon">{getStepIcon(step.step)}</span>
              <span className="step-title">{getStepTitle(step.step)}</span>
              <span className="step-confidence">
                {Math.round(step.confidence * 100)}% jistota
              </span>
            </div>
            <div className="step-content">{step.content}</div>
            <div className="step-timestamp">
              {new Date(step.timestamp).toLocaleTimeString('cs-CZ')}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ReasoningChain
