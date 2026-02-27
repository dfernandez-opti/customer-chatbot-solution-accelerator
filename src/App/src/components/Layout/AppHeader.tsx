import React from 'react';
import { Button, Text } from '@fluentui/react-components';
import { ChatCircle } from '@phosphor-icons/react';
import { LoginButton } from '@/components/LoginButton';
import { ThemeToggle } from '@/components/ThemeToggle';

interface AppHeaderProps {
  isChatOpen?: boolean;
  onChatToggle?: () => void;
}

export const AppHeader: React.FC<AppHeaderProps> = ({
  isChatOpen = false,
  onChatToggle
}) => {

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="w-full px-6 py-4">
        <div className="flex items-center justify-between w-full">
          {/* Left side - Brand OPTI */}
          <div className="flex items-center gap-3 header-brand">
            <img 
              src="/opti-logo.png" 
              alt="OPTI - tecnologías que dan valor" 
              className="h-10 w-auto object-contain"
            />
            <Text size={500} weight="semibold" className="text-foreground">
              OPTI - tecnologías que dan valor
            </Text>
          </div>
          
          {/* Center - Empty space */}
          <div className="flex-1"></div>
          
          {/* Right side - Actions (sin carrito) */}
          <div className="flex items-center gap-4">
            <Button
              appearance={isChatOpen ? "primary" : "subtle"}
              icon={<ChatCircle className="w-4 h-4" />}
              onClick={() => onChatToggle?.()}
              size="small"
              className="transition-all duration-200"
            >
              <span className="hidden sm:inline">
                {isChatOpen ? 'Cerrar Chat' : 'Abrir Chat'}
              </span>
            </Button>
            
            <ThemeToggle />
            <LoginButton />
          </div>
        </div>
      </div>
    </header>
  );
};
