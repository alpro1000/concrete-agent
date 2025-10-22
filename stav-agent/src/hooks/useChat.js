import { useCallback } from 'react';
import { useAppStore } from '../store/appStore';
import { sendChatMessage, triggerAction } from '../utils/api';

export const useChat = () => {
  const {
    messages,
    addMessage,
    isLoading,
    setIsLoading,
    selectedArtifact,
    setSelectedArtifact,
  } = useAppStore();

  const sendMessage = useCallback(
    async (projectId, message) => {
      if (!projectId || !message || !message.trim() || isLoading) return;

      addMessage({ type: 'user', text: message });
      setIsLoading(true);

      try {
        const res = await sendChatMessage(projectId, message);
        addMessage({
          type: 'ai',
          text: res.data?.response || 'Žádná odpověď',
        });
        if (res.data?.artifact) setSelectedArtifact(res.data.artifact);
      } catch (error) {
        addMessage({
          type: 'ai',
          text: 'Chyba: ' + (error.response?.data?.error || error.message),
        });
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, addMessage, setIsLoading, setSelectedArtifact]
  );

  const performAction = useCallback(
    async (projectId, descriptor = {}) => {
      const {
        apiAction,
        action: explicitAction,
        label,
        options,
        freeFormQuery,
        positionId,
      } = descriptor;

      const action = explicitAction || apiAction;

      if (!projectId || !action || isLoading) return;

      setIsLoading(true);
      try {
        const res = await triggerAction({
          projectId,
          action,
          options,
          positionId,
          freeFormQuery,
        });
        addMessage({
          type: 'ai',
          text:
            res.data?.response ||
            (label ? `Akce ${label} dokončena` : 'Akce dokončena'),
        });
        if (res.data?.artifact) setSelectedArtifact(res.data.artifact);
      } catch (error) {
        addMessage({
          type: 'ai',
          text: 'Chyba akce: ' + error.message,
        });
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, addMessage, setIsLoading, setSelectedArtifact]
  );

  return { messages, sendMessage, performAction, isLoading, selectedArtifact };
};
