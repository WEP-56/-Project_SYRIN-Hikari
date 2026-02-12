import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, Settings, X, Minus, Menu, Heart } from 'lucide-react';
import { useAppStore, emotionConfig } from '../../stores/appStore';
import ChatView from './ChatView';
import SettingsView from './SettingsView';
import Sidebar from './Sidebar';
import SoulSidebar from './SoulSidebar';
import ErrorBoundary from '../ErrorBoundary';

export default function NormalMode() {
  const [activeTab, setActiveTab] = useState<'chat' | 'settings'>('chat');
  const { 
    currentEmotion, 
    connectionStatus,
    messages,
    sidebarOpen,
    toggleSidebar,
    soulSidebarOpen,
    toggleSoulSidebar
  } = useAppStore();
  
  const { emoji, color, label } = emotionConfig[currentEmotion] || emotionConfig['normal'];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="w-full h-full flex flex-col overflow-hidden rounded-xl bg-[#f5f5f5]"
    >
      {/* 标题栏 */}
      <header 
        className="h-12 flex items-center justify-between px-4 relative z-50 border-b border-gray-100 bg-[#f5f5f5]"
        style={{ 
          // @ts-ignore
          WebkitAppRegion: 'drag' 
        }}
      >
        <div className="flex items-center space-x-3">
          {/* 侧边栏开关 */}
          <button 
            onClick={toggleSidebar}
            className={`p-1.5 rounded-md transition-colors no-drag ${
              sidebarOpen ? 'bg-gray-200 text-gray-800' : 'text-gray-500 hover:bg-gray-200'
            }`}
            style={{ WebkitAppRegion: 'no-drag' } as any}
          >
            <Menu size={18} />
          </button>

          {/* 情绪表情 - 稍微缩小并移除强烈发光 */}
          <motion.div 
            className="w-8 h-8 rounded-full flex items-center justify-center text-lg bg-white shadow-sm border border-gray-200"
            animate={{ 
              scale: [1, 1.1, 1],
              rotate: [0, -5, 5, 0]
            }}
            transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
          >
            {emoji}
          </motion.div>
          
          <div className="flex flex-col">
            <h1 className="text-sm font-bold text-gray-800 leading-tight">
              Hikari
            </h1>
            <div className="flex items-center space-x-1.5 text-[10px] text-gray-500 leading-tight">
              <span 
                className="px-1.5 rounded-full bg-gray-200 text-gray-600"
              >
                {label}
              </span>
              <span className="flex items-center space-x-1">
                <div 
                  className={`w-1.5 h-1.5 rounded-full ${
                    connectionStatus === 'connected' ? 'bg-green-500' : 
                    connectionStatus === 'error' ? 'bg-red-500' : 'bg-yellow-500 animate-pulse'
                  }`} 
                />
                <span>
                  {connectionStatus === 'connected' ? '在线' : 
                   connectionStatus === 'error' ? '离线' : '连接中'}
                </span>
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-1 no-drag" style={{ WebkitAppRegion: 'no-drag' } as any}>
          {/* 标签切换 - 微信风格 */}
          <nav className="flex space-x-1 p-0.5 rounded-lg mr-4">
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200 ${
                activeTab === 'chat'
                  ? 'text-green-600 bg-gray-200/50'
                  : 'text-gray-500 hover:text-gray-800 hover:bg-gray-200/30'
              }`}
            >
              <MessageSquare size={16} />
              {messages.length > 0 && (
                <span className="bg-red-500 text-white text-[10px] px-1 rounded-full min-w-[16px] text-center ml-1">
                  {messages.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('settings')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200 ${
                activeTab === 'settings'
                  ? 'text-green-600 bg-gray-200/50'
                  : 'text-gray-500 hover:text-gray-800 hover:bg-gray-200/30'
              }`}
            >
              <Settings size={16} />
            </button>
          </nav>
          
          {/* 窗口控制 */}
          <div className="flex items-center space-x-1">
            <button
              onClick={toggleSoulSidebar}
              className={`p-1.5 rounded-md transition-colors no-drag mr-2 ${
                soulSidebarOpen ? 'bg-pink-100 text-pink-600' : 'text-gray-500 hover:bg-pink-50 hover:text-pink-500'
              }`}
              title="情感状态"
            >
              <Heart size={16} />
            </button>

            <button
              onClick={() => window.electronAPI?.minimizeWindow()}
              className="p-1.5 text-gray-500 hover:text-gray-800 hover:bg-gray-200/50 rounded-md transition-colors"
              title="最小化"
            >
              <Minus size={16} />
            </button>
            <button
              onClick={() => window.electronAPI?.closeWindow()}
              className="p-1.5 text-gray-500 hover:text-white hover:bg-red-500 rounded-md transition-colors"
              title="关闭"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="flex-1 overflow-hidden relative">
        <ErrorBoundary>
          <Sidebar />
        </ErrorBoundary>
        
        <ErrorBoundary>
          <SoulSidebar />
        </ErrorBoundary>

        <AnimatePresence mode="wait">
          {activeTab === 'chat' ? (
            <motion.div
              key="chat"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              <ChatView />
            </motion.div>
          ) : (
            <motion.div
              key="settings"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              <SettingsView />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </motion.div>
  );
}
