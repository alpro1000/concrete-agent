import React, { useState, useEffect, useRef } from 'react';
import { useAppStore } from '../store/appStore';
import { useChat } from '../hooks/useChat';
import { useProjects } from '../hooks/useProject';
import Header from '../components/layout/Header';
import Sidebar from '../components/layout/Sidebar';
import ChatWindow from '../components/chat/ChatWindow';
import QuickActions from '../components/chat/QuickActions';
import InputArea from '../components/chat/InputArea';
import ArtifactPanel from '../components/layout/ArtifactPanel';
import { uploadFiles } from '../utils/api';

export default function ChatPage() {
  const fileInputRef = useRef(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const {
    messages,
    currentProject,
    setCurrentProject,
    selectedArtifact,
    isLoading,
    setIsLoading,
    addMessage,
  } = useAppStore();

  const { handleSendMessage, handleAction } = useChat();
  const { projectsQuery, selectProject } = useProjects();

  useEffect(() => {
    if (projectsQuery.data?.length && !currentProject) {
      setCurrentProject(projectsQuery.data[0]);
    }
  }, [projectsQuery.data, currentProject, setCurrentProject]);

  const handleSend = async (text) => {
    if (!currentProject) {
      addMessage({
        id: Date.now(),
        type: 'ai',
        text: 'Vyber prosím projekt před odesláním zprávy.',
      });
      return;
    }
    await handleSendMessage(text);
  };

  const handleQuickAction = async (action) => {
    if (!currentProject) {
      addMessage({
        id: Date.now(),
        type: 'ai',
        text: 'Vyber prosím projekt před spuštěním akce.',
      });
      return;
    }
    await handleAction(action);
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFilesSelected = async (event) => {
    const files = Array.from(event.target.files ?? []);
    if (!files.length || !currentProject) {
      return;
    }

    setIsLoading(true);
    try {
      await uploadFiles(currentProject.project_id ?? currentProject.id, files);
      addMessage({
        id: Date.now(),
        type: 'ai',
        text: 'Soubor byl úspěšně nahrán. Agent začne zpracování.',
      });
    } catch (error) {
      addMessage({
        id: Date.now(),
        type: 'ai',
        text: 'Nahrání souboru se nezdařilo.',
      });
    } finally {
      setIsLoading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <Header onNewProject={() => console.log('New project')} />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen((prev) => !prev)}
          projects={projectsQuery.data}
          onSelectProject={selectProject}
        />

        <div className="flex-1 flex flex-col">
          <ChatWindow messages={messages} isLoading={isLoading} />
          <QuickActions onAction={handleQuickAction} />
          <InputArea onSend={handleSend} onUpload={handleUploadClick} isLoading={isLoading} />
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            multiple
            onChange={handleFilesSelected}
          />
        </div>

        <ArtifactPanel artifact={selectedArtifact} />
      </div>
    </div>
  );
}
