import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { assessmentService } from '../services/api';
import { Calendar, ChevronRight, AlertCircle, Clock, SearchX, Plus, Brain, Filter } from 'lucide-react';

const riskBadgeConfig: Record<string, string> = {
  HIGH: 'bg-red-100 text-red-700 border-red-200',
  MEDIUM: 'bg-amber-100 text-amber-700 border-amber-200',
  LOW: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  '未知': 'bg-gray-100 text-gray-700 border-gray-200'
};

export default function HistoryPage() {
  const [showLearned, setShowLearned] = useState(true);
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['history'],
    queryFn: () => assessmentService.getAll(),
  });

  const filteredData = data?.filter(item => showLearned || !item.learned);

  if (isLoading) {
    return (
      <Layout>
        <div className="max-w-3xl mx-auto pt-12 px-4">
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 bg-gray-100 rounded-2xl animate-pulse"></div>
            ))}
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-3xl mx-auto pt-12 px-4 animate-fade-in">
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-black text-gray-900 tracking-tight">历史记录</h1>
            <p className="text-gray-500 mt-1">查看您在该设备上的既往评估报告</p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="flex items-center gap-2 bg-primary text-white font-bold px-4 py-2 rounded-xl shadow-md hover:shadow-lg transition-all text-sm"
            >
              <Plus size={16} />
              开启新对话
            </Link>
          </div>
        </div>

        <div className="flex items-center justify-between mb-6 bg-white p-2 rounded-2xl border border-gray-100 shadow-sm">
          <div className="flex items-center gap-4 px-2">
            <div className="flex items-center gap-2 text-xs font-bold text-gray-400">
              <Clock size={14} />
              {data?.length || 0} 条记录
            </div>
            {data?.some(i => i.learned) && (
              <div className="h-4 w-px bg-gray-200"></div>
            )}
            {data?.some(i => i.learned) && (
              <div className="flex items-center gap-2 text-xs font-bold text-blue-500">
                <Brain size={14} />
                {data?.filter(i => i.learned).length} 条已学习
              </div>
            )}
          </div>
          
          <button 
            onClick={() => setShowLearned(!showLearned)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              !showLearned 
              ? 'bg-blue-50 text-blue-600 border border-blue-100 shadow-inner' 
              : 'bg-gray-50 text-gray-500 border border-gray-100 hover:bg-gray-100'
            }`}
          >
            <Filter size={14} />
            {showLearned ? '过滤已学习' : '显示全部'}
          </button>
        </div>

        {error ? (
          <div className="bg-red-50 p-6 rounded-2xl border border-red-100 flex items-center gap-3 text-red-700">
            <AlertCircle size={24} />
            <p>加载历史记录失败，请刷新重试。</p>
          </div>
        ) : filteredData && filteredData.length > 0 ? (
          <div className="space-y-4">
            {filteredData.map((item) => (
              <Link
                key={item.id}
                to={`/result/${item.id}`}
                className="block bg-white hover:bg-gray-50 p-6 rounded-2xl shadow-sm hover:shadow-md border border-gray-100 transition-all group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0 pr-4">
                    <div className="flex items-center flex-wrap gap-2 mb-2">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase border ${riskBadgeConfig[item.risk_level as string] || riskBadgeConfig.LOW}`}>
                        {item.risk_level === 'HIGH' ? '高风险' : item.risk_level === 'MEDIUM' ? '中风险' : item.risk_level === 'LOW' ? '低风险' : '医学问询'}
                      </span>
                      {item.learned ? (
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase border bg-blue-50 text-blue-600 border-blue-100 flex items-center gap-1">
                          <Brain size={10} />
                          已学习
                        </span>
                      ) : (
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase border bg-gray-50 text-gray-400 border-gray-100 flex items-center gap-1">
                          <Clock size={10} />
                          未学习
                        </span>
                      )}
                      <span className="text-xs text-gray-400 flex items-center gap-1 ml-auto">
                        <Calendar size={12} />
                        {new Date(item.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-gray-800 font-medium truncate italic text-sm mt-3">
                      "{item.user_input}"
                    </p>
                  </div>
                  <ChevronRight className="text-gray-300 group-hover:text-primary transition-colors" size={24} />
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-20 bg-gray-50/50 rounded-3xl border-2 border-dashed border-gray-200">
            <div className="w-16 h-16 bg-white rounded-2xl shadow-sm flex items-center justify-center mx-auto mb-4 text-gray-300">
              <SearchX size={32} />
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">
              {data && data.length > 0 ? '暂无匹配项' : '暂无历史记录'}
            </h3>
            <p className="text-gray-500 mb-6">
              {data && data.length > 0 ? '尝试更改过滤器设置' : '您还没有进行过症状评估'}
            </p>
            {!(data && data.length > 0) && (
              <Link
                to="/"
                className="inline-flex items-center gap-2 bg-primary text-white font-bold px-6 py-3 rounded-xl shadow-lg hover:shadow-xl transition-all"
              >
                去进行第一次评估
              </Link>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
