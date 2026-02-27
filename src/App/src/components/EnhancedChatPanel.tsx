import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { ChatMessage, Product } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Add20Regular } from '@fluentui/react-icons';
import { PaperPlaneRight } from '@phosphor-icons/react';
import React, { useEffect, useRef, useState } from 'react';
import { EnhancedChatMessageBubble } from './EnhancedChatMessageBubble';
import { OpportunityForm } from './Opportunities/OpportunityForm';
import { SecurityBlock } from './Security/SecurityBlock';

interface BlockedError {
  attackType: string;
  severity: string;
  message: string;
  correlationId?: string;
  suggestedPrompts?: string[];
}

interface EnhancedChatPanelProps {
  messages: ChatMessage[];
  onSendMessage: (content: string) => void;
  onNewChat: () => void;
  isTyping: boolean;
  isOpen: boolean;
  onClose: () => void;
  onRequestQuote?: (product: Product) => void;
  className?: string;
  isLoading?: boolean;
  blockedError?: BlockedError | null;
  onDismissBlocked?: () => void;
  sessionId?: string | null;
}

export const EnhancedChatPanel = ({
  messages,
  onSendMessage,
  onNewChat,
  isTyping,
  isOpen,
  onClose,
  onRequestQuote,
  className,
  isLoading = false,
  blockedError,
  onDismissBlocked,
  sessionId,
}: EnhancedChatPanelProps) => {
  const [inputValue, setInputValue] = useState('');
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    if (inputValue.trim()) {
      onSendMessage(inputValue.trim());
      setInputValue('');
      // Focus the input after sending
      setTimeout(() => {
        inputRef.current?.focus();
      }, 0);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Maintain focus on input when not typing
  useEffect(() => {
    if (!isTyping && !isLoading && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isTyping, isLoading]);

  return (
    <div className={cn("flex flex-col h-full bg-background", className)}>
      {/* Scrollable Chat Content Area - Takes remaining space */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <ScrollArea className="flex-1 h-full" ref={scrollAreaRef}>
          <div className="p-6 space-y-6">
            {/* Loading State - Show skeleton when loading chat history */}
            {isLoading && messages.length === 0 ? (
              <div className="space-y-4">
                {/* Loading skeleton for messages */}
                <div className="flex gap-3 justify-start">
                  <Skeleton className="w-8 h-8 rounded-full flex-shrink-0" />
                  <div className="space-y-2 flex-1 max-w-[80%]">
                    <Skeleton className="h-16 w-full rounded-2xl" />
                  </div>
                </div>
                <div className="flex gap-3 justify-end">
                  <div className="space-y-2 flex-1 max-w-[80%] flex flex-col items-end">
                    <Skeleton className="h-12 w-3/4 rounded-2xl" />
                  </div>
                  <Skeleton className="w-8 h-8 rounded-full flex-shrink-0" />
                </div>
                <div className="flex gap-3 justify-start">
                  <Skeleton className="w-8 h-8 rounded-full flex-shrink-0" />
                  <div className="space-y-2 flex-1 max-w-[80%]">
                    <Skeleton className="h-20 w-full rounded-2xl" />
                  </div>
                </div>
              </div>
            ) : (
              <>
                {/* Security Block - when message was blocked */}
                {blockedError && (
                  <div className="mb-4">
                    <SecurityBlock
                      attackType={blockedError.attackType}
                      severity={blockedError.severity}
                      message={blockedError.message}
                      correlationId={blockedError.correlationId}
                      suggestedPrompts={blockedError.suggestedPrompts}
                      onDismiss={onDismissBlocked}
                    />
                  </div>
                )}
                {/* Welcome Message - Only show when no messages and not loading */}
                {messages.length === 0 && !isTyping && !isLoading && (
              <div className="flex flex-col items-center justify-center text-center space-y-6 h-full min-h-[400px]">
                {/* AI Assistant Icon - OPTI branding */}
                <img 
                  src="/opti-logo.png" 
                  alt="OPTI - tecnologías que dan valor" 
                  className="w-20 h-auto object-contain"
                />
                
                {/* Welcome Text */}
                <div className="space-y-2">
                  <h2 className="text-xl font-semibold text-foreground">
                    ¡Hola! Estoy aquí para ayudarte.
                  </h2>
                  <p className="text-muted-foreground max-w-sm">
                    Pregúntame sobre nuestros servicios, cotizaciones, políticas o cualquier duda.
                  </p>
                </div>
                
                {/* Quick Start Hint */}
                <div className="text-xs text-muted-foreground">
                  Haz clic en el icono + para iniciar una nueva conversación
                </div>
              </div>
            )}

            {/* Chat Messages */}
            {messages.map((message) => (
              <EnhancedChatMessageBubble
                key={message.id}
                message={message}
                onRequestQuote={onRequestQuote}
              />
            ))}
            
            {/* Typing Indicator - Only show when AI is actively responding */}
            {isTyping && !isLoading && (
              <div className="space-y-1">
                <EnhancedChatMessageBubble
                  message={{
                    id: 'typing',
                    content: '',
                    sender: 'assistant',
                    timestamp: new Date()
                  }}
                  isTyping={true}
                />
                <p className="text-xs text-muted-foreground pl-2">
                  Procesando... Si tarda más de lo habitual, el servicio puede estar ocupado. Por favor espera.
                </p>
              </div>
            )}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
      </div>

      {/* Fixed Input Footer */}
      <div className="flex-shrink-0 border-t bg-background p-4 space-y-3">
        {/* Registrar cotización - acceso rápido */}
        <div className="flex justify-end">
          <OpportunityForm sessionId={sessionId} />
        </div>
        {/* Input Field */}
        <div className="flex-1 relative">
          <Input
            ref={inputRef}
            placeholder="Ask a question"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyPress}
            className="pr-16 resize-none min-h-[40px]"
            disabled={isTyping || isLoading}
          />
          <div className="absolute right-1 top-1/2 transform -translate-y-1/2 flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              title="Nueva conversación"
              onClick={onNewChat}
              disabled={isTyping || isLoading}
            >
              <Add20Regular className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              title="Enviar mensaje"
              onClick={handleSend}
              disabled={!inputValue.trim() || isTyping || isLoading}
            >
              <PaperPlaneRight className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Disclaimer */}
        <p className="text-xs text-muted-foreground text-center">
          El contenido generado por IA puede contener errores
        </p>
      </div>
    </div>
  );
};
