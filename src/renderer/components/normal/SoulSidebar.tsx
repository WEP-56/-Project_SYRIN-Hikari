import React from 'react';
import { useAppStore } from '../../stores/appStore';
import SoulMetrics from './SoulMetrics';

export default function SoulSidebar() {
  const { 
    soulSidebarOpen, 
    toggleSoulSidebar 
  } = useAppStore();

  if (!soulSidebarOpen) return null;

  return (
    <>
      {/* Overlay */}
      <div 
        className="absolute inset-0 bg-black/20 z-30 transition-opacity"
        onClick={toggleSoulSidebar}
      />
      
      {/* Sidebar Panel */}
      <div
        className="absolute right-0 top-0 bottom-0 w-64 bg-white shadow-lg z-40 border-l border-gray-100 flex flex-col"
        onClick={(e) => e.stopPropagation()} 
      >
        <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-gray-50">
          <h2 className="text-sm font-bold text-gray-700">情感状态</h2>
        </div>
        
        <div className="flex-1 overflow-y-auto p-2 space-y-2">
          <SoulMetrics />
        </div>
      </div>
    </>
  );
}
