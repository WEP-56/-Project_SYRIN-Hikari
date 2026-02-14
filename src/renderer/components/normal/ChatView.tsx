import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Trash2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useAppStore, emotionConfig, detectEmotion } from '../../stores/appStore';
import { api } from '../../services/api';
import { generatePersonaPrompt, defaultPersonaState, updateEmotionFromInteraction, updateAffection } from '../../persona-engine/core/prompt';

export default function ChatView() {
  const { 
    messages, 
    addMessage, 
    clearMessages,
    isTyping, 
    setIsTyping,
    setCurrentEmotion,
    settings,
    currentSessionId,
    sidebarOpen,
    sessions,
    updateSession,
    soulState,
    loadSoulState
  } = useAppStore();
  
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  useEffect(() => {
    inputRef.current?.focus();
  }, [sidebarOpen]);
  
  // Ensure sessions are loaded and validated on mount
  useEffect(() => {
    useAppStore.getState().loadSessions();
    useAppStore.getState().loadSoulState();
  }, []);

  // 人格状态管理
  const [personaState, setPersonaState] = useState(defaultPersonaState);

  // Sync personaState from global soulState
  useEffect(() => {
    if (soulState) {
        setPersonaState(prev => ({
            ...prev,
            affection: soulState.metrics?.affection ?? 50,
            trust: soulState.metrics?.trust ?? 50,
            // If backend provides emotion, it's already in store.currentEmotion
            // But if we use personaState for other things, we might want to sync it too
             emotion: (soulState.emotion?.primary?.toLowerCase() as any) || prev.emotion
        }));
    }
  }, [soulState]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;

    const userMessage = {
      id: Date.now().toString(),
      role: 'user' as const,
      content: input.trim(),
      timestamp: Date.now(),
    };

    addMessage(userMessage);
    setInput('');
    setIsTyping(true);

    try {
      // Capture current session ID to prevent race conditions
      // Use "default" if currentSessionId is null/empty, to trigger initial session creation logic on backend
      const sendingSessionId = currentSessionId || "default";
      
      // We no longer generate systemPrompt on frontend to avoid state drift.
      // The backend SoulManager maintains the true state and generates the dynamic prompt.
      const response = await api.sendMessage(userMessage.content, sendingSessionId);
      
      // If session changed while waiting for response, do not update UI with new message
      // (The message is already saved in backend history for the original session)
      if (useAppStore.getState().currentSessionId !== currentSessionId) {
        console.log('Session changed, skipping UI update for previous session response');
        setIsTyping(false);
        return;
      }
      
      if (response?.success) {
        // Update session ID if it was a new session (e.g. sent with "default")
        // The backend returns the actual persistent session_id
        if (sendingSessionId === 'default' && response.session_id && response.session_id !== 'default') {
             console.log(`Switching from default to new session: ${response.session_id}`);
             // We need to update the store's current session ID to the real one
             // This prevents the NEXT message from sending "default" again and creating another duplicate
             useAppStore.getState().selectSession(response.session_id);
        }

        // Auto-rename logic: Check if current session title is generic and rename it
        const targetSessionId = response.session_id || sendingSessionId;
        const currentSession = sessions.find(s => s.id === targetSessionId);
        
        // We use the store's latest sessions to check title, as it might have been loaded
        const latestSessions = useAppStore.getState().sessions;
        const latestSession = latestSessions.find(s => s.id === targetSessionId);
        
        if (latestSession && (!latestSession.title || latestSession.title === 'New Chat' || latestSession.title === '新对话')) {
             if (userMessage.content.trim().length > 0) {
                 const newTitle = userMessage.content.trim().substring(0, 30);
                 // Call updateSession (which updates backend and reloads sessions)
                 useAppStore.getState().updateSession(targetSessionId, newTitle);
             }
        }

        // Reload soul state from backend (which has been updated by the chat request)
        await loadSoulState();
        
        // Note: loadSoulState already updates store.currentEmotion and our useEffect updates personaState

        // Update UI with response
        // We use the store's currentEmotion which was updated by loadSoulState
        const updatedEmotion = useAppStore.getState().currentEmotion;
        
        addMessage({
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.response,
          timestamp: Date.now(),
          emotion: updatedEmotion,
          });
      } else {
        setCurrentEmotion('sad');
        addMessage({
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: '呜呜... 出错了，请稍后再试～',
          timestamp: Date.now(),
          emotion: 'sad',
        });
      }
    } catch (error) {
      console.error('Chat error:', error);
      setCurrentEmotion('sad');
      addMessage({
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '连接好像不太稳定... 等等我再试一次好不好？🥺',
        timestamp: Date.now(),
        emotion: 'sad',
      });
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 如果没有选中会话，显示空状态
  const themeMode = settings?.themeMode || 'light';
  const sakura = [
    { left: '6%', top: '18%', size: 16, opacity: 0.25, delay: 0 },
    { left: '18%', top: '64%', size: 12, opacity: 0.18, delay: 0.8 },
    { left: '36%', top: '30%', size: 20, opacity: 0.22, delay: 1.2 },
    { left: '52%', top: '52%', size: 14, opacity: 0.2, delay: 0.4 },
    { left: '70%', top: '22%', size: 18, opacity: 0.24, delay: 1.6 },
    { left: '82%', top: '70%', size: 12, opacity: 0.18, delay: 0.6 },
    { left: '90%', top: '38%', size: 16, opacity: 0.2, delay: 1.1 },
  ];

  if (!currentSessionId) {
    return (
      <div className="chat-shell flex flex-col h-full items-center justify-center space-y-4">
        <div className="chat-empty-icon w-24 h-24 rounded-full flex items-center justify-center text-5xl shadow-sm animate-pulse">
          💕
        </div>
        <p className="chat-empty-text text-lg font-medium">快去创建一个新会话与光聊聊吧！</p>
      </div>
    );
  }

  return (
    <div className={`chat-shell theme-${themeMode} flex flex-col h-full`}>
      {themeMode === 'love' && (
        <div className="chat-sakura">
          {sakura.map((s, i) => (
            <span
              key={i}
              className="sakura-petal"
              style={{
                left: s.left,
                top: s.top,
                width: `${s.size}px`,
                height: `${s.size}px`,
                opacity: s.opacity,
                animationDelay: `${s.delay}s`,
              }}
            />
          ))}
        </div>
      )}
      {/* 消息列表 */}
      <div className="chat-list flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 space-y-4">
            <div className="chat-empty-icon w-20 h-20 rounded-full flex items-center justify-center text-4xl animate-pulse">
              💕
            </div>
            <p className="text-lg">开始和 Hikari 对话吧～</p>
          </div>
        )}
        
        <AnimatePresence>
          {messages.map((message, index) => (
            <MessageItem key={message.id} message={message} index={index} />
          ))}
        </AnimatePresence>
        
        {isTyping && <TypingIndicator />}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 - 微信风格 */}
      <div className="chat-input-bar border-t p-3">
        <div className="flex items-end space-x-2">
          <button
            onClick={clearMessages}
            className="p-2 text-gray-500 hover:text-red-500 hover:bg-gray-200 rounded-full transition-all"
            title="清除对话"
          >
            <Trash2 size={20} />
          </button>
          
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder=""
              className="chat-input w-full rounded-md px-3 py-2 text-sm resize-none focus:outline-none transition-all"
              rows={1}
              style={{ minHeight: '36px', maxHeight: '100px' }}
            />
          </div>
          
          <motion.button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className={`p-2 rounded-md shadow-sm transition-all ${
              !input.trim() || isTyping 
                ? 'bg-gray-200 text-gray-400 cursor-not-allowed' 
                : 'bg-[#07c160] text-white hover:bg-[#06ad56]'
            }`}
          >
            <Send size={20} />
          </motion.button>
        </div>
      </div>
    </div>
  );
}

