import { useMutation } from '@tanstack/react-query';
import { sendChatMessage, triggerAction } from '../utils/api';
import { useAppStore } from '../store/appStore';

export function useChat() {
  const {
    currentProject,
    addMessage,
    setSelectedArtifact,
    setIsLoading,
  } = useAppStore();

  const { mutateAsync: sendMessage } = useMutation({
    mutationFn: async (text) => {
      if (!currentProject) {
        throw new Error('Nebyl vybrán projekt');
      }
      const response = await sendChatMessage(currentProject.project_id ?? currentProject.id, text);
      return response.data;
    },
  });

  const { mutateAsync: runAction } = useMutation({
    mutationFn: async (action) => {
      if (!currentProject) {
        throw new Error('Nebyl vybrán projekt');
      }
      const response = await triggerAction(currentProject.project_id ?? currentProject.id, action);
      return response.data;
    },
  });

  const handleSendMessage = async (text) => {
    addMessage({ id: Date.now(), type: 'user', text });
    setIsLoading(true);
    try {
      const data = await sendMessage(text);
      addMessage({ id: Date.now() + 1, type: 'ai', text: data.response });
      if (data.artifact) {
        setSelectedArtifact(data.artifact);
      }
    } catch (error) {
      addMessage({
        id: Date.now() + 1,
        type: 'ai',
        text: error.message || 'Došlo k chybě při odesílání zprávy',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleAction = async (action) => {
    setIsLoading(true);
    try {
      const data = await runAction(action);
      addMessage({ id: Date.now(), type: 'ai', text: data.response });
      if (data.artifact) {
        setSelectedArtifact(data.artifact);
      }
    } catch (error) {
      addMessage({
        id: Date.now() + 1,
        type: 'ai',
        text: error.message || 'Akci se nepodařilo provést',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return {
    handleSendMessage,
    handleAction,
  };
}
