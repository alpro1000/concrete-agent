import React from 'react';
import { STATUS_COLORS } from '../../utils/constants';

export default function AuditResult({ data = {} }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-green-50 p-3 rounded text-center">
          <div className="text-2xl font-bold text-green-600">{data.green || 0}</div>
          <div className="text-xs text-green-700">GREEN</div>
        </div>
        <div className="bg-yellow-50 p-3 rounded text-center">
          <div className="text-2xl font-bold text-yellow-600">{data.amber || 0}</div>
          <div className="text-xs text-yellow-700">AMBER</div>
        </div>
        <div className="bg-red-50 p-3 rounded text-center">
          <div className="text-2xl font-bold text-red-600">{data.red || 0}</div>
          <div className="text-xs text-red-700">RED</div>
        </div>
      </div>

      {data.issues?.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2 text-gray-700">Problémy:</h4>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {data.issues.map((issue, i) => (
              <div key={i} className={`p-2 rounded text-sm border-l-2 ${STATUS_COLORS[issue.status] ?? ''}`}>
                <div className="font-mono text-sm">{issue.code}</div>
                <div className="text-xs">{issue.description}</div>
                <div className="text-xs font-semibold mt-1">⚠️ {issue.problem}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
