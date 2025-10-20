import React from 'react';
import { formatNumber } from '../../utils/helpers';

export default function PositionBreakdown({ data = {} }) {
  const items = data.positions ?? [];

  if (!items.length) {
    return <div className="text-sm text-gray-500">Žádná data k zobrazení.</div>;
  }

  return (
    <div className="space-y-3">
      <div className="text-xs uppercase tracking-wide text-gray-500">Struktura</div>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.id} className="bg-white p-3 rounded-lg shadow-sm border border-gray-200">
            <div className="flex justify-between text-sm font-semibold text-gray-800">
              <span>{item.code} – {item.name}</span>
              <span>{formatNumber(item.total_cost)} Kč</span>
            </div>
            {item.children?.length ? (
              <div className="mt-2 pl-3 border-l border-gray-200 space-y-1">
                {item.children.map((child) => (
                  <div key={child.id} className="flex justify-between text-xs text-gray-600">
                    <span>{child.code} – {child.name}</span>
                    <span>{formatNumber(child.total_cost)} Kč</span>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}
