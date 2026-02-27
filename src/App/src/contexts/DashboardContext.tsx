import React, { createContext, useContext, useState, useCallback } from 'react';

export type DashboardView = 'dashboard' | 'chat' | 'security' | 'opportunities' | 'catalog';

export interface DashboardStats {
  totalRequests: number;
  blockedRequests: number;
  promptInjectionAttempts: number;
  opportunitiesDetected: number;
  hasBlockedThisSession: boolean;
}

interface DashboardContextType {
  activeView: DashboardView;
  setActiveView: (view: DashboardView) => void;
  stats: DashboardStats;
  incrementTotalRequests: () => void;
  incrementBlockedRequests: () => void;
  incrementPromptInjection: () => void;
  incrementOpportunities: () => void;
  setHasBlockedThisSession: (v: boolean) => void;
  resetSessionBlocked: () => void;
}

const defaultStats: DashboardStats = {
  totalRequests: 0,
  blockedRequests: 0,
  promptInjectionAttempts: 0,
  opportunitiesDetected: 0,
  hasBlockedThisSession: false,
};

const DashboardContext = createContext<DashboardContextType | null>(null);

export const DashboardProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeView, setActiveView] = useState<DashboardView>('dashboard');
  const [stats, setStats] = useState<DashboardStats>(defaultStats);

  const incrementTotalRequests = useCallback(() => {
    setStats((s) => ({ ...s, totalRequests: s.totalRequests + 1 }));
  }, []);

  const incrementBlockedRequests = useCallback(() => {
    setStats((s) => ({
      ...s,
      blockedRequests: s.blockedRequests + 1,
      hasBlockedThisSession: true,
    }));
  }, []);

  const incrementPromptInjection = useCallback(() => {
    setStats((s) => ({ ...s, promptInjectionAttempts: s.promptInjectionAttempts + 1 }));
  }, []);

  const incrementOpportunities = useCallback(() => {
    setStats((s) => ({ ...s, opportunitiesDetected: s.opportunitiesDetected + 1 }));
  }, []);

  const setHasBlockedThisSession = useCallback((v: boolean) => {
    setStats((s) => ({ ...s, hasBlockedThisSession: v }));
  }, []);

  const resetSessionBlocked = useCallback(() => {
    setStats((s) => ({ ...s, hasBlockedThisSession: false }));
  }, []);

  return (
    <DashboardContext.Provider
      value={{
        activeView,
        setActiveView,
        stats,
        incrementTotalRequests,
        incrementBlockedRequests,
        incrementPromptInjection,
        incrementOpportunities,
        setHasBlockedThisSession,
        resetSessionBlocked,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
};

export const useDashboard = () => {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error('useDashboard must be used within DashboardProvider');
  return ctx;
};
