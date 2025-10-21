import axios, { isAxiosError } from 'axios';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  '';

const chatClient = axios.create({
  baseURL: API_BASE_URL || undefined,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

export type ChatAction =
  | 'audit_positions'
  | 'materials_summary'
  | 'breakdown_structure'
  | 'calculate_resources';

export type ChatArtifact =
  | {
      type: 'audit_result';
      title: string;
      data: {
        green: number;
        amber: number;
        red: number;
        issues: Array<{
          code: string;
          description: string;
          problem: string;
        }>;
      };
    }
  | {
      type: 'materials_summary';
      title: string;
      data: {
        materials: Array<{
          name: string;
          quantity: number;
          unit: string;
        }>;
        total_weight?: number;
      };
    }
  | {
      type: 'position_breakdown';
      title: string;
      data: {
        positions: Array<{
          code: string;
          description: string;
          unit: string;
          quantity: number;
        }>;
      };
    }
  | {
      type: 'resources_calc';
      title: string;
      data: {
        labor_hours: number;
        equipment: Array<{
          name: string;
          hours: number;
        }>;
        materials_cost: number;
      };
    }
  | undefined;

export interface ChatResponse {
  response: string;
  artifact?: ChatArtifact;
  metadata?: Record<string, unknown>;
}

const toError = (error: unknown): Error => {
  if (isAxiosError(error)) {
    const details =
      (typeof error.response?.data === 'object' && error.response?.data && 'error' in error.response.data
        ? String((error.response.data as { error?: unknown }).error)
        : undefined) || error.message || 'Neznámá chyba';
    return new Error(details);
  }
  if (error instanceof Error) {
    return error;
  }
  return new Error('Neznámá chyba');
};

export const sendMessage = async (projectId: string, message: string): Promise<ChatResponse> => {
  try {
    const { data } = await chatClient.post<ChatResponse>('/api/chat/message', {
      project_id: projectId,
      message,
      include_history: true,
    });
    return data;
  } catch (error) {
    throw toError(error);
  }
};

export const triggerAction = async (
  projectId: string,
  action: ChatAction,
  positionId?: string,
): Promise<ChatResponse> => {
  try {
    const { data } = await chatClient.post<ChatResponse>('/api/chat/action', {
      project_id: projectId,
      action,
      position_id: positionId,
    });
    return data;
  } catch (error) {
    throw toError(error);
  }
};