import CodeBlock from './CodeBlock';

function MessageItem({ message, index }: { message: import('../../stores/appStore').Message; index: number }) {
  const isUser = message.role === 'user';
  const emotion = message.emotion || 'normal';
  const { emoji, color } = emotionConfig[emotion];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25, delay: index * 0.05 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
    >
      <div className={`flex max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start space-x-2`}>
        {/* 头像 */}
        {!isUser ? (
          <div 
            className="chat-avatar w-9 h-9 rounded-md flex items-center justify-center text-xl flex-shrink-0 mr-2"
          >
            {emoji}
          </div>
        ) : (
          <div className="chat-avatar-me w-9 h-9 rounded-md flex items-center justify-center ml-2">
            <span className="text-xs">Me</span>
          </div>
        )}

        {/* 气泡 */}
        <div className="flex flex-col min-w-0">
          <div className={`chat-bubble relative px-3 py-2 rounded-md text-sm leading-relaxed shadow-sm break-words ${isUser ? 'chat-bubble-user' : 'chat-bubble-assistant'}`}>
            {/* 气泡小三角 */}
            <div className={`chat-bubble-tail absolute top-3 w-0 h-0 border-solid border-4 ${isUser ? 'chat-bubble-tail-user' : 'chat-bubble-tail-assistant'}`} />
            
            <div className="prose prose-sm max-w-none prose-p:my-0 prose-pre:my-0 prose-pre:bg-transparent prose-pre:p-0">
              <ReactMarkdown
                components={{
                  code({ node, inline, className, children, ...props }: any) {
                    const match = /language-(\w+)/.exec(className || '');
                    const language = match ? match[1] : '';
                    
                    if (!inline && match) {
                      return (
                        <CodeBlock 
                          language={language} 
                          value={String(children).replace(/\n$/, '')} 
                        />
                      );
                    }
                    return (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  }
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          </div>
          
          {/* 时间戳 */}
          <span className={`text-[10px] text-gray-400 mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      </div>
    </motion.div>
  );
}

function TypingIndicator() {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex justify-start mb-4"
    >
      <div className="flex items-center space-x-2">
        <div className="w-9 h-9 rounded-md bg-white border border-gray-200 flex items-center justify-center mr-2">
          ...
        </div>
        <div className="bg-white px-4 py-3 rounded-md border border-gray-100 shadow-sm flex space-x-1">
          <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0s' }} />
          <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
          <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
        </div>
      </div>
    </motion.div>
  );
}
