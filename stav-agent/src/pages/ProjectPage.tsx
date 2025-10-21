import React, { useCallback, useEffect, useMemo, useState } from 'react';
import ChatPanel, { type ChatMessage } from '../components/ChatPanel';
import ActionBar from '../components/ActionBar';
import Toast from '../components/common/Toast';
import type { ChatResponse } from '../services/chatApi';
import { getProjects } from '../utils/api';

interface ToastState {
  message: string;
  type: 'info' | 'error' | 'success';
}

interface ProjectSummary {
  id?: string;
  project_id?: string;
  name?: string;
  title?: string;
}

const createId = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`;

const ProjectPage: React.FC = () => {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | undefined>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeRequests, setActiveRequests] = useState(0);
  const [toast, setToast] = useState<ToastState | null>(null);

  const isBusy = activeRequests > 0;

  const handleError = useCallback((message: string) => {
    console.error(message);
    setToast({ message: `Chyba požadavku: ${message}`, type: 'error' });
  }, []);

  useEffect(() => {
    const loadProjects = async () => {
      try {
        const res = await getProjects();
        const projectList = (res?.data?.projects as ProjectSummary[]) || [];
        setProjects(projectList);
        if (projectList.length > 0) {
          const firstId = projectList[0].project_id || projectList[0].id;
          setSelectedProjectId(firstId);
        }
      } catch (error) {
        handleError(error instanceof Error ? error.message : 'Nepodařilo se načíst projekty');
      }
    };

    void loadProjects();
  }, [handleError]);

  useEffect(() => {
    setMessages([]);
  }, [selectedProjectId]);

  const appendMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const handleLoadingChange = useCallback((loading: boolean) => {
    setActiveRequests((prev) => {
      if (loading) {
        return prev + 1;
      }
      return Math.max(0, prev - 1);
    });
  }, []);

  const handleActionStart = useCallback(
    (label: string) => {
      const systemMessage: ChatMessage = {
        id: createId(),
        role: 'system',
        text: `Spouštím akci: ${label}`,
        createdAt: new Date().toISOString(),
      };
      appendMessage(systemMessage);
    },
    [appendMessage],
  );

  const handleActionComplete = useCallback(
    (response: ChatResponse, label: string) => {
      const assistantMessage: ChatMessage = {
        id: createId(),
        role: 'assistant',
        text: response.response || `Akce ${label} dokončena bez odpovědi`,
        artifact: response.artifact,
        createdAt: new Date().toISOString(),
      };
      appendMessage(assistantMessage);
    },
    [appendMessage],
  );

  const selectedProject = useMemo(
    () => projects.find((project) => (project.project_id || project.id) === selectedProjectId),
    [projects, selectedProjectId],
  );

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="mx-auto flex max-w-5xl flex-col gap-4 px-4">
        <header className="flex flex-col justify-between gap-3 rounded-lg bg-white p-4 shadow-sm md:flex-row md:items-center">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Stav Agent</h1>
            <p className="text-sm text-gray-500">Ptej se na projekt a spouštěj rychlé akce.</p>
            {selectedProjectId && (
              <p className="text-xs text-gray-400">Aktuální projekt: {selectedProject?.name || selectedProject?.title || selectedProjectId}</p>
            )}
          </div>
          <div className="flex flex-col gap-1 text-sm">
            <label htmlFor="project" className="font-medium text-gray-700">
              Projekt
            </label>
            <select
              id="project"
              value={selectedProjectId ?? ''}
              onChange={(event) =>
                setSelectedProjectId(event.target.value ? event.target.value : undefined)
              }
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            >
              <option value="" disabled>
                Vyber projekt
              </option>
              {projects.map((project) => {
                const value = project.project_id || project.id || '';
                return (
                  <option key={value} value={value}>
                    {project.name || project.title || value}
                  </option>
                );
              })}
            </select>
          </div>
        </header>

        <ActionBar
          projectId={selectedProjectId}
          disabled={!selectedProjectId || isBusy}
          onActionStart={handleActionStart}
          onActionComplete={handleActionComplete}
          onError={handleError}
          onLoadingChange={handleLoadingChange}
        />

        <ChatPanel
          projectId={selectedProjectId}
          messages={messages}
          onAppendMessage={appendMessage}
          disabled={!selectedProjectId || isBusy}
          onError={handleError}
          onLoadingChange={handleLoadingChange}
        />
      </div>

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
};

export default ProjectPage;
