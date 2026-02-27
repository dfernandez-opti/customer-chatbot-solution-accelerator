import { useDashboard } from '@/contexts/DashboardContext';
import { api, getContentSafetyDebug } from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import React, { useEffect, useState } from 'react';

interface SecurityEvent {
  id: string;
  timestamp: string;
  attack_type: string;
  severity: string;
  action: string;
  correlation_id: string;
  prompt_snippet?: string;
  evidence?: { matched_rules?: string[]; snippet?: string };
  session_id?: string;
}

interface Opportunity {
  id: string;
  timestamp: string;
  company?: string;
  service?: string;
  contact_name?: string;
  phone?: string;
  email?: string;
}

const ATTACK_COLORS: Record<string, string> = {
  prompt_injection: '#f6ad55',
  jailbreak: '#f6ad55',
  credential_theft: '#fc8181',
  data_exfiltration: '#63b3ed',
  violence: '#b794f4',
  self_harm: '#b794f4',
  hate: '#b794f4',
  sexual: '#b794f4',
  other: '#94a3b8',
};

function formatTime(date: Date): string {
  return date.toLocaleTimeString('es-MX', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatTimestamp(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleString('es-MX', { dateStyle: 'short', timeStyle: 'medium' });
}

export const DashboardView: React.FC = () => {
  const { stats } = useDashboard();
  const [clock, setClock] = useState(() => formatTime(new Date()));

  useEffect(() => {
    const t = setInterval(() => setClock(formatTime(new Date())), 1000);
    return () => clearInterval(t);
  }, []);

  const { data: securityEvents = [] } = useQuery({
    queryKey: ['security-events', 'dashboard'],
    queryFn: async (): Promise<SecurityEvent[]> => {
      try {
        const res = await api.get('/api/security/events?limit=50');
        return Array.isArray(res.data) ? res.data : res.data?.data || [];
      } catch {
        return [];
      }
    },
    staleTime: 5000,
    refetchInterval: 30000,
  });

  const { data: opportunitiesSummary } = useQuery({
    queryKey: ['opportunities-summary'],
    queryFn: async () => {
      try {
        const res = await api.get('/api/opportunities/summary');
        return res.data as { total: number };
      } catch {
        return { total: 0 };
      }
    },
    staleTime: 10000,
    refetchInterval: 30000,
  });

  const { data: opportunities = [] } = useQuery({
    queryKey: ['opportunities', 'dashboard'],
    queryFn: async (): Promise<Opportunity[]> => {
      try {
        const res = await api.get<Opportunity[]>('/api/opportunities');
        return res.data || [];
      } catch {
        return [];
      }
    },
    staleTime: 10000,
    refetchInterval: 30000,
  });

  const { data: csDebug } = useQuery({
    queryKey: ['content-safety-debug'],
    queryFn: getContentSafetyDebug,
    staleTime: 60000,
  });

  const contentSafetyVerified = csDebug?.configured && csDebug?.test_passed === true;

  // Aggregate by attack_type
  const blockedEvents = securityEvents.filter((e) => e.action === 'blocked');
  const totalBlocked = blockedEvents.length;
  const promptInjectionCount = blockedEvents.filter(
    (e) => e.attack_type === 'prompt_injection' || e.attack_type === 'jailbreak'
  ).length;

  const byType: Record<string, number> = {};
  blockedEvents.forEach((e) => {
    const t = e.attack_type || 'other';
    byType[t] = (byType[t] || 0) + 1;
  });

  const latestEvent = blockedEvents[0] || null;

  // Risk: simple ratio of blocked to total messages this session
  const totalMsgs = stats.totalRequests;
  const riskPct = totalMsgs > 0 ? Math.min(100, Math.round((stats.blockedRequests / Math.max(totalMsgs, 1)) * 100)) : 0;
  const riskLevel = stats.hasBlockedThisSession ? (riskPct > 50 ? 'HIGH' : 'MED') : 'LOW';

  // Bar chart "Requests vs Blocked (últimos 10)": 10 slots, blue=requests, red=blocked
  const last10 = blockedEvents.slice(0, 10);
  const passedCount = Math.max(0, Math.min(10 - last10.length, stats.totalRequests - stats.blockedRequests));
  const barData: { requests: number; blocked: number }[] = [];
  for (let i = 0; i < 10; i++) {
    if (i < last10.length) barData.push({ requests: 0, blocked: 1 });
    else if (i < last10.length + passedCount) barData.push({ requests: 1, blocked: 0 });
    else barData.push({ requests: 0, blocked: 0 });
  }
  const maxBar = Math.max(1, ...barData.map((d) => d.requests + d.blocked));

  const oppCount = opportunitiesSummary?.total ?? opportunities.length;

  return (
    <div className="dashboard-root bg-[#0a0d12] text-[#e2e8f0] min-h-full p-6">
      {/* HEADER */}
      <div className="flex items-center justify-between mb-7 pb-5 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div
            className="w-2.5 h-2.5 rounded-full bg-[#63b3ed] logo-dot"
            style={{ boxShadow: '0 0 12px #63b3ed' }}
          />
          <h1 className="text-[15px] font-semibold tracking-wider uppercase">Security Operations</h1>
          <div className="font-mono text-[11px] text-[#64748b] bg-[#161c2a] border border-white/10 px-2.5 py-1 rounded">
            OPTI · Executive Dashboard
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div
            className={`flex items-center gap-1.5 font-mono text-[11px] px-2.5 py-1 rounded ${
              contentSafetyVerified
                ? 'text-[#68d391] bg-[rgba(104,211,145,0.12)] border border-[rgba(104,211,145,0.2)]'
                : 'text-[#64748b] bg-[#161c2a] border border-white/10'
            }`}
          >
            <div
              className={`w-1.5 h-1.5 rounded-full ${contentSafetyVerified ? 'bg-[#68d391]' : 'bg-[#64748b]'}`}
            />
            Content Safety · {contentSafetyVerified ? 'Verified' : 'N/A'}
          </div>
          <div className="font-mono text-[11px] text-[#64748b] bg-[#161c2a] border border-white/10 px-2.5 py-1 rounded">
            {clock}
          </div>
        </div>
      </div>

      {/* KPI GRID */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-5">
        <KpiCard
          label="Mensajes enviados"
          value={String(stats.totalRequests)}
          sub="sesión actual"
          color="blue"
          icon="💬"
        />
        <KpiCard
          label="Solicitudes bloqueadas"
          value={String(totalBlocked)}
          sub="backend + content safety"
          color="red"
          icon="🛡"
        />
        <KpiCard
          label="Prompt injection / JB"
          value={String(promptInjectionCount)}
          sub="pattern detector"
          color="orange"
          icon="💉"
        />
        <KpiCard
          label="Oportunidades"
          value={String(oppCount)}
          sub="cotizaciones registradas"
          color="green"
          icon="📋"
        />
        <KpiCard
          label="Risk Level"
          value={riskLevel}
          sub={
            <div className="flex items-center gap-2 mt-1">
              <div className="flex-1 h-1 bg-[#161c2a] rounded overflow-hidden">
                <div
                  className="h-full rounded bg-gradient-to-r from-[#68d391] via-[#f6ad55] to-[#fc8181] transition-all duration-500"
                  style={{ width: `${Math.min(100, riskPct + 10)}%` }}
                />
              </div>
              <span className="font-mono text-[10px] text-[#68d391]">{riskPct}%</span>
            </div>
          }
          color="purple"
          icon=""
        />
      </div>

      {/* MAIN GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-4 mb-4">
        {/* DONUT + SPARKLINES */}
        <div className="bg-[#111520] border border-white/10 rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <span className="text-[11px] font-semibold tracking-wider uppercase text-[#94a3b8]">
              Attack Distribution
            </span>
            <span className="font-mono text-[10px] text-[#64748b]">últimos {totalBlocked} eventos</span>
          </div>
          <div className="flex items-center gap-7">
            <DonutChart segments={donutSegments} total={totalBlocked} />
            <div className="flex-1">
              {attackDistribution.slice(0, 4).map(({ type, count }) => (
                <div key={type} className="flex items-center gap-2 mb-3">
                  <div
                    className="w-2 h-2 rounded-sm flex-shrink-0"
                    style={{ background: ATTACK_COLORS[type] || '#94a3b8' }}
                  />
                  <span className="text-[11px] text-[#94a3b8] flex-1 capitalize">
                    {type.replace(/_/g, ' ')}
                  </span>
                  <span
                    className="font-mono text-xs font-semibold"
                    style={{ color: ATTACK_COLORS[type] || '#94a3b8' }}
                  >
                    {count}
                  </span>
                  <span className="font-mono text-[10px] text-[#64748b] ml-1">
                    {totalBlocked > 0 ? Math.round((count / totalBlocked) * 100) : 0}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Sparklines */}
          {sparkData.length > 0 && (
            <div className="mt-5 pt-4 border-t border-white/10">
              <div className="text-[11px] font-semibold tracking-wider uppercase text-[#94a3b8] mb-3">
                Actividad por categoría (últimas {blockedEvents.length})
              </div>
              <div className="space-y-2">
                {sparkData.map(({ cat, vals, total, color }) => (
                  <div key={cat} className="flex items-center gap-2">
                    <span className="text-[10px] text-[#64748b] w-28 flex-shrink-0 capitalize">
                      {cat.replace(/_/g, ' ')}
                    </span>
                    <div className="flex items-end gap-0.5 flex-1 h-6">
                      {vals.map((v, i) => (
                        <div
                          key={i}
                          className="flex-1 rounded-t transition-all"
                          style={{
                            background: v ? color : `${color}20`,
                            height: v ? '100%' : '20%',
                          }}
                        />
                      ))}
                    </div>
                    <span className="font-mono text-[11px] font-semibold w-6 text-right" style={{ color }}>
                      {total}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* LATEST EVENT */}
        <div className="bg-[#111520] border border-white/10 rounded-lg p-5 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold tracking-wider uppercase text-[#94a3b8]">
              Latest Security Event
            </span>
            <span className="text-[10px] font-semibold tracking-wide px-2 py-0.5 rounded bg-[rgba(252,129,129,0.12)] text-[#fc8181] border border-[rgba(252,129,129,0.3)]">
              LIVE
            </span>
          </div>
          <div className="h-px bg-white/10 -mx-5" />
          {latestEvent ? (
            <>
              <EventField label="Type" value={<Badge color="orange">{latestEvent.attack_type}</Badge>} />
              <EventField
                label="Severity"
                value={
                  <Badge color={latestEvent.severity === 'high' ? 'red' : latestEvent.severity === 'medium' ? 'orange' : 'green'}>
                    {(latestEvent.severity || 'low').toUpperCase()}
                  </Badge>
                }
              />
              <EventField label="Action" value={<Badge color="blue">blocked</Badge>} />
              <div className="h-px bg-white/10 -mx-5" />
              <EventField label="Correlation ID" value={latestEvent.correlation_id} mono small />
              <EventField label="Session" value={latestEvent.session_id || 'anonymous_default'} small />
              <EventField label="Timestamp" value={formatTimestamp(latestEvent.timestamp)} small />
              <div className="h-px bg-white/10 -mx-5" />
              <div className="pt-1">
                <div className="text-[10px] font-medium tracking-wider uppercase text-[#64748b] mb-2">Snippet</div>
                <div className="bg-[#161c2a] border border-white/10 rounded p-2.5 font-mono text-[10px] text-[#64748b] leading-relaxed">
                  {latestEvent.prompt_snippet ||
                    latestEvent.evidence?.snippet ||
                    'Sin snippet'}
                </div>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 gap-2">
              <div className="w-10 h-10 rounded-lg bg-[#161c2a] border border-white/10 flex items-center justify-center text-xl opacity-40">
                🛡
              </div>
              <p className="text-[11px] text-[#64748b] text-center">Sin eventos de seguridad aún.</p>
              <p className="text-[10px] text-[#64748b] text-center">Los bloqueos aparecerán aquí.</p>
            </div>
          )}
        </div>
      </div>

      {/* BOTTOM GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* ATTACK TIMELINE */}
        <div className="bg-[#111520] border border-white/10 rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <span className="text-[11px] font-semibold tracking-wider uppercase text-[#94a3b8]">
              Attack Timeline
            </span>
            <span className="font-mono text-[10px] text-[#64748b]">últimos eventos</span>
          </div>
          <div className="flex flex-col">
            {blockedEvents.slice(0, 6).map((e) => (
              <div
                key={e.id}
                className="grid grid-cols-[80px_10px_1fr_auto] items-start gap-3 py-2.5 border-b border-white/10 last:border-0"
              >
                <div className="font-mono text-[10px] text-[#64748b] pt-0.5">
                  {new Date(e.timestamp).toLocaleTimeString('es-MX', { hour12: false })}
                </div>
                <div
                  className="w-2 h-2 rounded-full mt-1 flex-shrink-0"
                  style={{ background: ATTACK_COLORS[e.attack_type] || '#94a3b8' }}
                />
                <div className="text-[11px] text-[#94a3b8]">
                  <strong className="text-[#e2e8f0] font-medium text-xs">{e.attack_type}</strong>
                  {e.evidence?.matched_rules?.[0] && (
                    <span className="text-[#64748b]"> — {e.evidence.matched_rules[0].slice(0, 30)}...</span>
                  )}
                </div>
                <Badge
                  color={
                    e.severity === 'high'
                      ? 'red'
                      : e.severity === 'medium'
                        ? 'orange'
                        : 'green'
                  }
                >
                  {(e.severity || 'low').toUpperCase()}
                </Badge>
              </div>
            ))}
            {blockedEvents.length === 0 && (
              <div className="py-8 text-center text-[11px] text-[#64748b]">Sin eventos en el timeline.</div>
            )}
          </div>
        </div>

        {/* OPPORTUNITIES */}
        <div className="bg-[#111520] border border-white/10 rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <span className="text-[11px] font-semibold tracking-wider uppercase text-[#94a3b8]">
              Oportunidades registradas
            </span>
            <Badge color="green">{oppCount} total</Badge>
          </div>
          {opportunities.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-6 gap-2">
              <div className="w-10 h-10 bg-[#161c2a] border border-white/10 rounded-lg flex items-center justify-center text-lg opacity-40">
                📋
              </div>
              <p className="text-[11px] text-[#64748b] text-center leading-relaxed">
                Sin oportunidades aún.<br />
                Cuando un usuario solicite cotización<br />
                aparecerá aquí.
              </p>
            </div>
          ) : (
            <div className="space-y-0">
              {opportunities.slice(0, 5).map((opp) => (
                <div
                  key={opp.id}
                  className="flex items-center gap-3 py-2.5 border-b border-white/10 last:border-0"
                >
                  <div className="w-7 h-7 rounded-md bg-[#161c2a] border border-white/10 flex items-center justify-center font-mono text-[11px] font-semibold text-[#63b3ed] flex-shrink-0">
                    {(opp.company || opp.service || '?')[0].toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-[#e2e8f0] truncate">
                      {opp.company || 'Sin empresa'}
                    </div>
                    <div className="text-[10px] text-[#64748b] truncate">{opp.service || 'Sin servicio'}</div>
                  </div>
                  <div className="font-mono text-[10px] text-[#64748b] flex-shrink-0">
                    {new Date(opp.timestamp).toLocaleTimeString('es-MX', { hour12: false })}
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="h-px bg-white/10 -mx-5 my-4" />
          <div className="text-[10px] text-[#64748b] text-center font-mono">
            API: GET /api/opportunities · auto-refresh 30s
          </div>
        </div>
      </div>
    </div>
  );
};

function KpiCard({
  label,
  value,
  sub,
  color,
  icon,
}: {
  label: string;
  value: string;
  sub: React.ReactNode;
  color: 'blue' | 'red' | 'orange' | 'green' | 'purple';
  icon: string;
}) {
  const colors = {
    blue: '#63b3ed',
    red: '#fc8181',
    orange: '#f6ad55',
    green: '#68d391',
    purple: '#b794f4',
  };
  const c = colors[color];
  return (
    <div className="bg-[#111520] border border-white/10 rounded-lg p-4 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: c }} />
      <div className="text-[10px] font-medium tracking-wider uppercase text-[#64748b] mb-2">{label}</div>
      <div className="font-mono text-3xl font-semibold leading-none mb-1" style={{ color: c }}>
        {value}
      </div>
      {typeof sub === 'string' ? (
        <div className="font-mono text-[10px] text-[#64748b]">{sub}</div>
      ) : (
        sub
      )}
      {icon && <div className="absolute right-3 top-3 text-base opacity-25">{icon}</div>}
    </div>
  );
}

function DonutChart({
  segments,
  total,
}: {
  segments: { type: string; count: number; pct: number; len: number; color: string; offset: number }[];
  total: number;
}) {
  const C = 2 * Math.PI * 48;
  return (
    <svg className="flex-shrink-0" width={120} height={120} viewBox="0 0 120 120">
      <circle cx={60} cy={60} r={48} fill="none" stroke="#161c2a" strokeWidth={18} />
      {segments.map((seg, i) => (
        <circle
          key={i}
          cx={60}
          cy={60}
          r={48}
          fill="none"
          stroke={seg.color}
          strokeWidth={18}
          strokeDasharray={`${seg.len} ${C - seg.len}`}
          strokeDashoffset={seg.offset}
          strokeLinecap="round"
        />
      ))}
      <text x={60} y={56} textAnchor="middle" fill="#e2e8f0" fontFamily="IBM Plex Mono" fontSize={18} fontWeight={600}>
        {total}
      </text>
      <text x={60} y={70} textAnchor="middle" fill="#64748b" fontFamily="IBM Plex Sans" fontSize={9}>
        blocked
      </text>
    </svg>
  );
}

function EventField({
  label,
  value,
  mono,
  small,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
  small?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-2">
      <span className="text-[10px] font-medium tracking-wider uppercase text-[#64748b] min-w-[70px]">{label}</span>
      <span
        className={`text-right break-all ${mono ? 'font-mono' : ''} ${small ? 'text-[10px] text-[#64748b]' : 'text-[11px] text-[#e2e8f0]'}`}
      >
        {value}
      </span>
    </div>
  );
}

function Badge({
  children,
  color,
}: {
  children: React.ReactNode;
  color: 'red' | 'orange' | 'green' | 'blue';
}) {
  const styles: Record<string, string> = {
    red: 'bg-[rgba(252,129,129,0.12)] text-[#fc8181] border-[rgba(252,129,129,0.3)]',
    orange: 'bg-[rgba(246,173,85,0.12)] text-[#f6ad55] border-[rgba(246,173,85,0.3)]',
    green: 'bg-[rgba(104,211,145,0.12)] text-[#68d391] border-[rgba(104,211,145,0.3)]',
    blue: 'bg-[rgba(99,179,237,0.15)] text-[#63b3ed] border-[rgba(99,179,237,0.3)]',
  };
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold tracking-wide font-mono border ${styles[color] || styles.blue}`}
    >
      {children}
    </span>
  );
}
