import React from 'react';

export default function MaterialsSummary({ data }) {
  if (!data) return <div className="text-gray-500">Žádná data</div>;

  const { materials = [], total_weight = 0 } = data;

  return (
    <div className="space-y-3">
      <div className="bg-blue-50 p-2 rounded text-xs text-blue-700 border border-blue-200">
        📦 Celkový obsah: {total_weight} t
      </div>

      <div className="space-y-1">
        {materials.map((mat, i) => (
          <div key={i} className="p-2 bg-gray-50 rounded text-xs border border-gray-200">
            <div className="flex justify-between">
              <span className="font-semibold text-gray-900">{mat.name}</span>
              <span className="text-gray-600">
                {mat.quantity} {mat.unit}
              </span>
            </div>
            {mat.notes && <div className="text-gray-500 text-xs mt-1">{mat.notes}</div>}
          </div>
        ))}
        {materials.length === 0 && (
          <div className="text-gray-500 text-xs">Žádné materiály</div>
        )}
      </div>
    </div>
  );
}
