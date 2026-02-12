import { useEffect } from 'react';
import { Heart, Shield, Lock, Activity, Users } from 'lucide-react';
import { useAppStore } from '../../stores/appStore';

export default function SoulMetrics() {
  const { soulState, loadSoulState } = useAppStore();

  useEffect(() => {
    loadSoulState();
    const interval = setInterval(() => {
      loadSoulState();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  // Debug logging
  console.log('[SoulMetrics] Render soulState:', soulState);

  if (!soulState) {
    console.log('[SoulMetrics] No soulState');
    return null;
  }

  const metrics = soulState.metrics || {};
  const current_phase = soulState.current_phase || 1;
  const emotion = soulState.emotion || {};
  
  // Phase Labels
  const PHASE_LABELS: Record<number, string> = {
    1: "陌生人 (Stranger)",
    2: "伙伴 (Partner)",
    3: "病娇 (Yandere)"
  };

  const PHASE_COLORS: Record<number, string> = {
    1: "text-gray-500",
    2: "text-pink-500",
    3: "text-purple-600 font-bold"
  };

  return (
    <div className="space-y-4">
      {/* 头部摘要 */}
      <div className="bg-white rounded-lg p-3 border border-gray-100 shadow-sm">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <Heart size={18} className={(metrics?.affection ?? 0) > 60 ? "text-pink-500 fill-pink-500" : "text-gray-400"} />
            <span className="text-sm font-bold text-gray-700">
              好感度: {(metrics?.affection ?? 0).toFixed(0)}%
            </span>
          </div>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full bg-gray-50 border border-gray-100 ${PHASE_COLORS[current_phase] || "text-gray-500"}`}>
            {PHASE_LABELS[current_phase] || "Unknown"}
          </span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-pink-300 to-pink-500 transition-all duration-1000 ease-out"
            style={{ width: `${metrics?.affection ?? 0}%` }}
          />
        </div>
      </div>

      {/* 详细指标 */}
      <div className="bg-white rounded-lg p-4 border border-gray-100 shadow-sm space-y-4">
        <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">
          灵魂维度 (Dimensions)
        </h3>
        
        <MetricItem 
          icon={<Shield size={14} />} 
          label="信任度 (Trust)" 
          value={metrics?.trust} 
          color="text-blue-500" 
          barColor="bg-blue-500"
        />
        
        <MetricItem 
          icon={<Lock size={14} />} 
          label="占有欲 (Possessiveness)" 
          value={metrics?.possessiveness} 
          color="text-purple-600" 
          barColor="bg-purple-600"
        />
        
        <MetricItem 
          icon={<Activity size={14} />} 
          label="依赖度 (Dependency)" 
          value={metrics?.dependency} 
          color="text-orange-500" 
          barColor="bg-orange-500"
        />
        
        <MetricItem 
          icon={<Users size={14} />} 
          label="亲密程度 (Intimacy)" 
          value={metrics?.intimacy} 
          color="text-red-500" 
          barColor="bg-red-500"
        />
      </div>

      {/* 情绪状态 */}
      <div className="bg-white rounded-lg p-3 border border-gray-100 shadow-sm flex items-center justify-between">
        <span className="text-xs text-gray-500">当前情绪状态</span>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${emotion?.intensity > 0.7 ? 'bg-red-500 animate-pulse' : 'bg-green-500'}`} />
          <span className="text-xs font-medium text-gray-700">
            {emotion?.primary || "平静"} 
            {emotion?.intensity > 0.7 && " (强烈)"}
          </span>
        </div>
      </div>
    </div>
  );
}

function MetricItem({ icon, label, value, color, barColor }: any) {
  const safeValue = typeof value === 'number' ? value : 0;
  
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs text-gray-600">
        <div className="flex items-center space-x-1.5">
          <span className={color}>{icon}</span>
          <span>{label}</span>
        </div>
        <span className="font-mono text-gray-400">{safeValue.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div 
          className={`h-full ${barColor} opacity-80 transition-all duration-500 ease-out`}
          style={{ width: `${safeValue}%` }}
        />
      </div>
    </div>
  );
}
