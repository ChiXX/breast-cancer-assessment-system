import { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Layout } from '../components/Layout';
import { assessmentService } from '../services/api';
import { AlertTriangle, CheckCircle, Info, ArrowLeft, ShieldAlert } from 'lucide-react';
import type { RiskLevel } from '../types';
import { logEvent } from '../utils/eventLogger';
import { EventName } from '../types';
import { getOrCreateSessionId } from '../utils/session';

const riskConfig = {
  High: {
    color: 'bg-red-500',
    bg: 'bg-red-50',
    text: 'text-red-700',
    border: 'border-red-100',
    icon: ShieldAlert,
    label: '高风险',
    gradient: 'from-red-500 to-rose-600'
  },
  Medium: {
    color: 'bg-amber-500',
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-100',
    icon: AlertTriangle,
    label: '中风险',
    gradient: 'from-amber-500 to-orange-600'
  },
  Low: {
    color: 'bg-emerald-500',
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-100',
    icon: CheckCircle,
    label: '低风险',
    gradient: 'from-emerald-500 to-teal-600'
  }
};

export default function ResultPage() {
  const { id } = useParams<{ id: string }>();
  const sessionId = getOrCreateSessionId();
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['assessment', id],
    queryFn: () => assessmentService.getById(Number(id)),
    enabled: !!id,
  });

  useEffect(() => {
    if (data) {
      logEvent(EventName.RESULT_VIEWED, sessionId, data.id);
    }
  }, [data, sessionId]);

  const handleContactTeam = () => {
    if (data) {
      logEvent(EventName.CONTACT_TEAM_CLICKED, sessionId, data.id);
      alert('已收到您的协同请求，团队将尽快与您联系。');
    }
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="max-w-2xl mx-auto pt-20 text-center">
          <div className="animate-pulse flex flex-col items-center">
            <div className="w-16 h-16 bg-gray-200 rounded-full mb-4"></div>
            <div className="h-6 w-48 bg-gray-200 rounded mb-2"></div>
            <div className="h-4 w-64 bg-gray-200 rounded"></div>
          </div>
        </div>
      </Layout>
    );
  }

  if (error || !data) {
    return (
      <Layout>
        <div className="max-w-2xl mx-auto pt-20 text-center">
          <p className="text-red-500">无法加载评估结果，请稍后再试。</p>
          <Link to="/" className="mt-4 inline-block text-primary">返回首页</Link>
        </div>
      </Layout>
    );
  }

  const config = riskConfig[data.risk_level as RiskLevel] || riskConfig.Low;
  const Icon = config.icon;

  return (
    <Layout>
      <div className="max-w-2xl mx-auto pt-8 px-4 animate-fade-in">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-primary mb-6 transition-colors">
          <ArrowLeft size={16} />
          返回重新评估
        </Link>

        {/* Risk Banner */}
        <div className={`rounded-3xl overflow-hidden shadow-2xl mb-8 border ${config.border}`}>
          <div className={`h-3 bg-gradient-to-r ${config.gradient}`}></div>
          <div className={`p-8 ${config.bg}`}>
            <div className="flex items-center gap-4 mb-4">
              <div className={`p-3 rounded-2xl bg-white shadow-sm ${config.text}`}>
                <Icon size={32} />
              </div>
              <div>
                <span className={`text-sm font-bold uppercase tracking-wider ${config.text}`}>风险分级</span>
                <h2 className={`text-3xl font-black ${config.text}`}>{config.label}</h2>
              </div>
            </div>
            <p className="text-gray-700 leading-relaxed font-medium">
              您的输入："{data.user_input}"
            </p>
          </div>
        </div>

        {/* Advice Card */}
        <div className="bg-white rounded-3xl shadow-xl p-8 mb-8 border border-gray-100 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 text-gray-50 opacity-10">
            <Info size={120} />
          </div>
          <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            下一步建议
          </h3>
          <div className="text-lg text-gray-700 leading-relaxed space-y-4">
            {data.advice.split('\n').map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>
          
          {data.contact_team && (
            <button 
              onClick={handleContactTeam}
              className="mt-8 w-full bg-primary text-white font-bold py-4 rounded-2xl shadow-lg hover:shadow-2xl hover:-translate-y-1 transition-all"
            >
              立即联系医疗团队
            </button>
          )}
        </div>

        {/* Evidence Accordion */}
        <div className="bg-gray-50 rounded-2xl p-6 border border-gray-100">
          <h4 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-4">评估依据</h4>
          <div className="text-gray-600 text-sm leading-relaxed italic">
            {data.evidence}
          </div>
          <div className="mt-4 pt-4 border-t border-gray-200 flex justify-between text-[10px] text-gray-400 font-mono">
            <span>命中规则: {data.matched_rule_id}</span>
            <span>系统版本: {data.version}</span>
          </div>
        </div>
      </div>
    </Layout>
  );
}
