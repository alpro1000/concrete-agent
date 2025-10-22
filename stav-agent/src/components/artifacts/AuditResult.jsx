import React from 'react';

const severityStyles = {
  GREEN: 'bg-green-50 text-green-700 border-green-200',
  AMBER: 'bg-amber-50 text-amber-700 border-amber-200',
  RED: 'bg-red-50 text-red-700 border-red-200',
};

const severityLabels = {
  GREEN: 'Bez problémů',
  AMBER: 'Varování',
  RED: 'Kritické',
};

export default function AuditResult({ data = {}, compact = false }) {
  const {
    summary,
    statistics = {},
    issues = [],
    statistics_by_severity: severityStats = {},
  } = data;

  const totalPositions = statistics.total_positions ?? 0;

  return (
    <div className={`space-y-4 ${compact ? 'text-xs' : 'text-sm'}`}>
      {summary && <p className="text-gray-700 leading-relaxed">{summary}</p>}

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
          <div className="text-xs font-semibold uppercase text-blue-600">Pozice</div>
          <div className="text-lg font-bold text-blue-900">{totalPositions}</div>
        </div>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
          <div className="text-xs font-semibold uppercase text-emerald-600">Ověřeno</div>
          <div className="text-lg font-bold text-emerald-900">{statistics.verified ?? 0}</div>
        </div>
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <div className="text-xs font-semibold uppercase text-amber-600">Varování</div>
          <div className="text-lg font-bold text-amber-900">{statistics.with_warnings ?? 0}</div>
        </div>
        <div className="rounded-lg border border-red-200 bg-red-50 p-3">
          <div className="text-xs font-semibold uppercase text-red-600">Kritické</div>
          <div className="text-lg font-bold text-red-900">{statistics.critical_issues ?? 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs">
        {Object.entries(severityStats).map(([severity, count]) => (
          <div
            key={severity}
            className={`rounded border p-2 text-center font-medium ${severityStyles[severity] || 'bg-gray-50 text-gray-600 border-gray-200'}`}
          >
            <div className="text-xs uppercase tracking-wide">{severity}</div>
            <div className="text-base">{count}</div>
            <div className="text-[10px] opacity-75">{severityLabels[severity] || ''}</div>
          </div>
        ))}
      </div>

      {issues.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-600">
            Problematické pozice ({issues.length})
          </h4>
          <div className="space-y-2">
            {issues.map((issue) => (
              <div
                key={issue.position_id || issue.code}
                className={`rounded-lg border p-3 text-xs shadow-sm ${
                  severityStyles[issue.severity] || 'bg-gray-50 text-gray-700 border-gray-200'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-mono text-sm font-semibold">{issue.code}</div>
                    <div className="font-medium">{issue.description}</div>
                  </div>
                  <span className="rounded-full bg-white/60 px-2 py-0.5 text-[10px] font-semibold uppercase">
                    {issue.severity}
                  </span>
                </div>
                <div className="mt-2 text-[11px] font-semibold">⚠️ {issue.problem}</div>
                {issue.suggestion && (
                  <div className="mt-1 text-[11px] text-gray-700">
                    Návrh: <span className="font-medium">{issue.suggestion}</span>
                  </div>
                )}
                {issue.sources && issue.sources.length > 0 && (
                  <div className="mt-2 text-[10px] text-gray-600">
                    Zdroje: {issue.sources.join(', ')}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
