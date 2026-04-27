import { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Layout } from '../components/Layout';
import { assessmentService } from '../services/api';
import { AlertTriangle, CheckCircle, Info, ArrowLeft, ShieldAlert, MessageSquare, Brain, Clock } from 'lucide-react';
import { logEvent } from '../utils/eventLogger';
import { EventName } from '../types';
import { getOrCreateSessionId } from '../utils/session';

const riskConfig: Record<string, any> = {
  'Grade 1': {
    color: 'bg-rose-500',
    bg: 'bg-rose-50',
    text: 'text-rose-700',
    border: 'border-rose-200',
    icon: ShieldAlert,
    label: '高风险 (Grade 1)',
    buttonLabel: '紧急拨打 120',
    gradient: 'from-rose-500 to-red-600',
    action: '立即线下就医'
  },
  'Grade 2': {
    color: 'bg-orange-500',
    bg: 'bg-orange-50',
    text: 'text-orange-700',
    border: 'border-orange-200',
    icon: AlertTriangle,
    label: '高风险 (Grade 2)',
    buttonLabel: '预约医生',
    gradient: 'from-orange-500 to-amber-600',
    action: '24小时内联系团队'
  },
  'Grade 3': {
    color: 'bg-amber-500',
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-200',
    icon: MessageSquare,
    label: '中风险 (Grade 3)',
    buttonLabel: '在线咨询',
    gradient: 'from-amber-500 to-orange-600',
    action: '联系团队'
  },
  'Grade 4': {
    color: 'bg-sky-500',
    bg: 'bg-sky-50',
    text: 'text-sky-700',
    border: 'border-sky-200',
    icon: Info,
    label: '中风险 (Grade 4)',
    buttonLabel: '添加观察日志',
    gradient: 'from-sky-500 to-blue-600',
    action: '密切观察'
  },
  'Grade 5': {
    color: 'bg-emerald-500',
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
    icon: CheckCircle,
    label: '低风险 (Grade 5)',
    buttonLabel: '完成记录',
    gradient: 'from-emerald-500 to-teal-600',
    action: '继续观察与记录'
  },
  '未知': {
    color: 'bg-gray-500',
    bg: 'bg-gray-50',
    text: 'text-gray-700',
    border: 'border-gray-100',
    icon: Info,
    label: '医学问询',
    buttonLabel: '联系团队',
    gradient: 'from-gray-400 to-gray-600',
    action: '正在分析'
  }
};

// Aliases for robustness
riskConfig.HIGH = riskConfig['Grade 1'];
riskConfig.MEDIUM = riskConfig['Grade 3'];
riskConfig.LOW = riskConfig['Grade 5'];
riskConfig.Urgent = riskConfig.HIGH;
riskConfig.High = riskConfig.HIGH;
riskConfig.Medium = riskConfig.MEDIUM;
riskConfig.Low = riskConfig.LOW;
riskConfig.urgent = riskConfig.HIGH;
riskConfig.high = riskConfig.HIGH;
riskConfig.medium = riskConfig.MEDIUM;
riskConfig.low = riskConfig.LOW;

export default function ResultPage() {
  const { id } = useParams<{ id: string }>();
  const sessionId = getOrCreateSessionId();
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['assessment', id],
    queryFn: () => assessmentService.getById(Number(id)),
    enabled: !!id,
  });

  const { data: history, isLoading: isHistoryLoading } = useQuery({
    queryKey: ['assessment-history', id],
    queryFn: () => assessmentService.getHistory(Number(id)),
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
          <Link to="/history" className="mt-4 inline-block text-primary">返回历史记录</Link>
        </div>
      </Layout>
    );
  }

  const config = riskConfig[data.ctcae_grade || data.risk_level] || riskConfig.Low;
  const Icon = config.icon;

  return (
    <Layout>
      <div className="max-w-2xl mx-auto pt-8 px-4 animate-fade-in">
        <Link to="/history" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-primary mb-6 transition-colors">
          <ArrowLeft size={16} />
          返回历史记录
        </Link>

        {/* Risk Banner */}
        <div className={`rounded-3xl overflow-hidden shadow-2xl mb-8 border ${config.border}`}>
          <div className={`h-3 bg-gradient-to-r ${config.gradient}`}></div>
          <div className={`p-8 ${config.bg}`}>
            <div className="flex items-center gap-4 mb-4">
              <div className={`p-3 rounded-2xl bg-white shadow-sm ${config.text}`}>
                <Icon size={32} />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-bold uppercase tracking-wider ${config.text}`}>风险分级</span>
                    {data.learned ? (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase bg-blue-100 text-blue-700 border border-blue-200 flex items-center gap-1 shadow-sm">
                        <Brain size={10} />
                        已学习
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase bg-gray-100 text-gray-500 border border-gray-200 flex items-center gap-1 shadow-sm">
                        <Clock size={10} />
                        未学习
                      </span>
                    )}
                  </div>
                  {data.ctcae_grade && (
                    <span className="text-xs px-2 py-0.5 bg-white/50 rounded-full font-bold border border-current/10">
                      {data.ctcae_grade}
                    </span>
                  )}
                </div>
                <h2 className={`text-3xl font-black ${config.text}`}>{config.label}</h2>
                {data.action_required && (
                   <div className={`text-sm font-bold mt-1 opacity-80 ${config.text}`}>需采取行动：{data.action_required}</div>
                )}
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
              className={`mt-8 w-full ${config.color} text-white font-bold py-4 rounded-2xl shadow-lg hover:shadow-2xl hover:-translate-y-1 transition-all`}
            >
              {config.buttonLabel || '立即联系医疗团队'}
            </button>
          )}
        </div>

        {/* Evidence Accordion */}
        <div className="bg-gray-50 rounded-2xl p-6 border border-gray-100 mb-12">
          <h4 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-4">评估依据</h4>
          <div className="text-gray-600 text-sm leading-relaxed italic">
            {data.evidence}
          </div>
          <div className="mt-4 pt-4 border-t border-gray-200 flex justify-between text-[10px] text-gray-400 font-mono">
            <span>命中规则: {data.matched_rule_id}</span>
            <span>系统版本: {data.version}</span>
          </div>
        </div>

        {/* Conversation History */}
        <div className="mt-12 mb-20 animate-in fade-in slide-in-from-bottom-4 duration-700 delay-300">
          <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
            <MessageSquare className="text-primary" size={24} />
            完整对话记录
          </h3>
          <div className="space-y-6 bg-gray-50/30 p-8 rounded-[2rem] border border-gray-100 shadow-inner">
            {isHistoryLoading ? (
               <div className="animate-pulse space-y-4">
                 <div className="h-12 bg-gray-200 rounded-2xl w-2/3"></div>
                 <div className="h-12 bg-gray-200 rounded-2xl w-1/2 ml-auto"></div>
                 <div className="h-12 bg-gray-200 rounded-2xl w-3/4"></div>
               </div>
            ) : history && history.length > 0 ? (
              history.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[90%] p-5 rounded-2xl shadow-sm ${
                    msg.role === 'user' 
                      ? 'bg-primary text-white rounded-tr-none' 
                      : 'bg-white text-gray-800 border border-gray-100 rounded-tl-none'
                  }`}>
                    <div className="flex items-center gap-2 mb-1 opacity-70">
                       <span className="text-[10px] font-black uppercase tracking-tighter">
                         {msg.role === 'user' ? '患者' : '助手'}
                       </span>
                    </div>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-center text-gray-400 py-10 italic">暂无详细对话记录</p>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}
