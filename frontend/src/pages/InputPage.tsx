import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { Layout } from '../components/Layout';
import { MessageSquarePlus, Loader2 } from 'lucide-react';
import { assessmentService } from '../services/api';
import { getOrCreateSessionId } from '../utils/session';
import { logEvent } from '../utils/eventLogger';
import { EventName } from '../types';

export default function InputPage() {
  const [userInput, setUserInput] = useState('');
  const navigate = useNavigate();
  const sessionId = getOrCreateSessionId();

  useEffect(() => {
    logEvent(EventName.ASSESSMENT_STARTED, sessionId);
    return () => {
      logEvent(EventName.ASSESSMENT_CLOSED, sessionId);
    };
  }, []);

  const mutation = useMutation({
    mutationFn: (text: string) => assessmentService.submit(text, sessionId),
    onSuccess: (data) => {
      logEvent(EventName.ASSESSMENT_SUBMITTED, sessionId, data.id);
      navigate(`/result/${data.id}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!userInput.trim() || mutation.isPending) return;
    mutation.mutate(userInput);
  };

  return (
    <Layout>
      <div className="max-w-2xl mx-auto pt-12 px-4 animate-fade-in">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight mb-4">
            副作用评估系统
          </h1>
          <p className="text-lg text-gray-600">
            请详细描述您的症状，我们将为您提供专业的风险评估与建议。
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                症状描述
              </label>
              <textarea
                rows={6}
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                disabled={mutation.isPending}
                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-primary focus:border-transparent transition-all resize-none text-gray-800 disabled:bg-gray-50"
                placeholder="例如：自昨天起出现轻微发烧，伴有恶心感..."
              />
            </div>
            
            <button
              type="submit"
              disabled={!userInput.trim() || mutation.isPending}
              className="w-full bg-primary hover:bg-blue-600 text-white font-bold py-4 rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:transform-none"
            >
              {mutation.isPending ? (
                <>
                  <Loader2 className="animate-spin" size={20} />
                  正在分析中...
                </>
              ) : (
                <>
                  <MessageSquarePlus size={20} />
                  开始评估
                </>
              )}
            </button>
          </form>

          {mutation.isError && (
            <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-xl text-sm border border-red-100">
              评估提交失败，请检查后端服务是否启动。
            </div>
          )}
          
          <div className="mt-8 pt-8 border-t border-gray-50 flex justify-center">
            <Link to="/history" className="text-sm font-medium text-primary hover:underline">
              查看历史记录 →
            </Link>
          </div>
        </div>
      </div>
    </Layout>
  );
}
