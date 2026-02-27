import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Briefcase } from '@phosphor-icons/react';
import { createOpportunity } from '@/lib/api';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

const SERVICES = [
  'IA (Inteligencia Artificial)',
  'BRE (Boutique de Recursos Especializados)',
  'SEC (Ciberseguridad)',
  'ITSM',
  'CSP',
  'Cloud and Data',
  'ADM (Servicios Administrados)',
  'SEG (Seguridad Integral)',
];

interface OpportunityFormProps {
  sessionId?: string | null;
  defaultService?: string;
  onSuccess?: () => void;
  triggerLabel?: string;
}

export const OpportunityForm: React.FC<OpportunityFormProps> = ({
  sessionId,
  defaultService = '',
  onSuccess,
  triggerLabel = 'Registrar cotización',
}) => {
  const [open, setOpen] = useState(false);
  const [contactName, setContactName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [company, setCompany] = useState('');
  const [service, setService] = useState(defaultService);
  const [submitting, setSubmitting] = useState(false);
  const queryClient = useQueryClient();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim() || !company.trim() || !service.trim()) {
      toast.error('Completa teléfono, empresa y servicio (mínimo)');
      return;
    }
    setSubmitting(true);
    try {
      await createOpportunity({
        phone: phone.trim(),
        company: company.trim(),
        service: service.trim(),
        contact_name: contactName.trim() || undefined,
        email: email.trim() || undefined,
        session_id: sessionId || undefined,
      });
      toast.success('Oportunidad registrada. Se guardó en el panel de oportunidades.');
      setContactName('');
      setEmail('');
      setPhone('');
      setCompany('');
      setService(defaultService || '');
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ['opportunities'] });
      queryClient.invalidateQueries({ queryKey: ['opportunities-summary'] });
      onSuccess?.();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Error al registrar');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1.5">
          <Briefcase className="w-4 h-4" />
          {triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Registrar oportunidad de cotización</DialogTitle>
          <p className="text-xs text-muted-foreground mt-1">
            Los datos se guardan en el panel de oportunidades y un ejecutivo te contactará.
          </p>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="opp-name" className="block">Nombre completo</Label>
            <Input
              id="opp-name"
              placeholder="Tu nombre"
              value={contactName}
              onChange={(e) => setContactName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="opp-email" className="block">Correo electrónico</Label>
            <Input
              id="opp-email"
              type="email"
              placeholder="correo@empresa.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="opp-phone" className="block">Teléfono *</Label>
            <Input
              id="opp-phone"
              type="tel"
              placeholder="+506 8888 8888"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="opp-company" className="block">Empresa</Label>
            <Input
              id="opp-company"
              placeholder="Nombre de la empresa"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="opp-service" className="block">Servicio de interés *</Label>
            <select
              id="opp-service"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={service}
              onChange={(e) => setService(e.target.value)}
              required
            >
              <option value="">Selecciona un servicio</option>
              {SERVICES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? 'Registrando...' : 'Registrar'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
