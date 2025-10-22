import { useMemo } from 'react';
import {
  getProjects,
  getProject,
  createProject,
  uploadFiles,
  sendChatMessage,
  triggerAction,
  getProjectResults,
  getProjectStatus,
  getProjectFiles,
} from '../utils/api';

export function useAPI() {
  return useMemo(
    () => ({
      getProjects,
      getProject,
      createProject,
      uploadFiles,
      sendChatMessage,
      triggerAction,
      getProjectResults,
      getProjectStatus,
      getProjectFiles,
    }),
    [],
  );
}
