import React from 'react';
import { Link } from 'react-router-dom';
import { Activity, History } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <nav className="bg-white/80 backdrop-blur-md sticky top-0 z-50 border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center text-white shadow-lg group-hover:rotate-12 transition-transform">
              <Activity size={24} />
            </div>
            <span className="font-bold text-xl text-gray-800">深至医疗</span>
          </Link>
          
          <div className="flex items-center gap-6">
            <Link to="/history" className="text-gray-600 hover:text-primary transition-colors flex items-center gap-1">
              <History size={18} />
              <span className="text-sm font-medium">历史记录</span>
            </Link>
          </div>
        </div>
      </nav>
      
      <main className="pb-20">
        {children}
      </main>
    </div>
  );
}
