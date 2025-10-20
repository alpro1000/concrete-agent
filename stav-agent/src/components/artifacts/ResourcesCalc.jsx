import React from 'react';
import { formatNumber } from '../../utils/helpers';

export default function ResourcesCalc({ data = {} }) {
  const labor = data.labor ?? [];
  const machinery = data.machinery ?? [];

  if (!labor.length && !machinery.length) {
    return <div className="text-sm text-gray-500">Žádné zdroje k zobrazení.</div>;
  }

  return (
    <div className="space-y-4">
      {labor.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Pracovní síla</h4>
          <div className="space-y-2">
            {labor.map((item) => (
              <div key={item.id} className="flex justify-between text-sm bg-white border border-gray-200 rounded-lg p-2">
                <span className="text-gray-700">{item.role}</span>
                <span className="text-gray-600">{formatNumber(item.hours)} h</span>
                <span className="font-medium text-gray-800">{formatNumber(item.cost)} Kč</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {machinery.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Technika</h4>
          <div className="space-y-2">
            {machinery.map((item) => (
              <div key={item.id} className="flex justify-between text-sm bg-white border border-gray-200 rounded-lg p-2">
                <span className="text-gray-700">{item.name}</span>
                <span className="text-gray-600">{formatNumber(item.hours)} h</span>
                <span className="font-medium text-gray-800">{formatNumber(item.cost)} Kč</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
