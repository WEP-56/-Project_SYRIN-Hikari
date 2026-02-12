// ============================================================================
// Type Definitions
// ============================================================================

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  emotion?: string;
  isStreaming?: boolean;
}

export interface Settings {
  provider: string;
  model: string;
  apiKey: string;
  apiBase: string;
  maxIterations: number;
  braveApiKey?: string;
  search_provider?: string;
  telegramToken?: string;
  telegramEnabled?: boolean;
  user_name?: string;
  role_name?: string;
  emotionEnabled: boolean;
  autoExecute: boolean;
  enableUserModeling?: boolean;
  proactiveEnabled?: boolean;
}

export interface Session {
  id: string;
  title: string;
  updated_at: string;
  created_at: string;
  preview: string;
}

export type ConnectionStatus = 'connected' | 'connecting' | 'error';

export interface ChatResponse {
  success: boolean;
  response: string;
  session_id: string;
  emotion?: string;
  thoughts?: string[];
  error?: string;
}

export interface ToolResponse {
  success: boolean;
  result?: string;
  error?: string;
  execution_time?: number;
}

export interface SystemStatus {
  status: string;
  provider?: string;
  model?: string;
  workspace: string;
  tools_available: string[];
}

export interface Tool {
  name: string;
  description: string;
}
