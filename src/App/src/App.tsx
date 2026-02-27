import { AppSidebar } from '@/components/Layout/AppSidebar';
import { ChatSidebar } from '@/components/Layout/ChatSidebar';
import { DashboardHeader } from '@/components/Layout/DashboardHeader';
import { DashboardView } from '@/components/Dashboard/DashboardView';
import { SecurityEventsView } from '@/components/Security/SecurityEventsView';
import { OpportunitiesView } from '@/components/Opportunities/OpportunitiesView';
import { CatalogView } from '@/components/Catalog/CatalogView';
import { ProductGrid } from '@/components/ProductGrid';
import { useDashboard } from '@/contexts/DashboardContext';
import {
  clearCurrentSessionId,
  createNewChatSession,
  createTimestamp,
  getChatHistory,
  getCurrentSessionId,
  getProducts,
  saveCurrentSessionId,
  sendMessageToChat,
} from '@/lib/api';
import { filterProducts, sortProducts } from '@/lib/data';
import { ChatMessage, Product, SortBy } from '@/lib/types';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { DashboardProvider } from '@/contexts/DashboardContext';

function AppContent() {
  const queryClient = useQueryClient();
  const {
    activeView,
    stats,
    incrementTotalRequests,
    incrementBlockedRequests,
    incrementPromptInjection,
    setHasBlockedThisSession,
  } = useDashboard();

  const { data: products = [], isLoading: productsLoading } = useQuery({
    queryKey: ['products'],
    queryFn: getProducts,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const [currentSessionId, setCurrentSessionId] = useState<string | null>(() =>
    getCurrentSessionId()
  );
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [blockedError, setBlockedError] = useState<{
    attackType: string;
    severity: string;
    message: string;
    correlationId?: string;
    suggestedPrompts?: string[];
  } | null>(null);

  const { data: chatMessages = [], refetch: refetchChat } = useQuery({
    queryKey: ['chat', currentSessionId],
    queryFn: () => getChatHistory(currentSessionId || undefined),
    enabled: false,
    staleTime: 0,
  });

  const [searchQuery] = useState('');
  const [selectedCategory] = useState('All');
  const [sortBy] = useState<SortBy>('name');

  useEffect(() => {
    if (currentSessionId) saveCurrentSessionId(currentSessionId);
  }, [currentSessionId]);

  const filteredProducts = useMemo(() => {
    const filters = {
      category: selectedCategory,
      minPrice: 0,
      maxPrice: 1000,
      minRating: 0,
      inStockOnly: false,
    };
    return sortProducts(filterProducts(products, searchQuery, filters), sortBy);
  }, [products, searchQuery, selectedCategory, sortBy]);

  const handleRequestQuote = async (product: Product) => {
    setIsChatOpen(true);
    const msg = `Quiero solicitar cotización para: ${product.title}`;
    await handleSendMessage(msg);
  };

  const sendMessageMutation = useMutation({
    mutationFn: ({ message, sessionId }: { message: string; sessionId?: string }) =>
      sendMessageToChat(message, sessionId),
    onSuccess: (newMessage, vars) => {
      queryClient.setQueryData(['chat', currentSessionId], (old: ChatMessage[] = []) => [
        ...old,
        newMessage,
      ]);
      setIsTyping(false);
    },
    onError: (error: any) => {
      const res = error?.response?.data;
      const detail = res?.detail;
      const isBlocked = error?.response?.status === 400 && (detail?.blocked || res?.blocked);
      if (isBlocked) {
        incrementBlockedRequests();
        setHasBlockedThisSession(true);
        const reason = detail?.blocked_reason || detail?.attack_type || '';
        if (reason === 'prompt_injection' || reason === 'jailbreak') {
          incrementPromptInjection();
        }
        setBlockedError({
          attackType: detail?.attack_type || detail?.blocked_reason || 'other',
          severity: detail?.severity || 'high',
          message: detail?.message || 'Solicitud bloqueada por políticas de seguridad.',
          correlationId: detail?.correlation_id,
          suggestedPrompts: detail?.suggested_prompts,
        });
        queryClient.invalidateQueries({ queryKey: ['security-stats'] });
        queryClient.invalidateQueries({ queryKey: ['security-events'] });
        toast.error('Solicitud bloqueada');
      } else {
        const msg =
          typeof detail === 'string'
            ? detail
            : detail?.message || res?.message || 'Error al enviar. Si el servicio está ocupado, usa «Registrar cotización» para guardar tus datos.';
        toast.error(msg);
      }
      setIsTyping(false);
    },
  });

  const createNewSessionMutation = useMutation({
    mutationFn: createNewChatSession,
    onSuccess: (sessionData) => {
      clearCurrentSessionId();
      setCurrentSessionId(sessionData.session_id);
      queryClient.setQueryData(['chat', sessionData.session_id], []);
      queryClient.invalidateQueries({ queryKey: ['chat'] });
    },
    onError: () => toast.error('Failed to create new chat session'),
  });

  const handleSendMessage = async (content: string) => {
    incrementTotalRequests(); // Actualiza al enviar (antes de la llamada API)
    if (!currentSessionId) {
      try {
        const sessionData = await createNewChatSession();
        setCurrentSessionId(sessionData.session_id);
        saveCurrentSessionId(sessionData.session_id);
        const userMessage: ChatMessage = {
          id: `user-${Date.now()}`,
          content,
          sender: 'user',
          timestamp: createTimestamp(),
        };
        queryClient.setQueryData(['chat', sessionData.session_id], [userMessage]);
        setIsTyping(true);
        sendMessageMutation.mutate({ message: content, sessionId: sessionData.session_id });
      } catch {
        toast.error('Failed to start chat session');
      }
      return;
    }
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      content,
      sender: 'user',
      timestamp: createTimestamp(),
    };
    queryClient.setQueryData(['chat', currentSessionId], (old: ChatMessage[] = []) => [
      ...old,
      userMessage,
    ]);
    setIsTyping(true);
    sendMessageMutation.mutate({ message: content, sessionId: currentSessionId });
  };

  const handleNewChat = () => createNewSessionMutation.mutate();

  const toggleChat = () => {
    setIsChatOpen((prev) => !prev);
    if (!isChatOpen && currentSessionId) refetchChat();
  };

  const renderMainContent = () => {
    switch (activeView) {
      case 'dashboard':
        return <DashboardView />;
      case 'security':
        return <SecurityEventsView />;
      case 'opportunities':
        return <OpportunitiesView />;
      case 'catalog':
        return <CatalogView onRequestQuote={handleRequestQuote} />;
      case 'chat':
        return (
          <div className="p-6 space-y-4">
            <h2 className="text-xl font-semibold text-foreground">Chat & Servicios</h2>
            <ProductGrid
              products={filteredProducts}
              isLoading={productsLoading}
              onRequestQuote={handleRequestQuote}
            />
          </div>
        );
      default:
        return <DashboardView />;
    }
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <AppSidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <DashboardHeader isChatOpen={isChatOpen} onChatToggle={toggleChat} />
        <div className="flex-1 flex min-h-0">
          <main className="flex-1 min-w-0 overflow-y-auto bg-muted/20">
            {renderMainContent()}
          </main>
          <ChatSidebar
            isOpen={isChatOpen}
            onClose={() => setIsChatOpen(false)}
            messages={chatMessages || []}
            onSendMessage={handleSendMessage}
            onNewChat={handleNewChat}
            isTyping={isTyping}
            isLoading={false}
            onRequestQuote={handleRequestQuote}
            blockedError={blockedError}
            onDismissBlocked={() => setBlockedError(null)}
            sessionId={currentSessionId}
          />
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <DashboardProvider>
      <AppContent />
    </DashboardProvider>
  );
}

export default App;
