import React from 'react';
import {
  ChartBar,
  ChatCircle,
  ShieldWarning,
  Briefcase,
  GridFour,
} from '@phosphor-icons/react';
import { useDashboard, type DashboardView } from '@/contexts/DashboardContext';

const navItems: { id: DashboardView; label: string; icon: React.ReactNode }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <ChartBar className="w-5 h-5" /> },
  { id: 'chat', label: 'Chat', icon: <ChatCircle className="w-5 h-5" /> },
  { id: 'security', label: 'Security Events', icon: <ShieldWarning className="w-5 h-5" /> },
  { id: 'opportunities', label: 'Opportunities', icon: <Briefcase className="w-5 h-5" /> },
  { id: 'catalog', label: 'Service Catalog', icon: <GridFour className="w-5 h-5" /> },
];

export const AppSidebar: React.FC = () => {
  const { activeView, setActiveView } = useDashboard();

  return (
    <aside className="w-56 flex-shrink-0 border-r border-border bg-card flex flex-col">
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveView(item.id)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              activeView === item.id
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            {item.icon}
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  );
};
