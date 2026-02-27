import React from 'react';
import { Button } from '@/components/ui/button';
import { ShieldCheck, ShieldWarning, ChatCircle } from '@phosphor-icons/react';
import { useDashboard } from '@/contexts/DashboardContext';
import { ThemeToggle } from '@/components/ThemeToggle';
import { LoginButton } from '@/components/LoginButton';
import { useQuery } from '@tanstack/react-query';
import { getContentSafetyDebug } from '@/lib/api';

interface DashboardHeaderProps {
  isChatOpen?: boolean;
  onChatToggle?: () => void;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  isChatOpen = false,
  onChatToggle,
}) => {
  const { stats } = useDashboard();
  const isProtected = !stats.hasBlockedThisSession;

  /** Verificación REAL: llama a Azure Content Safety, no solo revisa env vars */
  const { data: csDebug } = useQuery({
    queryKey: ['content-safety-debug'],
    queryFn: getContentSafetyDebug,
    staleTime: 60_000,
    refetchInterval: 120_000,
  });

  const contentSafetyStatus =
    csDebug === undefined
      ? 'checking'
      : csDebug === null
        ? 'offline'
        : !csDebug.configured
          ? 'not_configured'
          : csDebug.test_passed === true
            ? 'verified'
            : 'config_failed';

  return (
    <header className="h-16 flex-shrink-0 border-b border-border bg-card flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <img
          src="/opti-logo.png"
          alt="OPTI"
          className="h-7 w-auto object-contain max-h-10"
        />
        <div className="flex flex-col">
          <h1 className="text-base font-semibold text-foreground">
            AI Secure Business Assistant
          </h1>
          <p className="text-xs text-muted-foreground">
            Powered by Microsoft Security
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div
            className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium ${
              isProtected
                ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400'
                : 'bg-red-500/15 text-red-700 dark:text-red-400'
            }`}
          >
            {isProtected ? (
              <ShieldCheck className="w-4 h-4" weight="fill" />
            ) : (
              <ShieldWarning className="w-4 h-4" weight="fill" />
            )}
            <span>Security Status: {isProtected ? 'Protected' : 'Alert'}</span>
          </div>
          <div
            className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${
              contentSafetyStatus === 'verified'
                ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400'
                : contentSafetyStatus === 'config_failed'
                  ? 'bg-red-500/15 text-red-700 dark:text-red-400'
                  : contentSafetyStatus === 'not_configured'
                    ? 'bg-amber-500/15 text-amber-700 dark:text-amber-400'
                    : 'bg-slate-500/15 text-slate-600 dark:text-slate-400'
            }`}
            title={
              contentSafetyStatus === 'verified'
                ? 'Azure Content Safety verificado: la API responde correctamente'
                : contentSafetyStatus === 'config_failed'
                  ? 'Content Safety configurado pero la API falla. Revisa CONTENT_SAFETY_ENDPOINT y KEY en App Service.'
                  : contentSafetyStatus === 'not_configured'
                    ? 'Configura CONTENT_SAFETY_ENABLED, CONTENT_SAFETY_ENDPOINT y CONTENT_SAFETY_KEY en el backend'
                    : contentSafetyStatus === 'offline'
                      ? 'No se pudo conectar con el backend'
                      : 'Verificando...'
            }
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                contentSafetyStatus === 'verified'
                  ? 'bg-emerald-500'
                  : contentSafetyStatus === 'config_failed'
                    ? 'bg-red-500'
                    : contentSafetyStatus === 'not_configured'
                      ? 'bg-amber-500'
                      : 'bg-slate-400 animate-pulse'
              }`}
            />
            Content Safety: {contentSafetyStatus === 'verified' ? 'verificado' : contentSafetyStatus === 'config_failed' ? 'error de conexión' : contentSafetyStatus === 'not_configured' ? 'no configurado' : contentSafetyStatus === 'offline' ? 'sin conexión' : '...'}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {onChatToggle && (
          <Button
            variant={isChatOpen ? 'default' : 'outline'}
            size="sm"
            onClick={onChatToggle}
            className="gap-2"
          >
            <ChatCircle className="w-4 h-4" />
            {isChatOpen ? 'Cerrar Chat' : 'Abrir Chat'}
          </Button>
        )}
        <ThemeToggle />
        <LoginButton />
      </div>
    </header>
  );
};
