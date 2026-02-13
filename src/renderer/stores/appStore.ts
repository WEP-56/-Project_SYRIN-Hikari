/**
 * Project SYRIN - 前端状态管理
 * 管理应用级别的状态：模式切换、用户配置、消息历史等
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '../services/api';
import { Session } from '../types';

export type Emotion = 'normal' | 'happy' | 'sad' | 'clingy' | 'jealous' | 'angry' | 'surprised';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  emotion?: Emotion;
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
  enableUserModeling: boolean;
}

interface AppState {
  // 消息
  messages: Message[];
  addMessage: (message: Message) => void;
  clearMessages: () => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  
  // 会话管理
  sessions: Session[];
  currentSessionId: string | null;
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  soulSidebarOpen: boolean;
  toggleSoulSidebar: () => void;
  loadSessions: () => Promise<void>;
  createSession: () => Promise<void>;
  updateSession: (id: string, title: string) => Promise<void>;
  selectSession: (id: string) => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
  
  // 设置
  settings: Settings;
  updateSettings: (settings: Partial<Settings>) => void;
  
  // UI 状态
  isTyping: boolean;
  setIsTyping: (typing: boolean) => void;
  connectionStatus: 'connected' | 'connecting' | 'error';
  setConnectionStatus: (status: 'connected' | 'connecting' | 'error') => void;
  
  // 当前情绪
  currentEmotion: Emotion;
  setCurrentEmotion: (emotion: Emotion) => void;
  
  // Soul State
  soulState: any | null;
  loadSoulState: () => Promise<void>;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // 初始状态
      messages: [
        {
          id: 'welcome',
          role: 'assistant',
          content: '你好呀，主人～ 💕\n\n我是 Hikari (光)，会一直陪着你的！',
          timestamp: Date.now(),
          emotion: 'happy',
        },
      ],
      
      sessions: [],
      currentSessionId: null,
      sidebarOpen: false,
      soulSidebarOpen: false,
      
      settings: {
        provider: 'openai',
        model: 'gpt-4o-mini',
        apiKey: '',
        apiBase: '',
        maxIterations: 20,
        braveApiKey: '',
        search_provider: 'brave',
        telegramToken: '',
        telegramEnabled: false,
        user_name: 'User',
        role_name: 'Assistant',
        emotionEnabled: true,
        autoExecute: true,
        enableUserModeling: true,
        proactiveEnabled: false,
      },
      
      isTyping: false,
      connectionStatus: 'connecting',
      currentEmotion: 'happy',
      soulState: null,
      
      // Actions
      addMessage: (message) => set((state) => ({ 
        messages: [...state.messages, message] 
      })),
      
      clearMessages: () => set({ 
        messages: [{
          id: 'cleared',
          role: 'assistant',
          content: '聊天记录已清除～ 让我们重新开始吧！💕',
          timestamp: Date.now(),
          emotion: 'happy',
        }]
      }),
      
      updateMessage: (id, updates) => set((state) => ({
        messages: state.messages.map((msg) =>
          msg.id === id ? { ...msg, ...updates } : msg
        ),
      })),
      
      // Session Actions
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      toggleSoulSidebar: () => set((state) => ({ soulSidebarOpen: !state.soulSidebarOpen })), 
      
      loadSessions: async () => {
        const sessions = await api.getSessions();
        set({ sessions });
      },
      
      createSession: async () => {
        // Create session on backend
        const session = await api.createSession();
        if (session) {
          // Immediately reload sessions to ensure consistency
          const sessions = await api.getSessions();
          set({ 
            sessions,
            currentSessionId: session.id,
            messages: [{
              id: 'welcome',
              role: 'assistant',
              content: '新的开始... 这次只属于我们两个人哦～ 💕',
              timestamp: Date.now(),
              emotion: 'happy',
            }]
          });
        }
      },
      
      updateSession: async (id, title) => {
        await api.updateSession(id, title);
        await get().loadSessions();
      },
      
      selectSession: async (id) => {
        set({ isTyping: true });
        try {
          const sessionData = await api.getSession(id);
          if (sessionData && sessionData.messages) {
            // Convert backend messages to frontend format if needed
            // Backend: { role, content, timestamp, ... }
            // Frontend: Message interface
            const messages = sessionData.messages.map((msg: any, index: number) => ({
              id: msg.metadata?.message_id || `msg-${index}`,
              role: msg.role,
              content: msg.content,
              timestamp: msg.timestamp ? new Date(msg.timestamp).getTime() : Date.now(),
              emotion: msg.metadata?.emotion as Emotion || 'normal'
            }));
            
            set({ 
              currentSessionId: id,
              messages: messages.length > 0 ? messages : [{
                id: 'welcome',
                role: 'assistant',
                content: '... (盯着你看) 💕',
                timestamp: Date.now(),
                emotion: 'happy',
              }]
            });
          }
        } catch (e) {
          console.error("Failed to load session", e);
        } finally {
          set({ isTyping: false });
        }
      },
      
      deleteSession: async (id) => {
        await api.deleteSession(id);
        await get().loadSessions();
        const sessions = get().sessions;
        
        // Only if deleting the current session
        if (get().currentSessionId === id) {
          if (sessions.length > 0) {
            // Select the first available session
            await get().selectSession(sessions[0].id);
          } else {
            // No sessions left, create new one
            await get().createSession();
          }
        }
      },

      updateSettings: (newSettings) => set((state) => ({
        settings: { ...state.settings, ...newSettings },
      })),
      
      setIsTyping: (isTyping) => set({ isTyping }),
      setConnectionStatus: (status) => set({ connectionStatus: status }),
      setCurrentEmotion: (emotion) => set({ currentEmotion: emotion }),
      
      loadSoulState: async () => {
        const state = await api.getSoulState();
        if (state) {
          set({ soulState: state });
          // Update emotion from soul state if available
          if (state.emotion?.primary) {
            // Map backend emotion to frontend emotion type
            const backendEmotion = state.emotion.primary.toLowerCase();
            const validEmotions: Emotion[] = ['normal', 'happy', 'sad', 'clingy', 'jealous', 'angry', 'surprised'];
            
            // Map common backend synonyms to frontend keys if needed
            let frontendEmotion: Emotion = 'normal';
            if (validEmotions.includes(backendEmotion as Emotion)) {
              frontendEmotion = backendEmotion as Emotion;
            } else {
              // Fallback mapping
              if (backendEmotion.includes('love') || backendEmotion.includes('joy')) frontendEmotion = 'happy';
              else if (backendEmotion.includes('anger')) frontendEmotion = 'angry';
              else if (backendEmotion.includes('sorrow') || backendEmotion.includes('grief')) frontendEmotion = 'sad';
              else if (backendEmotion.includes('fear')) frontendEmotion = 'surprised';
              // Default to normal for unknown
            }
            
            set({ currentEmotion: frontendEmotion });
          }
        }
      },
    }),
    {
      name: 'yandere-assistant-storage',
      partialize: (state) => ({
        settings: state.settings,
        // We don't persist messages here if we rely on backend for history, 
        // but for now let's keep it for offline capability or current view
        messages: state.messages.slice(-50), 
        currentSessionId: state.currentSessionId,
        soulState: state.soulState,
      }),
    }
  )
);

// 情绪相关的工具函数
export const emotionConfig: Record<Emotion, { emoji: string; color: string; label: string }> = {
  normal: { emoji: '🙂', color: '#9CA3AF', label: '平静' },
  happy: { emoji: '😊', color: '#F472B6', label: '开心' },
  sad: { emoji: '😢', color: '#60A5FA', label: '伤心' },
  clingy: { emoji: '🥺', color: '#F9A8D4', label: '粘人' },
  jealous: { emoji: '😤', color: '#FB923C', label: '吃醋' },
  angry: { emoji: '😠', color: '#EF4444', label: '生气' },
  surprised: { emoji: '😲', color: '#A78BFA', label: '惊讶' },
};

// 根据消息内容推测情绪（简单规则）
export function detectEmotion(content: string): Emotion {
  const lower = content.toLowerCase();
  if (lower.includes('生气') || lower.includes('讨厌') || lower.includes('笨蛋')) return 'angry';
  if (lower.includes('吃醋') || lower.includes('不要看别人') || lower.includes('嫉妒')) return 'jealous';
  if (lower.includes('粘') || lower.includes('不要走') || lower.includes('陪着我')) return 'clingy';
  if (lower.includes('伤心') || lower.includes('难过') || lower.includes('哭')) return 'sad';
  if (lower.includes('！') || lower.includes('耶') || lower.includes('开心')) return 'happy';
  if (lower.includes('？') || lower.includes('真的吗') || lower.includes('诶')) return 'surprised';
  return 'normal';
}
