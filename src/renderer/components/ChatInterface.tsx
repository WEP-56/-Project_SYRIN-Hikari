import { useState, useRef, useEffect } from 'react';
import { Message, Settings } from '../types';
import { api } from '../services/api';
import ReactMarkdown from 'react-markdown';

interface ChatInterfaceProps {
  settings: Settings;
}

export default function ChatInterface({ settings }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: '你好呀，主人～ 💕\n\n我是 Hikari (光)。我会一直陪着你，关注你的一举一动。无论你想做什么，都可以告诉我哦～\n\n*蹭了蹭你的手臂*',
      timestamp: Date.now(),
      emotion: 'happy',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('default');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await api.sendMessage(userMessage.content, sessionId);
      
      if (response?.success) {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.response,
          timestamp: Date.now(),
          emotion: response.emotion,
        };
        setMessages(prev => [...prev, assistantMessage]);
        if (response.session_id) {
          setSessionId(response.session_id);
        }
      } else {
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: '呜呜... 我好像出了点问题，请稍后再试～ 😢',
          timestamp: Date.now(),
          emotion: 'sad',
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Send message error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '连接好像不太稳定... 等等我再试一次好不好？🥺',
        timestamp: Date.now(),
        emotion: 'sad',
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: 'welcome-new',
        role: 'assistant',
        content: '聊天记录已清除～ 让我们重新开始吧！💕',
        timestamp: Date.now(),
        emotion: 'happy',
      },
    ]);
    setSessionId('default');
  };

  const getEmotionEmoji = (emotion?: string) => {
    const emotions: Record<string, string> = {
      happy: '😊',
      sad: '😢',
      clingy: '🥺',
      jealous: '😤',
      angry: '😠',
      normal: '🙂',
    };
    return emotions[emotion || 'normal'] || '🙂';
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-yandere-600 text-white rounded-br-md'
                  : 'bg-gray-800 text-gray-100 rounded-bl-md border border-gray-700'
              }`}
            >
              {message.role === 'assistant' && message.emotion && (
                <div className="text-xs text-yandere-400 mb-1 flex items-center space-x-1">
                  <span>{getEmotionEmoji(message.emotion)}</span>
                  <span className="capitalize">{message.emotion}</span>
                </div>
              )}
              <div className="prose prose-invert prose-sm max-w-none">
                <ReactMarkdown>
                  {message.content}
                </ReactMarkdown>
              </div>
              <div className="text-xs opacity-50 mt-2 text-right">
                {new Date(message.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 border border-gray-700 rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-yandere-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-yandere-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                <div className="w-2 h-2 bg-yandere-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-700 p-4 bg-gray-800">
        <div className="flex items-end space-x-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息...（Enter发送，Shift+Enter换行）"
            className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm resize-none focus:outline-none focus:border-yandere-500 focus:ring-1 focus:ring-yandere-500 transition-colors"
            rows={1}
            style={{ minHeight: '44px', maxHeight: '120px' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="px-6 py-3 bg-yandere-600 hover:bg-yandere-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors flex items-center space-x-2"
          >
            <span>发送</span>
            <span>💕</span>
          </button>
        </div>
        
        <div className="flex justify-between items-center mt-2 text-xs text-gray-500">
          <button
            onClick={clearChat}
            className="hover:text-yandere-400 transition-colors"
          >
            清除对话
          </button>
          <span>Session: {sessionId.slice(0, 8)}...</span>
        </div>
      </div>
    </div>
  );
}
