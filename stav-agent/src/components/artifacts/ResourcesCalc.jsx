import React from 'react';

export default function ResourcesCalc({ data }) {
  if (!data) return <div className="text-gray-500">Žádná data</div>;

  const { labor_hours = 0, equipment = [], materials_cost = 0 } = data;

  return (
    <div className="space-y-3">
      <div className="bg-orange-50 p-2 rounded text-xs border border-orange-200">
        <div className="font-semibold text-orange-900">⏱️ Pracovní hodiny</div>
        <div className="text-orange-700 text-lg font-bold">{labor_hours} h</div>
      </div>

      {equipment && equipment.length > 0 && (
        <div>
          <div className="font-semibold text-xs text-gray-700 mb-1">⚙️ Technika:</div>
          <div className="space-y-1">
            {equipment.map((eq, i) => (
              <div key={i} className="text-xs p-2 bg-gray-50 rounded border border-gray-200">
                <div className="font-semibold">{eq.name}</div>
                <div className="text-gray-600">{eq.hours} h</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-green-50 p-2 rounded text-xs border border-green-200">
        <div className="font-semibold text-green-900">💰 Materiály</div>
        <div className="text-green-700 text-lg font-bold">{Number(materials_cost || 0).toLocaleString()} Kč</div>
      </div>
    </div>
  );
}
