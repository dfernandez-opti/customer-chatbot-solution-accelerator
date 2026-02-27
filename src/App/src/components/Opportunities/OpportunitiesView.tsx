import React from 'react';
import { Briefcase, User, EnvelopeSimple, Phone, Building } from '@phosphor-icons/react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface Opportunity {
  id: string;
  timestamp: string;
  phone?: string;
  company?: string;
  service?: string;
  contact_name?: string;
  email?: string;
  inferred_service?: string;
  intent_confidence?: number;
  user_message_snippet?: string;
  status: string;
}

export const OpportunitiesView: React.FC = () => {
  const { data: opportunities = [] } = useQuery({
    queryKey: ['opportunities'],
    queryFn: async () => {
      try {
        const res = await api.get<Opportunity[]>('/api/opportunities');
        return res.data || [];
      } catch {
        return [];
      }
    },
    staleTime: 5000,
    refetchInterval: 15000,
  });

  if (opportunities.length === 0) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[300px]">
        <Briefcase className="w-16 h-16 text-muted-foreground/40 mb-4" />
        <h3 className="text-lg font-medium text-foreground mb-1">
          No hay oportunidades registradas aún
        </h3>
        <p className="text-sm text-muted-foreground text-center max-w-sm">
          Las oportunidades se guardan aquí cuando usas el botón &quot;Registrar cotización&quot; en el chat o cuando el usuario comparte sus datos (nombre, correo, teléfono, empresa).
        </p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold text-foreground">
          Oportunidades ({opportunities.length})
        </h2>
      </div>
      <div className="space-y-4">
        {opportunities.map((opp) => (
          <div
            key={opp.id}
            className="rounded-xl border border-border bg-card p-5 shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="flex justify-between items-start gap-4">
              <div className="flex-1 min-w-0 space-y-3">
                {/* Servicio - destacado */}
                <div>
                  <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Servicio
                  </span>
                  <p className="font-semibold text-foreground mt-0.5">
                    {opp.service || opp.inferred_service || 'Sin servicio'}
                  </p>
                </div>
                {/* Datos de contacto - cada uno en su línea */}
                <div className="grid gap-2 text-sm">
                  {opp.contact_name && (
                    <div className="flex items-center gap-2">
                      <User className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                      <span className="text-foreground">{opp.contact_name}</span>
                    </div>
                  )}
                  {opp.email && (
                    <div className="flex items-center gap-2">
                      <EnvelopeSimple className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                      <a
                        href={`mailto:${opp.email}`}
                        className="text-primary hover:underline truncate"
                      >
                        {opp.email}
                      </a>
                    </div>
                  )}
                  {opp.phone && (
                    <div className="flex items-center gap-2">
                      <Phone className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                      <a
                        href={`tel:${opp.phone.replace(/\D/g, '')}`}
                        className="text-foreground hover:text-primary"
                      >
                        {opp.phone}
                      </a>
                    </div>
                  )}
                  {opp.company && (
                    <div className="flex items-center gap-2">
                      <Building className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                      <span className="text-foreground">{opp.company}</span>
                    </div>
                  )}
                  {!opp.contact_name && !opp.email && !opp.company && !opp.phone && opp.user_message_snippet && (
                    <p className="text-muted-foreground italic">{opp.user_message_snippet}</p>
                  )}
                </div>
                <p className="text-xs text-muted-foreground pt-1">
                  Registrado: {new Date(opp.timestamp).toLocaleString('es-MX', {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  })}
                </p>
              </div>
              <span className="text-xs font-medium px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 flex-shrink-0">
                {opp.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
