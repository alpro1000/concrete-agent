import React, { useState, useEffect, useCallback } from 'react';
import { useAppStore } from '../store/appStore';
import { getProjects, uploadFiles } from '../utils/api';
import { useChat } from '../hooks/useChat';

import Header from '../components/layout/Header';
import Sidebar from '../components/layout/Sidebar';
import ChatWindow from '../components/chat/ChatWindow';
import QuickActions from '../components/chat/QuickActions';
import InputArea from '../components/chat/InputArea';
import ArtifactPanel from '../components/layout/ArtifactPanel';

export default function ChatPage() {
  const [projects, setProjects] = useState([]);
  const [uploadProgress, setUploadProgress] = useState(null);
  const fileInputRef = React.useRef(null);

  const {
    addMessage,
    currentProject,
    setCurrentProject,
    setSelectedArtifact,
    setIsLoading,
    sidebarOpen,
    setSidebarOpen,
    clearMessages,
  } = useAppStore();
  const { messages, sendMessage, performAction, isLoading, selectedArtifact } = useChat();

  const loadProjects = useCallback(async () => {
    try {
      const res = await getProjects();
      setProjects(res.data?.projects || []);
    } catch (err) {
      console.error('Failed to load projects:', err);
    }
  }, []);

  // Загрузить проекты при монтировании
  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // Очистить при смене проекта
  useEffect(() => {
    if (currentProject) {
      clearMessages();
      setSelectedArtifact(null);
    }
  }, [currentProject, clearMessages, setSelectedArtifact]);

  const handleSendMessage = useCallback(
    (text) => {
      const projectId = currentProject?.project_id ?? currentProject?.id;
      if (!projectId) return;

      sendMessage(projectId, text);
    },
    [currentProject, sendMessage]
  );

  const handleQuickAction = useCallback(
    (action) => {
      if (!action) return;
      const projectId = currentProject?.project_id ?? currentProject?.id;
      if (!projectId) return;

      const label = action.label || action.czech_name || action.apiAction || action.id;
      addMessage({
        type: 'user',
        text: `Akce: ${label}`,
      });
      performAction(projectId, action);
    },
    [addMessage, currentProject, performAction]
  );

  const handleFileUpload = useCallback(async (files) => {
    const projectId = currentProject?.project_id ?? currentProject?.id;
    if (!projectId || !files.length || isLoading) return;

    setIsLoading(true);
    try {
      const res = await uploadFiles(projectId, Array.from(files));

      addMessage({
        type: 'ai',
        text: `Soubory nahrány: ${res.data.message || 'Hotovo'}`,
      });

      if (res.data.artifact) {
        setSelectedArtifact(res.data.artifact);
      }
    } catch (error) {
      console.error('Upload error:', error);
      addMessage({
        type: 'ai',
        text: 'Chyba: Nahrávání selhalo.',
      });
    } finally {
      setIsLoading(false);
      setUploadProgress(null);
    }
  }, [addMessage, currentProject, isLoading, setIsLoading, setSelectedArtifact]);

  const handleNewProject = useCallback(() => {
    const name = prompt('Název nového projektu:');
    if (name) {
      // TODO: Implementovat createProject
      console.log('Create project:', name);
    }
  }, []);

  return (
    <div className="h-screen flex flex-col bg-gray-50 overflow-hidden">
      <Header
        onNewProject={handleNewProject}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        currentProject={currentProject}
      />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(!sidebarOpen)}
          projects={projects}
          onSelectProject={setCurrentProject}
          currentProject={currentProject}
        />

        <div className="flex-1 flex flex-col overflow-hidden">
          <ChatWindow messages={messages} isLoading={isLoading} />
          {currentProject && <QuickActions onAction={handleQuickAction} isLoading={isLoading} />}
          <InputArea
            onSend={handleSendMessage}
            onUpload={() => fileInputRef.current?.click()}
            isLoading={isLoading}
            uploadProgress={uploadProgress}
          />
          <input
            ref={fileInputRef}
            type="file"
            multiple
            hidden
            onChange={(e) => handleFileUpload(e.target.files)}
            accept=".pdf,.xlsx,.xls,.png,.jpg,.jpeg,.dwg"
          />
        </div>

        <ArtifactPanel artifact={selectedArtifact} isLoading={isLoading} />
      </div>
    </div>
  );
}
