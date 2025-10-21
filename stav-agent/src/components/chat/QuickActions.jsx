import React from 'react';
import { QUICK_ACTIONS } from '../../utils/constants';

export default function QuickActions({ onAction, isLoading }) {
  return (
    <div className="px-4 py-3 bg-white border-t border-gray-200">
      <div className="flex gap-2 overflow-x-auto pb-2">
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action.id}
            onClick={() => onAction(action.id)}
            disabled={isLoading}
            className={`flex-shrink-0 px-3 py-2 rounded text-sm font-medium whitespace-nowrap transition ${action.color} disabled:opacity-50 disabled:cursor-not-allowed`}
            title={action.description}
          >
            {action.icon} {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}
