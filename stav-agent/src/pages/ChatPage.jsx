import React, { useState, useEffect, useCallback } from 'react';
import { useAppStore } from '../store/appStore';
import {
  sendChatMessage,
  triggerAction,
  getProjects,
  uploadFiles,
} from '../utils/api';

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
    messages,
    addMessage,
    currentProject,
    setCurrentProject,
    selectedArtifact,
    setSelectedArtifact,
    isLoading,
    setIsLoading,
    sidebarOpen,
    setSidebarOpen,
    clearMessages,
  } = useAppStore();

  // Загрузить проекты при монтировании
  useEffect(() => {
    loadProjects();
  }, []);

  // Очистить при смене проекта
  useEffect(() => {
    if (currentProject) {
      clearMessages();
      setSelectedArtifact(null);
    }
  }, [currentProject, clearMessages, setSelectedArtifact]);

  const loadProjects = useCallback(async () => {
    try {
      const res = await getProjects();
      setProjects(res.data?.projects || []);
    } catch (err) {
      console.error('Failed to load projects:', err);
    }
  }, []);

  const handleSendMessage = useCallback(async (text) => {
    if (!currentProject || !text.trim() || isLoading) return;

    addMessage({
      type: 'user',
      text,
    });

    setIsLoading(true);
    try {
      const res = await sendChatMessage(currentProject.project_id, text);

      addMessage({
        type: 'ai',
        text: res.data.response || 'Žádná odpověď',
      });

      if (res.data.artifact) {
        setSelectedArtifact(res.data.artifact);
      }
    } catch (error) {
      console.error('Chat error:', error);
      addMessage({
        type: 'ai',
        text: 'Chyba: Nepodařilo se zpracovat požadavek. Zkus později.',
      });
    } finally {
      setIsLoading(false);
    }
  }, [currentProject, isLoading, addMessage, setIsLoading, setSelectedArtifact]);

  const handleQuickAction = useCallback(async (action) => {
    if (!currentProject || isLoading) return;

    addMessage({
      type: 'user',
      text: `Akce: ${action}`,
    });

    setIsLoading(true);
    try {
      const res = await triggerAction(currentProject.project_id, action);

      addMessage({
        type: 'ai',
        text: res.data.response || 'Zpracování...',
      });

      if (res.data.artifact) {
        setSelectedArtifact(res.data.artifact);
      }
    } catch (error) {
      console.error('Action error:', error);
      addMessage({
        type: 'ai',
        text: 'Chyba: Akce se nezdařila.',
      });
    } finally {
      setIsLoading(false);
    }
  }, [currentProject, isLoading, addMessage, setIsLoading, setSelectedArtifact]);

  const handleFileUpload = useCallback(async (files) => {
    if (!currentProject || !files.length) return;

    setIsLoading(true);
    try {
      const res = await uploadFiles(currentProject.project_id, Array.from(files));

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
  }, [currentProject, isLoading, addMessage, setIsLoading, setSelectedArtifact]);

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
