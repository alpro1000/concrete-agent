import React, { useCallback, useState } from 'react';
import type { ChatAction, ChatResponse } from '../services/chatApi';
import { triggerAction } from '../services/chatApi';

const ACTIONS: Array<{ label: string; action: ChatAction; icon: string }> = [
  { label: 'Audit', action: 'audit_positions', icon: '🛠️' },
  { label: 'Materials', action: 'materials_summary', icon: '🧱' },
  { label: 'Breakdown', action: 'breakdown_structure', icon: '📊' },
  { label: 'Resources', action: 'calculate_resources', icon: '⚙️' },
];

interface ActionBarProps {
  projectId?: string;
  disabled?: boolean;
  onActionStart?: (label: string) => void;
  onActionComplete?: (response: ChatResponse, label: string) => void;
  onError?: (message: string) => void;
  onLoadingChange?: (loading: boolean) => void;
  positionId?: string;
}

const ActionBar: React.FC<ActionBarProps> = ({
  projectId,
  disabled = false,
  onActionStart,
  onActionComplete,
  onError,
  onLoadingChange,
  positionId,
}) => {
  const [activeAction, setActiveAction] = useState<ChatAction | null>(null);

  const handleError = useCallback(
    (message: string) => {
      if (onError) {
        onError(message);
      }
    },
    [onError],
  );

  const handleClick = useCallback(
    async (action: { label: string; action: ChatAction }) => {
      if (!projectId || disabled || activeAction) {
        if (!projectId) {
          handleError('Vyber projekt a zkus to znovu.');
        }
        return;
      }

      try {
        setActiveAction(action.action);
        onLoadingChange?.(true);
        onActionStart?.(action.label);

        const response = await triggerAction(projectId, action.action, positionId);
        onActionComplete?.(response, action.label);
      } catch (error) {
        handleError(error instanceof Error ? error.message : 'Neznámá chyba');
      } finally {
        setActiveAction(null);
        onLoadingChange?.(false);
      }
    },
    [projectId, disabled, activeAction, positionId, onActionStart, onActionComplete, onLoadingChange, handleError],
  );

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <div className="flex flex-wrap gap-3">
        {ACTIONS.map((item) => {
          const isLoading = activeAction === item.action;
          return (
            <button
              key={item.action}
              type="button"
              onClick={() => handleClick(item)}
              disabled={disabled || Boolean(activeAction)}
              className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-4 py-2 text-sm font-medium text-gray-700 transition hover:border-blue-300 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  {item.label}
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <span>{item.icon}</span>
                  {item.label}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default ActionBar;
