/**
 * Medical Chat Page
 */
import React, { useState, useEffect, useRef } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Layout } from '../components/Layout';
import { assessmentService } from '../services/api';
import { createNewSessionId } from '../utils/session';
import { logEvent } from '../utils/eventLogger';
import { EventName, type Assessment } from '../types';
import { 
  Send, 
  Loader2, 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle, 
  User, 
  MessageSquare,
  Plus,
  Info,
  Check,
  RotateCcw
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const riskConfig: Record<string, any> = {
  'Grade 1': {
    color: 'text-rose-700',
    bg: 'bg-rose-50',
    border: 'border-rose-200',
    icon: ShieldAlert,
    label: '高风险 (Grade 1)',
    buttonLabel: '立即线下就医',
    glow: 'shadow-rose-100',
    action: '立即线下就医'
  },
  'Grade 2': {
    color: 'text-orange-600',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    icon: AlertTriangle,
    label: '高风险 (Grade 2)',
    buttonLabel: '24小时内联系团队',
    glow: 'shadow-orange-100',
    action: '24小时内联系团队'
  },
  'Grade 3': {
    color: 'text-amber-600',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    icon: MessageSquare,
    label: '中风险 (Grade 3)',
    buttonLabel: '联系团队',
    glow: 'shadow-amber-100',
    action: '联系团队'
  },
  'Grade 4': {
    color: 'text-sky-600',
    bg: 'bg-sky-50',
    border: 'border-sky-200',
    icon: Info,
    label: '中风险 (Grade 4)',
    buttonLabel: '密切观察',
    glow: 'shadow-sky-100',
    action: '密切观察'
  },
  'Grade 5': {
    color: 'text-emerald-600',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    icon: CheckCircle,
    label: '低风险 (Grade 5)',
    buttonLabel: '继续观察与记录',
    glow: 'shadow-emerald-100',
    action: '继续观察与记录'
  }
};

// Fallbacks and legacy support
riskConfig.HIGH = riskConfig['Grade 1'];
riskConfig.MEDIUM = riskConfig['Grade 3'];
riskConfig.LOW = riskConfig['Grade 5'];
riskConfig.Urgent = riskConfig.HIGH;
riskConfig.High = riskConfig.HIGH;
riskConfig.Medium = riskConfig.MEDIUM;
riskConfig.Low = riskConfig.LOW;

interface Message {
  id: string | number;
  role: 'user' | 'assistant';
  content: string;
  assessment?: Assessment;
}

export default function ChatPage() {
  const [userInput, setUserInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState(createNewSessionId());
  const [isInputDisabled, setIsInputDisabled] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load history
  const { data: historyData, isLoading: isHistoryLoading } = useQuery({
    queryKey: ['history', sessionId],
    queryFn: () => assessmentService.getBySession(sessionId),
  });

  useEffect(() => {
    if (historyData) {
      const historyMessages: Message[] = [];
      // Backend returns history as list of {role, content}
      // If it's the old format, it will be handled by the mapping logic below
      
      if (Array.isArray(historyData)) {
        historyData.forEach((item, idx) => {
          if (item.role && item.content) {
            // Check if content contains a JSON block (legacy format)
            let content = item.content;
            let assessment = item.assessment;

            if (!assessment && content.includes('```json')) {
              try {
                const parts = content.split('```json');
                const jsonStr = parts[1].split('```')[0].trim();
                const parsed = JSON.parse(jsonStr);
                if (parsed.type === 'evaluation' && parsed.data) {
                  assessment = parsed.data;
                  content = parts[0].trim();
                }
              } catch (e) {
                console.error('Failed to parse legacy history JSON', e);
              }
            }

            historyMessages.push({
              id: `h-${idx}`,
              role: item.role as 'user' | 'assistant',
              content: content,
              assessment: assessment,
            });
          } else {
             // Support legacy Assessment objects if returned
             historyMessages.push({
               id: `u-${item.id}`,
               role: 'user',
               content: item.user_input,
             });
             historyMessages.push({
               id: `a-${item.id}`,
               role: 'assistant',
               content: item.display_text || item.advice,
               assessment: item,
             });
          }
        });
      }
      setMessages(historyMessages);
    }
  }, [historyData]);

  useEffect(() => {
    logEvent(EventName.ASSESSMENT_STARTED, sessionId);
    
    const handleBeforeUnload = () => {
      logEvent(EventName.ASSESSMENT_CLOSED, sessionId);
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      logEvent(EventName.ASSESSMENT_CLOSED, sessionId);
    };
  }, [sessionId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const mutation = useMutation({
    mutationFn: async (text: string) => {
      const history = messages.map(m => ({
        role: m.role,
        content: m.content,
        assessment: m.assessment
      }));
      return assessmentService.submit(text, sessionId, history);
    },
    onSuccess: (data) => {
      logEvent(EventName.ASSESSMENT_SUBMITTED, sessionId, data.id);
      const aiMessage: Message = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: data.display_text || data.advice,
        assessment: data,
      };
      setMessages(prev => [...prev, aiMessage]);
      
      if (data.risk_level && data.risk_level !== '未知') {
        setIsInputDisabled(true);
      }
    },
  });

  const saveMutation = useMutation({
    mutationFn: async ({ assessment, history }: { assessment: Assessment, history: any[] }) => {
      return assessmentService.save(sessionId, assessment, history);
    },
    onSuccess: () => {
      alert('评估已完成并存入历史。');
      startNewChat();
    }
  });

  const handleFinishAnswer = (assessment: Assessment) => {
    const fullHistory = messages.map(m => ({
      role: m.role,
      content: m.content,
      assessment: m.assessment
    }));
    saveMutation.mutate({ assessment, history: fullHistory });
  };

  const handleSupplement = () => {
    setIsInputDisabled(false);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedInput = userInput.trim();
    if (!trimmedInput || mutation.isPending || isInputDisabled) return;

    const userMsg: Message = {
      id: Date.now(),
      role: 'user',
      content: trimmedInput,
    };

    setMessages(prev => [...prev, userMsg]);
    setUserInput('');
    mutation.mutate(trimmedInput);
  };

  const startNewChat = () => {
    const newId = createNewSessionId();
    setSessionId(newId);
    setMessages([]);
    setUserInput('');
    setIsInputDisabled(false);
  };

  const handleContactTeam = (assessment: Assessment) => {
    logEvent(EventName.CONTACT_TEAM_CLICKED, sessionId, assessment.id);
    alert('已收到您的协同请求，团队将尽快与您联系。');
  };

  return (
    <Layout>
      <div className="max-w-3xl mx-auto h-[calc(100vh-140px)] flex flex-col bg-white rounded-3xl shadow-2xl border border-gray-100 overflow-hidden mt-4 animate-fade-in">
        {/* Header */}
        <div className="p-6 border-b border-gray-50 flex items-center justify-between bg-white z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center text-primary">
              <MessageSquare size={24} />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900">副作用评估助手</h1>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                <span className="text-xs text-gray-500 font-medium">在线 | 专业医学指南支持</span>
              </div>
            </div>
          </div>

          <button
            onClick={startNewChat}
            className="flex items-center gap-2 px-4 py-2 bg-gray-50 hover:bg-gray-100 text-gray-600 rounded-xl text-sm font-bold transition-all border border-gray-100"
          >
            <Plus size={16} />
            新对话
          </button>
        </div>

        {/* Chat Content */}
        <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-6 space-y-8 scroll-smooth"
        >
          {messages.length === 0 && !isHistoryLoading && (
            <div className="text-center py-20">
              <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4 text-gray-300">
                <Info size={32} />
              </div>
              <h3 className="text-gray-900 font-bold mb-2">欢迎使用评估系统</h3>
              <p className="text-gray-500 text-sm max-w-xs mx-auto">
                请描述您当前的症状，例如：“我今天感觉手脚有点麻木，持续了几个小时。”
              </p>
            </div>
          )}

          <AnimatePresence initial={false}>
            {messages.map((message, idx) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex gap-3 max-w-[85%] ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 ${
                    message.role === 'user' ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600'
                  }`}>
                    {message.role === 'user' ? <User size={16} /> : <MessageSquare size={16} />}
                  </div>
                  
                  <div className="space-y-3">
                    {(!message.assessment || message.role === 'user' || message.assessment.risk_level === '未知') && (
                      <div className={`chat-bubble ${message.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}`}>
                        {message.content}
                      </div>
                    )}

                    {/* Inline Assessment Result */}
                    {message.assessment && message.assessment.risk_level !== '未知' && (
                      <motion.div 
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className={`rounded-2xl border-2 ${riskConfig[message.assessment.ctcae_grade || message.assessment.risk_level]?.border || 'border-gray-100'} ${riskConfig[message.assessment.ctcae_grade || message.assessment.risk_level]?.bg || 'bg-gray-50'} p-5 shadow-lg ${riskConfig[message.assessment.ctcae_grade || message.assessment.risk_level]?.glow || ''} relative overflow-hidden`}
                      >
                        {/* Decorative Background Pattern */}
                        <div className={`absolute top-0 right-0 w-32 h-32 opacity-10 -mr-8 -mt-8 rounded-full ${riskConfig[message.assessment.ctcae_grade || message.assessment.risk_level]?.color.replace('text', 'bg')}`}></div>
                        
                        <div className="relative z-10">
                          <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                              <div className={`p-1.5 rounded-lg ${riskConfig[message.assessment.ctcae_grade || message.assessment.risk_level]?.bg.replace('50', '100')}`}>
                                {React.createElement(riskConfig[message.assessment.ctcae_grade || message.assessment.risk_level]?.icon || Info, { 
                                  size: 20, 
                                  className: riskConfig[message.assessment.ctcae_grade || message.assessment.risk_level]?.color 
                                })}
                              </div>
                              <span className={`text-base font-bold ${riskConfig[message.assessment.ctcae_grade || message.assessment.risk_level]?.color}`}>
                                {riskConfig[message.assessment.ctcae_grade || message.assessment.risk_level]?.label}
                              </span>
                            </div>
                            {message.assessment.ctcae_grade && (
                              <span className="text-[10px] px-2 py-0.5 bg-white/50 rounded-full font-bold border border-current/10 opacity-70">
                                {message.assessment.ctcae_grade}
                              </span>
                            )}
                          </div>

                          {message.assessment.action_required && (
                            <div className={`text-sm font-black mb-2 ${riskConfig[message.assessment.ctcae_grade || message.assessment.risk_level]?.color}`}>
                              需采取行动：{message.assessment.action_required}
                            </div>
                          )}

                          {message.assessment.display_text && (
                            <div className="mb-4 text-sm text-gray-700 font-medium px-1 leading-relaxed">
                              {message.assessment.display_text}
                            </div>
                          )}

                          <div className="flex flex-col gap-3">
                            <div className="flex items-center gap-1.5">
                              <div className={`w-1.5 h-1.5 rounded-full ${riskConfig[message.assessment.ctcae_grade || message.assessment.risk_level]?.color.replace('text', 'bg')}`}></div>
                              <span className="text-[11px] font-extrabold text-gray-400 uppercase tracking-widest">下一步建议</span>
                            </div>
                            <div className="text-sm text-gray-800 leading-relaxed font-medium">{message.assessment.advice}</div>
                          </div>

                          <div className="mt-4 pt-4 border-t border-gray-100/50 flex flex-col gap-3">
                            <div className="flex items-center gap-1.5">
                              <div className={`w-1.5 h-1.5 rounded-full ${riskConfig[message.assessment.ctcae_grade || message.assessment.risk_level]?.color.replace('text', 'bg')}`}></div>
                              <span className="text-[11px] font-extrabold text-gray-400 uppercase tracking-widest">评估依据</span>
                            </div>
                            <div className="text-[11px] text-gray-500 leading-relaxed italic">{message.assessment.evidence}</div>
                          </div>
  
                          <div className="flex items-center justify-between pt-2 border-t border-gray-100/50 mb-4">
                            <div className="text-[10px] text-gray-400 font-mono bg-gray-100/50 px-2 py-0.5 rounded">
                              RULE: {message.assessment.matched_rule_id}
                            </div>
                            {message.assessment.contact_team && (
                              <button
                                onClick={() => handleContactTeam(message.assessment!)}
                                className={`px-4 py-2 ${riskConfig[message.assessment.ctcae_grade || message.assessment.risk_level]?.color.replace('text', 'bg')} ${riskConfig[message.assessment.ctcae_grade || message.assessment.risk_level]?.color} text-xs font-bold rounded-xl hover:brightness-95 transition-all shadow-sm active:scale-95`}
                              >
                                {riskConfig[message.assessment.ctcae_grade || message.assessment.risk_level]?.buttonLabel || '联系团队'}
                              </button>
                            )}
                          </div>

                          {/* Action Buttons for multi-turn flow (Only for the latest message) */}
                          {idx === messages.length - 1 && isInputDisabled && (
                            <div className="flex gap-3 mt-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                              <button
                                onClick={() => handleFinishAnswer(message.assessment!)}
                                disabled={saveMutation.isPending}
                                className="flex-1 flex items-center justify-center gap-2 py-3 bg-gray-900 text-white rounded-xl text-sm font-bold hover:bg-gray-800 transition-all shadow-lg active:scale-95 disabled:opacity-50"
                              >
                                {saveMutation.isPending ? <Loader2 className="animate-spin" size={16} /> : <Check size={16} />}
                                结束回答
                              </button>
                              <button
                                onClick={handleSupplement}
                                className="flex-1 flex items-center justify-center gap-2 py-3 bg-white text-gray-700 border border-gray-200 rounded-xl text-sm font-bold hover:bg-gray-50 transition-all shadow-sm active:scale-95"
                              >
                                <RotateCcw size={16} />
                                我要补充
                              </button>
                            </div>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {mutation.isPending && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex justify-start"
            >
              <div className="flex gap-3 items-center">
                <div className="w-8 h-8 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center">
                  <MessageSquare size={16} />
                </div>
                <div className="chat-bubble chat-bubble-ai flex items-center gap-2">
                  <Loader2 className="animate-spin" size={16} />
                  <span>助手正在思考中...</span>
                </div>
              </div>
            </motion.div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-6 border-t border-gray-50 bg-gray-50/30">
          <form onSubmit={handleSubmit} className="relative">
            <textarea
              rows={1}
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              disabled={isInputDisabled || mutation.isPending}
              placeholder={isInputDisabled ? "请选择‘结束回答’或‘我要补充’" : "描述您的症状..."}
              className={`w-full bg-white pl-4 pr-16 py-4 rounded-2xl border border-gray-200 focus:ring-2 focus:ring-primary focus:border-transparent transition-all resize-none shadow-sm block ${isInputDisabled ? 'opacity-50 cursor-not-allowed bg-gray-100' : ''}`}
            />
            <button
              type="submit"
              disabled={!userInput.trim() || mutation.isPending || isInputDisabled}
              className="absolute right-3 bottom-3 w-10 h-10 bg-primary text-white rounded-xl flex items-center justify-center shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:transform-none"
            >
              <Send size={18} />
            </button>
          </form>
          <p className="mt-3 text-[10px] text-gray-400 text-center uppercase tracking-widest font-medium">
            AI 建议仅供参考，不作为医疗诊断。
          </p>
        </div>
      </div>
    </Layout>
  );
}
