import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Trash2, X, Edit2, Check } from 'lucide-react';
import { useAppStore } from '../../stores/appStore';

export default function Sidebar() {
  const { 
    sessions, 
    currentSessionId, 
    sidebarOpen, 
    toggleSidebar,
    loadSessions, 
    createSession, 
    selectSession, 
    deleteSession,
    updateSession
  } = useAppStore();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  useEffect(() => {
    if (sidebarOpen) {
      loadSessions();
    }
  }, [sidebarOpen]);

  const handleStartEdit = (e: React.MouseEvent, session: any) => {
    e.stopPropagation();
    setEditingId(session.id);
    setEditTitle(session.title || '新对话');
  };

  const handleSaveEdit = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (editingId && editTitle.trim()) {
      await updateSession(editingId, editTitle.trim());
      setEditingId(null);
    }
  };

  const handleCancelEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  };

  return (
    <AnimatePresence>
      {sidebarOpen && (
        <>
          {/* Overlay to close sidebar when clicking outside (optional, but good for mobile/small screens) */}
          <motion.div 
            key="sidebar-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.2 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black z-30"
            onClick={(e) => {
              e.stopPropagation();
              toggleSidebar();
            }}
          />
          
          <motion.div
            key="sidebar-panel"
            initial={{ x: -250, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -250, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="absolute left-0 top-0 bottom-0 w-64 bg-white shadow-lg z-40 border-r border-gray-100 flex flex-col"
            onClick={(e) => e.stopPropagation()} 
          >
            <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-gray-50">
            <h2 className="text-sm font-bold text-gray-700">历史会话</h2>
            <button 
              onClick={createSession}
              className="p-1.5 rounded-md hover:bg-white hover:shadow-sm text-green-600 transition-all"
              title="新对话"
            >
              <Plus size={16} />
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {sessions.map((session) => (
              <div 
                key={session.id}
                onClick={() => selectSession(session.id)}
                className={`group p-3 rounded-lg cursor-pointer transition-all ${
                  currentSessionId === session.id 
                    ? 'bg-green-50 border border-green-100 shadow-sm' 
                    : 'hover:bg-gray-50 border border-transparent'
                }`}
              >
                <div className="flex justify-between items-start mb-1">
                  {editingId === session.id ? (
                    <div className="flex-1 flex items-center space-x-1" onClick={e => e.stopPropagation()}>
                        <input 
                            autoFocus
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') handleSaveEdit(e as any);
                                if (e.key === 'Escape') handleCancelEdit(e as any);
                            }}
                            className="flex-1 text-xs px-1 py-0.5 border border-green-300 rounded focus:outline-none"
                        />
                        <button onClick={handleSaveEdit} className="text-green-600 hover:text-green-700"><Check size={12} /></button>
                        <button onClick={handleCancelEdit} className="text-gray-400 hover:text-gray-600"><X size={12} /></button>
                    </div>
                  ) : (
                    <>
                      <span className={`text-xs font-medium line-clamp-1 ${
                        currentSessionId === session.id ? 'text-green-700' : 'text-gray-700'
                      }`}>
                        {session.title || '新对话'}
                      </span>
                      <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                            onClick={(e) => handleStartEdit(e, session)}
                            className="text-gray-400 hover:text-blue-500 p-1"
                            title="重命名"
                        >
                            <Edit2 size={12} />
                        </button>
                        <button
                            onClick={(e) => {
                            e.stopPropagation();
                            if (confirm('确定要删除这个会话吗？')) {
                                deleteSession(session.id);
                            }
                            }}
                            className="text-gray-400 hover:text-red-500 p-1"
                            title="删除"
                        >
                            <Trash2 size={12} />
                        </button>
                      </div>
                    </>
                  )}
                </div>
                <p className="text-[10px] text-gray-500 line-clamp-2 mb-1">
                  {session.preview || '暂无内容'}
                </p>
                <div className="flex justify-between items-center">
                  <div className="text-[10px] text-gray-400">
                    {new Date(session.updated_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))}
            
            {(!sessions || sessions.length === 0) && (
              <div className="text-center text-gray-400 text-xs py-8">
                暂无历史会话
                <button 
                  onClick={createSession}
                  className="block mx-auto mt-2 text-green-600 hover:underline"
                >
                  开始新对话
                </button>
              </div>
            )}
          </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
