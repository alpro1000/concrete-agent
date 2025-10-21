import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAppStore } from '../store/appStore';
import {
  sendChatMessage,
  triggerAction,
  getProjects,
  uploadFiles,
  getProjectStatus,
} from '../utils/api';
import { QUICK_ACTIONS, MESSAGE_TYPES } from '../utils/constants';

import Header from '../components/layout/Header';
import Sidebar from '../components/layout/Sidebar';
import ChatWindow from '../components/chat/ChatWindow';
import QuickActions from '../components/chat/QuickActions';
import InputArea from '../components/chat/InputArea';
import ArtifactPanel from '../components/layout/ArtifactPanel';

export default function ChatPage() {
  const fileInputRef = useRef(null);
  const [uploadProgress, setUploadProgress] = useState(null);

  const {
    projects,
    setProjects,
    messages,
    addMessage,
    currentProject,
    setCurrentProject,
    selectedArtifact,
    setSelectedArtifact,
    isLoading,
    setIsLoading,
    error,
    setError,
    clearError,
    sidebarOpen,
    setSidebarOpen,
    clearMessages,
  } = useAppStore();

  const loadProjects = useCallback(async () => {
    try {
      const res = await getProjects();
      const fetchedProjects = res.data?.projects || [];
      setProjects(fetchedProjects);

      if (!currentProject && fetchedProjects.length > 0) {
        setCurrentProject(fetchedProjects[0]);
      }
      clearError();
    } catch (err) {
      console.error('Failed to load projects', err);
      setError('Nepodařilo se načíst projekty');
    }
  }, [clearError, currentProject, setCurrentProject, setError, setProjects]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const checkProjectStatus = useCallback(async () => {
    if (!currentProject) return;
    try {
      const res = await getProjectStatus(currentProject.project_id ?? currentProject.id);
      if (res.data?.status === 'AUDITED') {
        addMessage({
          type: MESSAGE_TYPES.SYSTEM,
          text: 'Projekt automaticky naauditován. Zkontroluj výsledky.',
        });
      }
    } catch (err) {
      console.error('Failed to fetch project status', err);
    }
  }, [addMessage, currentProject]);

  useEffect(() => {
    if (currentProject) {
      clearMessages();
      setSelectedArtifact(null);
      checkProjectStatus();
    }
  }, [currentProject, clearMessages, setSelectedArtifact, checkProjectStatus]);

  const handleSend = useCallback(
    async (text) => {
      if (!currentProject) {
        addMessage({
          type: MESSAGE_TYPES.AI,
          text: 'Vyber prosím projekt před odesláním zprávy.',
        });
        return;
      }

      clearError();
      addMessage({ type: MESSAGE_TYPES.USER, text });
      setIsLoading(true);

      try {
        const res = await sendChatMessage(currentProject.project_id ?? currentProject.id, text);
        const data = res.data;
        if (data?.response) {
          addMessage({ type: MESSAGE_TYPES.AI, text: data.response });
        }
        if (data?.artifact) {
          setSelectedArtifact(data.artifact);
        }
      } catch (err) {
        console.error('Failed to send chat message', err);
        const message = err.response?.data?.message || 'Došlo k chybě při odesílání zprávy.';
        setError(message);
        addMessage({ type: MESSAGE_TYPES.SYSTEM, text: message });
      } finally {
        setIsLoading(false);
      }
    },
    [addMessage, clearError, currentProject, setError, setIsLoading, setSelectedArtifact],
  );

  const handleQuickAction = useCallback(
    async (actionId) => {
      if (!currentProject) {
        addMessage({
          type: MESSAGE_TYPES.AI,
          text: 'Vyber prosím projekt před spuštěním akce.',
        });
        return;
      }

      const action = QUICK_ACTIONS.find((item) => item.id === actionId);
      if (!action) return;

      clearError();
      setIsLoading(true);

      try {
        const res = await triggerAction(
          currentProject.project_id ?? currentProject.id,
          action.apiAction,
        );
        const data = res.data;
        if (data?.response) {
          addMessage({ type: MESSAGE_TYPES.AI, text: data.response });
        }
        if (data?.artifact) {
          setSelectedArtifact(data.artifact);
        }
      } catch (err) {
        console.error('Failed to trigger action', err);
        const message = err.response?.data?.message || 'Akci se nepodařilo provést.';
        setError(message);
        addMessage({ type: MESSAGE_TYPES.SYSTEM, text: message });
      } finally {
        setIsLoading(false);
      }
    },
    [addMessage, clearError, currentProject, setError, setIsLoading, setSelectedArtifact],
  );

  const handleUploadClick = useCallback(() => {
    setUploadProgress(null);
    fileInputRef.current?.click();
  }, []);

  const handleFilesSelected = useCallback(
    async (event) => {
      const files = Array.from(event.target.files ?? []);
      if (!files.length) {
        return;
      }

      if (!currentProject) {
        addMessage({
          type: MESSAGE_TYPES.AI,
          text: 'Vyber prosím projekt před nahráním souborů.',
        });
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
        return;
      }

      clearError();
      setIsLoading(true);
      setUploadProgress(0);

      try {
        await uploadFiles(currentProject.project_id ?? currentProject.id, files, setUploadProgress);
        addMessage({
          type: MESSAGE_TYPES.SYSTEM,
          text: 'Soubor byl úspěšně nahrán. Agent začne zpracování.',
        });
      } catch (err) {
        console.error('File upload failed', err);
        const message = err.response?.data?.message || 'Nahrání souboru se nezdařilo.';
        setError(message);
        addMessage({ type: MESSAGE_TYPES.SYSTEM, text: message });
      } finally {
        setIsLoading(false);
        setUploadProgress(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }
    },
    [addMessage, clearError, currentProject, setError, setIsLoading, setUploadProgress],
  );

  const handleSelectProject = useCallback(
    (project) => {
      setCurrentProject(project);
    },
    [setCurrentProject],
  );

  const handleToggleSidebar = useCallback(() => {
    setSidebarOpen((prev) => !prev);
  }, [setSidebarOpen]);

  const handleDismissError = useCallback(() => {
    clearError();
  }, [clearError]);

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <Header
        onNewProject={() => console.log('New project')}
        onToggleSidebar={handleToggleSidebar}
        currentProject={currentProject}
      />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          isOpen={sidebarOpen}
          onToggle={handleToggleSidebar}
          projects={projects}
          onSelectProject={handleSelectProject}
          currentProject={currentProject}
        />

        <div className="flex-1 flex flex-col">
          {error && (
            <div className="px-4 pt-4">
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded flex items-center justify-between">
                <span>{error}</span>
                <button onClick={handleDismissError} className="text-sm text-red-600 hover:underline">
                  Zavřít
                </button>
              </div>
            </div>
          )}

          <ChatWindow messages={messages} isLoading={isLoading} />
          <QuickActions onAction={handleQuickAction} isLoading={isLoading} />
          <InputArea
            onSend={handleSend}
            onUpload={handleUploadClick}
            isLoading={isLoading}
            uploadProgress={uploadProgress}
          />
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            multiple
            onChange={handleFilesSelected}
          />
        </div>

        <ArtifactPanel artifact={selectedArtifact} isLoading={isLoading} />
      </div>
    </div>
  );
}
