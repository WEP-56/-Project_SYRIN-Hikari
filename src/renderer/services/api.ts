import axios from 'axios';
import { ChatResponse, ToolResponse, SystemStatus, Settings, Tool } from '../types';

let baseURL = 'http://127.0.0.1:8888';

// Try to get API URL from Electron
if (typeof window !== 'undefined' && window.electronAPI) {
  window.electronAPI.getApiUrl().then((url) => {
    baseURL = url;
    apiClient.defaults.baseURL = url;
  });
}

const apiClient = axios.create({
  baseURL,
  timeout: 120000, // 2 minutes for long operations
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  if (baseURL && config.baseURL !== baseURL) {
    config.baseURL = baseURL;
  }
  return config;
});

export const api = {
  // Chat
  async sendMessage(message: string, sessionId?: string, systemPrompt?: string): Promise<ChatResponse | null> {
    try {
      const response = await apiClient.post('/chat', {
        message,
        session_id: sessionId,
        system_prompt: systemPrompt,
        context: {},
      });
      return response.data;
    } catch (error) {
      console.error('Chat error:', error);
      return null;
    }
  },

  // Tools
  async executeTool(task: string, context: Record<string, any> = {}): Promise<ToolResponse> {
    try {
      const response = await apiClient.post<ToolResponse>('/execute', { task, context });
      return response.data;
    } catch (error) {
      console.error('Execute tool error:', error);
      return { success: false, error: 'Failed to execute tool' };
    }
  },

  async runSandboxCode(code: string, language: string = 'python'): Promise<ToolResponse> {
    try {
      const response = await apiClient.post<ToolResponse>('/sandbox/run', { code, language });
      return response.data;
    } catch (error) {
      console.error('Run sandbox code error:', error);
      return { success: false, error: 'Failed to run code' };
    }
  },

  async getTools(): Promise<Tool[]> {
    try {
      const response = await apiClient.get('/tools');
      return response.data.tools || [];
    } catch (error) {
      console.error('Get tools error:', error);
      return [];
    }
  },

  // Memories
  async getMemories(limit?: number, typeFilter?: string) {
    try {
      const response = await apiClient.get('/memories', {
        params: { limit, type_filter: typeFilter }
      });
      return response.data.memories || [];
    } catch (error) {
      console.error('Get memories error:', error);
      return [];
    }
  },

  async getMemoryContext(): Promise<string> {
    try {
      const response = await apiClient.get('/memories/context');
      return response.data.context || '';
    } catch (error) {
      console.error('Get memory context error:', error);
      return '';
    }
  },

  async addFact(fact: string): Promise<boolean> {
    try {
      await apiClient.post('/memories/fact', null, {
        params: { fact }
      });
      return true;
    } catch (error) {
      console.error('Add fact error:', error);
      return false;
    }
  },

  // Sessions
  async getSessions(): Promise<any[]> {
    try {
      const response = await apiClient.get('/sessions');
      return response.data.sessions || [];
    } catch (error) {
      console.error('Get sessions error:', error);
      return [];
    }
  },

  async getSession(sessionId: string): Promise<any | null> {
    try {
      const response = await apiClient.get(`/sessions/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error('Get session error:', error);
      return null;
    }
  },

  async createSession(title?: string): Promise<any | null> {
    try {
      const response = await apiClient.post('/sessions', { title });
      return response.data.session;
    } catch (error) {
      console.error('Create session error:', error);
      return null;
    }
  },

  async updateSession(sessionId: string, title: string): Promise<boolean> {
    try {
      await apiClient.patch(`/sessions/${sessionId}`, { title });
      return true;
    } catch (error) {
      console.error('Update session error:', error);
      return false;
    }
  },

  async deleteSession(sessionId: string): Promise<boolean> {
    try {
      await apiClient.delete(`/sessions/${sessionId}`);
      return true;
    } catch (error) {
      console.error('Delete session error:', error);
      return false;
    }
  },

  // Status
  async getStatus(): Promise<SystemStatus | null> {
    try {
      const response = await apiClient.get('/status');
      return response.data;
    } catch (error) {
      console.error('Status error:', error);
      return null;
    }
  },

  // Config
  async getConfig(): Promise<Partial<Settings> | null> {
    try {
      const response = await apiClient.get('/config');
      return response.data;
    } catch (error) {
      console.error('Get config error:', error);
      return null;
    }
  },

  async updateConfig(config: Partial<Settings>): Promise<boolean> {
    try {
      await apiClient.post('/config', config);
      return true;
    } catch (error) {
      console.error('Update config error:', error);
      return false;
    }
  },

  // Soul
  async getSoulState(): Promise<any | null> {
    try {
      const response = await apiClient.get('/soul/state');
      return response.data;
    } catch (error) {
      console.error('Get soul state error:', error);
      return null;
    }
  },

  async getNotifications() {
    try {
      const response = await apiClient.get('/notifications');
      return response.data;
    } catch (error) {
      console.error('Get notifications error:', error);
      return { notifications: [] };
    }
  },

  // Server management
  async restartServer(): Promise<{ success: boolean; error?: string }> {
    if (typeof window !== 'undefined' && window.electronAPI) {
      return window.electronAPI.restartServer();
    }
    return { success: false, error: 'Not running in Electron' };
  },

  async testTelegram(): Promise<{success: boolean, message?: string, error?: string}> {
    try {
      const response = await apiClient.post('/telegram/test');
      return response.data;
    } catch (error: any) {
      console.error('Telegram test error:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || error.message || 'Connection failed' 
      };
    }
  },

  async resetSystem(): Promise<{success: boolean, message?: string, error?: string}> {
    try {
        const response = await apiClient.post('/system/reset', null, { params: { confirm: true } });
        return response.data;
    } catch (error: any) {
        console.error('Reset system error:', error);
        return { 
            success: false, 
            error: error.response?.data?.detail || error.message || 'Reset failed' 
        };
    }
  },
};
