import { EnhancedChatPanel } from '@/components/EnhancedChatPanel';
import { ChatMessage, Product } from '@/lib/types';
import React, { useEffect } from 'react';
import PanelRight from './PanelRight';
import PanelRightToolbar from './PanelRightToolbar';
import eventBus from './eventbus';

interface BlockedError {
  attackType: string;
  severity: string;
  message: string;
  correlationId?: string;
  suggestedPrompts?: string[];
}

interface ChatSidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
  messages?: ChatMessage[];
  onSendMessage?: (content: string) => void;
  onNewChat?: () => void;
  isTyping?: boolean;
  isLoading?: boolean;
  onRequestQuote?: (product: Product) => void;
  blockedError?: BlockedError | null;
  onDismissBlocked?: () => void;
  sessionId?: string | null;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  isOpen = true,
  onClose,
  messages = [],
  onSendMessage,
  onNewChat,
  isTyping = false,
  isLoading = false,
  onRequestQuote,
  blockedError,
  onDismissBlocked,
  sessionId,
}) => {
  // Sync the panel state with the isOpen prop
  useEffect(() => {
    if (isOpen) {
      eventBus.emit("setActivePanel", "first");
    } else {
      eventBus.emit("setActivePanel", null);
    }
  }, [isOpen]);

  return (
    <PanelRight 
      panelType="first"
      panelWidth={400}
      panelResize={true}
      defaultClosed={!isOpen}
    >
      <PanelRightToolbar
        panelTitle="Chat"
      />
      
      <div className="h-full">
        <EnhancedChatPanel
          messages={messages}
          onSendMessage={onSendMessage || (() => {})}
          onNewChat={onNewChat || (() => {})}
          isTyping={isTyping}
          isLoading={isLoading}
          isOpen={isOpen}
          onClose={onClose || (() => {})}
          onRequestQuote={onRequestQuote}
          blockedError={blockedError}
          onDismissBlocked={onDismissBlocked}
          sessionId={sessionId}
          className="h-full"
        />
      </div>
    </PanelRight>
  );
};