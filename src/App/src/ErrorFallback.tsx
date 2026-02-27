import { Button, Card, Text } from "@fluentui/react-components";
import { Alert24Regular, ArrowClockwise24Regular } from "@fluentui/react-icons";

export const ErrorFallback = ({ error, resetErrorBoundary }) => {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <img src="/opti-logo.png" alt="OPTI" className="h-12 mx-auto mb-4 opacity-80" />
          <h1 className="text-xl font-semibold text-foreground mb-1">
            Acceso restringido
          </h1>
          <p className="text-muted-foreground text-sm">
            Tu acceso ha sido bloqueado por uso indebido del asistente de inteligencia artificial. Por políticas de seguridad, no podemos continuar la sesión en este momento.
          </p>
        </div>

        <Card className="p-4 border-border">
          <div className="flex items-start gap-3">
            <Alert24Regular className="text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <Text weight="semibold" className="text-foreground">
                ¿Qué puedes hacer?
              </Text>
              <ul className="mt-2 text-sm text-muted-foreground space-y-1 list-disc list-inside">
                <li>Si consideras que fue un error, intenta más tarde con una consulta diferente</li>
                <li>Evita solicitudes que intenten eludir las restricciones del asistente</li>
                <li>Contacta al equipo de OPTI si necesitas asistencia</li>
              </ul>
            </div>
          </div>
        </Card>

        <Button
          onClick={resetErrorBoundary}
          className="w-full"
          appearance="primary"
          icon={<ArrowClockwise24Regular />}
        >
          Reintentar
        </Button>

        {import.meta.env.DEV && (
          <details className="text-xs">
            <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
              Detalles técnicos (solo desarrollo)
            </summary>
            <pre className="mt-2 p-3 rounded bg-muted text-red-600 overflow-auto max-h-24">
              {error?.message || "Error desconocido"}
            </pre>
          </details>
        )}
      </div>
    </div>
  );
}
