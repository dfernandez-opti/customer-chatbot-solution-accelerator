import React from 'react';
import { ShieldWarning } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';

interface SecurityBlockProps {
  attackType: string;
  severity: string;
  message: string;
  correlationId?: string;
  suggestedPrompts?: string[];
  onViewDetails?: () => void;
  onDismiss?: () => void;
}

export const SecurityBlock: React.FC<SecurityBlockProps> = ({
  attackType,
  severity,
  message,
  correlationId,
  suggestedPrompts = [],
  onViewDetails,
  onDismiss,
}) => {
  const severityBorder =
    severity === 'high'
      ? 'border-l-red-500'
      : severity === 'medium'
        ? 'border-l-amber-500'
        : 'border-l-slate-500';

  return (
    <div
      className={`rounded-lg border border-border border-l-4 ${severityBorder} bg-card p-4 shadow-sm`}
    >
      <div className="flex gap-3">
        <div className="flex-shrink-0">
          <ShieldWarning className="w-8 h-8 text-red-500" weight="fill" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-foreground">
            Tu mensaje fue bloqueado
          </h3>
          <p className="text-sm text-muted-foreground mt-1">{message}</p>
          <p className="text-xs text-muted-foreground mt-2">
            Tipo detectado: <strong className="text-foreground">{attackType}</strong>
          </p>
          <div className="flex flex-wrap gap-2 mt-3">
            <span className="px-2 py-0.5 rounded text-xs bg-red-500/20 text-red-700 dark:text-red-400">
              {attackType}
            </span>
            <span className="px-2 py-0.5 rounded text-xs bg-amber-500/20 text-amber-700 dark:text-amber-400">
              {severity} Severity
            </span>
            <span className="px-2 py-0.5 rounded text-xs bg-slate-500/20 text-slate-600 dark:text-slate-400">
              Blocked
            </span>
          </div>
          {suggestedPrompts.length > 0 && (
            <p className="text-xs text-muted-foreground mt-3">
              Reformula tu solicitud. Ejemplos seguros:{' '}
              {suggestedPrompts.slice(0, 2).join(' • ')}
            </p>
          )}
          <div className="flex gap-2 mt-4">
            {onViewDetails && (
              <Button variant="outline" size="sm" onClick={onViewDetails}>
                Ver detalles
              </Button>
            )}
            {onDismiss && (
              <Button variant="ghost" size="sm" onClick={onDismiss}>
                Entendido
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
