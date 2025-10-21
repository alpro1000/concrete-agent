import React from 'react';

export default function AuditResult({ data }) {
  if (!data) return <div className="text-gray-500">Žádná data</div>;

  const { green = 0, amber = 0, red = 0, issues = [] } = data;
  const total = green + amber + red;
  const getPercent = (value) => (total ? Math.round((value / total) * 100) : 0);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-green-50 p-3 rounded-lg text-center border border-green-200">
          <div className="text-2xl font-bold text-green-600">{green}</div>
          <div className="text-xs text-green-700 font-semibold">GREEN</div>
          <div className="text-xs text-green-600">{getPercent(green)}%</div>
        </div>
        <div className="bg-yellow-50 p-3 rounded-lg text-center border border-yellow-200">
          <div className="text-2xl font-bold text-yellow-600">{amber}</div>
          <div className="text-xs text-yellow-700 font-semibold">AMBER</div>
          <div className="text-xs text-yellow-600">{getPercent(amber)}%</div>
        </div>
        <div className="bg-red-50 p-3 rounded-lg text-center border border-red-200">
          <div className="text-2xl font-bold text-red-600">{red}</div>
          <div className="text-xs text-red-700 font-semibold">RED</div>
          <div className="text-xs text-red-600">{getPercent(red)}%</div>
        </div>
      </div>

      {issues && issues.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2 text-gray-700">Problémy ({issues.length}):</h4>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {issues.map((issue, i) => (
              <div key={i} className="p-2 rounded text-xs border-l-2 bg-red-50 border-red-300">
                <div className="font-mono text-red-700 font-bold">{issue.code}</div>
                <div className="text-gray-700 text-xs mt-1">{issue.description}</div>
                <div className="text-red-600 text-xs font-semibold mt-1">⚠️ {issue.problem}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
