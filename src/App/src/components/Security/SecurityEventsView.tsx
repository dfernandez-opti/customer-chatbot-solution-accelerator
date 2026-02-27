import React, { useState } from 'react';
import { ShieldWarning } from '@phosphor-icons/react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface SecurityEvent {
  id: string;
  timestamp: string;
  attack_type: string;
  severity: string;
  action: string;
  correlation_id: string;
  prompt_snippet?: string;
  evidence?: { matched_rules?: string[] };
  export_status?: string;
}

export const SecurityEventsView: React.FC = () => {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: events = [], isLoading } = useQuery({
    queryKey: ['security-events'],
    queryFn: async (): Promise<SecurityEvent[]> => {
      try {
        const res = await api.get('/api/security/events?limit=20');
        return Array.isArray(res.data) ? res.data : res.data?.data || [];
      } catch {
        return [];
      }
    },
    staleTime: 5000,
  });

  const selected = events.find((e) => e.id === selectedId);

  const severityClass = (s: string) => {
    if (s === 'high') return 'bg-red-500/20 text-red-700 dark:text-red-400';
    if (s === 'medium') return 'bg-amber-500/20 text-amber-700 dark:text-amber-400';
    return 'bg-slate-500/20 text-slate-600 dark:text-slate-400';
  };

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[300px]">
        <ShieldWarning className="w-16 h-16 text-muted-foreground/40 mb-4" />
        <h3 className="text-lg font-medium text-foreground mb-1">
          No security incidents detected
        </h3>
        <p className="text-sm text-muted-foreground text-center max-w-sm">
          Security events will appear here when blocked requests are detected.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 flex gap-6 h-full">
      <div className="flex-1 min-w-0 overflow-auto">
        <h2 className="text-xl font-semibold text-foreground mb-4">
          Security Events
        </h2>
        <div className="rounded-lg border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-3 font-medium">Timestamp</th>
                <th className="text-left p-3 font-medium">Type</th>
                <th className="text-left p-3 font-medium">Severity</th>
                <th className="text-left p-3 font-medium">Action</th>
                <th className="text-left p-3 font-medium">Correlation ID</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr
                  key={e.id}
                  onClick={() => setSelectedId(e.id)}
                  className={`border-t border-border cursor-pointer hover:bg-muted/30 ${
                    selectedId === e.id ? 'bg-muted/50' : ''
                  }`}
                >
                  <td className="p-3">{new Date(e.timestamp).toLocaleString()}</td>
                  <td className="p-3 font-medium">{e.attack_type}</td>
                  <td className="p-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${severityClass(
                        e.severity
                      )}`}
                    >
                      {e.severity}
                    </span>
                  </td>
                  <td className="p-3">{e.action}</td>
                  <td className="p-3 font-mono text-xs truncate max-w-[120px]">
                    {e.correlation_id}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {selected && (
        <div className="w-80 flex-shrink-0 rounded-lg border border-border bg-card p-4">
          <h3 className="text-sm font-semibold text-foreground mb-4">
            Event Details
          </h3>
          <div className="space-y-3 text-sm">
            <div>
              <span className="text-muted-foreground">Evidence</span>
              <p className="mt-1 text-foreground">
                {selected.evidence?.matched_rules?.join(', ') || 'N/A'}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">Prompt Snippet</span>
              <p className="mt-1 text-foreground font-mono text-xs break-words">
                {selected.prompt_snippet || 'N/A'}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">Export Status</span>
              <p className="mt-1">{selected.export_status || 'pending'}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
