import { useEffect } from 'react';
import NormalMode from './components/normal/NormalMode';
import { useAppStore } from './stores/appStore';
import { api } from './services/api';
import './styles.css';

function App() {
  const { setConnectionStatus, updateSettings, addMessage } = useAppStore();

  useEffect(() => {
    // 检查后端连接
    const checkConnection = async () => {
      try {
        const status = await api.getStatus();
        if (status) {
          setConnectionStatus('connected');
          // 仅在首次连接或重连时加载配置
          // 这里简化为每次连接都尝试加载，但频率降低
          const config = await api.getConfig();
          if (config) {
            updateSettings({
              provider: config.provider || 'openai',
              model: config.model || 'gpt-4o-mini',
            });
          }
        } else {
          setConnectionStatus('error');
        }
      } catch {
        setConnectionStatus('error');
      }
    };

    checkConnection();
    // 延长轮询间隔至5分钟，减少日志噪音和窗口波动
    const interval = setInterval(checkConnection, 300000);

    return () => clearInterval(interval);
  }, []);

  // Poll for notifications (Proactive Mode)
  useEffect(() => {
    // Request permission if not granted
    if (Notification.permission === 'default') {
      Notification.requestPermission();
    }

    const pollNotifications = async () => {
      try {
        const result = await api.getNotifications();
        if (result && result.notifications && result.notifications.length > 0) {
          result.notifications.forEach((n: any) => {
             new Notification('Hikari', {
               body: n.content,
               silent: true // Non-intrusive as requested
             });
          });
        }
      } catch (e) {
        // Silent fail
      }
    };

    // Poll every 10 seconds
    const interval = setInterval(pollNotifications, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-screen h-screen overflow-hidden bg-transparent">
      <NormalMode />
    </div>
  );
}

export default App;
