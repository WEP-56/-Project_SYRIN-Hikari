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
    sidebarOpen
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

  // 人格状态管理
  const [personaState, setPersonaState] = useState(defaultPersonaState);

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
      // 生成病娇人设 Prompt
      const recentMessages = messages.slice(-5).map(m => `${m.role}: ${m.content}`);
      const systemPrompt = generatePersonaPrompt(personaState, recentMessages);
      
      console.log('Generated persona prompt:', systemPrompt.substring(0, 200) + '...');
      
      // Capture current session ID to prevent race conditions
      // Use "default" if currentSessionId is null/empty, to trigger initial session creation logic on backend
      const sendingSessionId = currentSessionId || "default";
      
      const response = await api.sendMessage(userMessage.content, sendingSessionId, systemPrompt);
      
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
        // 更新情绪和好感度
        const newEmotion = settings.emotionEnabled 
          ? updateEmotionFromInteraction(personaState, userMessage.content, response.response)
          : 'normal';
        const newAffection = updateAffection(personaState.affection, userMessage.content);
        
        setPersonaState(prev => ({
          ...prev,
          emotion: newEmotion,
          affection: newAffection,
          lastInteraction: Date.now(),
        }));
        
        setCurrentEmotion(newEmotion);
        
        addMessage({
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.response,
          timestamp: Date.now(),
          emotion: newEmotion,
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

  return (
    <div className="flex flex-col h-full bg-[#f5f5f5]">
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 space-y-4">
            <div className="w-20 h-20 rounded-full bg-gray-200 flex items-center justify-center text-4xl animate-pulse">
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
      <div className="border-t border-[#e5e5e5] p-3 bg-[#f5f5f5]">
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
              className="w-full bg-white border border-[#e5e5e5] rounded-md px-3 py-2 text-sm resize-none focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500/50 transition-all text-gray-800"
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
            className="w-9 h-9 rounded-md flex items-center justify-center text-xl flex-shrink-0 bg-white border border-gray-200 mr-2"
          >
            {emoji}
          </div>
        ) : (
          <div className="w-9 h-9 rounded-md bg-gray-200 flex items-center justify-center ml-2">
            <span className="text-gray-500 text-xs">Me</span>
          </div>
        )}

        {/* 气泡 */}
        <div className="flex flex-col min-w-0">
          <div
            className={`relative px-3 py-2 rounded-md text-sm leading-relaxed shadow-sm break-words ${
              isUser 
                ? 'bg-[#95ec69] text-black' 
                : 'bg-white text-gray-800 border border-gray-100'
            }`}
          >
            {/* 气泡小三角 */}
            <div 
              className={`absolute top-3 w-0 h-0 border-solid border-4 ${
                isUser
                  ? 'right-[-8px] border-transparent border-l-[#95ec69]'
                  : 'left-[-8px] border-transparent border-r-white'
              }`}
            />
            
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
