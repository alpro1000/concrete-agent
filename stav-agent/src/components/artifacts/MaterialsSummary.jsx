import React from 'react';
import { formatNumber } from '../../utils/helpers';

export default function MaterialsSummary({ data = {} }) {
  const materials = data.materials ?? [];

  if (!materials.length) {
    return <div className="text-sm text-gray-500">Žádné materiály k dispozici.</div>;
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2 text-xs font-semibold text-gray-500 uppercase">
        <span>Materiál</span>
        <span className="text-right">Množství</span>
        <span className="text-right">Cena</span>
      </div>
      <div className="space-y-2">
        {materials.map((item) => (
          <div key={item.id} className="grid grid-cols-3 gap-2 text-sm bg-white border border-gray-200 rounded-lg p-2">
            <span className="font-medium text-gray-800">{item.name}</span>
            <span className="text-right text-gray-600">{formatNumber(item.quantity)} {item.unit}</span>
            <span className="text-right text-gray-800">{formatNumber(item.total_cost)} Kč</span>
          </div>
        ))}
      </div>
    </div>
  );
}
