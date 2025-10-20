import { create } from 'zustand';

export const useAppStore = create((set) => ({
  // Auth
  user: null,
  setUser: (user) => set({ user }),

  // Projects
  currentProject: null,
  setCurrentProject: (project) => set({ currentProject: project }),

  // Chat
  messages: [],
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  clearMessages: () => set({ messages: [] }),

  // Artifact
  selectedArtifact: null,
  setSelectedArtifact: (artifact) => set({ selectedArtifact: artifact }),

  // Loading
  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),
}));
