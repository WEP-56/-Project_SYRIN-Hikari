import { ConnectionStatus } from '../types';

interface StatusBarProps {
  status: ConnectionStatus;
}

export default function StatusBar({ status }: StatusBarProps) {
  const getStatusInfo = () => {
    switch (status) {
      case 'connected':
        return {
          color: 'bg-green-500',
          text: '已连接',
          icon: '✓',
        };
      case 'connecting':
        return {
          color: 'bg-yellow-500',
          text: '连接中...',
          icon: '⟳',
        };
      case 'error':
        return {
          color: 'bg-red-500',
          text: '连接失败',
          icon: '✗',
        };
      default:
        return {
          color: 'bg-gray-500',
          text: '未知',
          icon: '?',
        };
    }
  };

  const { color, text, icon } = getStatusInfo();

  return (
    <div className="h-8 bg-gray-800 border-t border-gray-700 flex items-center justify-between px-4 text-xs">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${color} ${status === 'connecting' ? 'animate-pulse' : ''}`} />
          <span className="text-gray-400">{icon} {text}</span>
        </div>
        
        <div className="text-gray-500">
          v1.0.0
        </div>
      </div>

      <div className="flex items-center space-x-4 text-gray-500">
        <span>API: http://127.0.0.1:8888</span>
        <span>Project SYRIN © 2026</span>
      </div>
    </div>
  );
}
