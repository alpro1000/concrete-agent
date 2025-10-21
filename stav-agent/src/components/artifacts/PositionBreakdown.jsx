import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

export default function PositionBreakdown({ data }) {
  const [expandedId, setExpandedId] = useState(null);

  if (!data) return <div className="text-gray-500">Žádná data</div>;

  const { positions = [] } = data;

  return (
    <div className="space-y-2">
      {positions.map((pos, i) => (
        <div key={i} className="border border-gray-300 rounded-lg overflow-hidden">
          <button
            onClick={() => setExpandedId(expandedId === i ? null : i)}
            className="w-full p-3 bg-gray-50 hover:bg-gray-100 transition text-left flex items-center justify-between"
          >
            <div className="flex-1">
              <div className="font-semibold text-sm text-gray-900">{pos.code}</div>
              <div className="text-xs text-gray-600">{pos.description}</div>
            </div>
            {expandedId === i ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>

          {expandedId === i && (
            <div className="p-3 bg-white border-t border-gray-200 text-xs space-y-1">
              <div>
                <strong>Jednotka:</strong> {pos.unit}
              </div>
              <div>
                <strong>Množství:</strong> {pos.quantity}
              </div>
              {pos.materials && (
                <div className="mt-2">
                  <strong>Materiály:</strong>
                  <div className="ml-2 text-gray-600">
                    {pos.materials.map((m, j) => (
                      <div key={j}>
                        {m.name}: {m.quantity} {m.unit}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
