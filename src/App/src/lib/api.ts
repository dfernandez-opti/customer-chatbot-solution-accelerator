import axios from 'axios';

const getApiBaseUrl = (): string => {
  if (typeof window !== 'undefined' && (window as any).__RUNTIME_CONFIG__?.VITE_API_BASE_URL) {
    return (window as any).__RUNTIME_CONFIG__.VITE_API_BASE_URL;
  }

  return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60 seconds to handle cold starts
  withCredentials: true, // This is crucial for Easy Auth cookies
});

// Store Easy Auth headers globally
let cachedEasyAuthHeaders: Record<string, string> | null = null;

export const setEasyAuthHeaders = (headers: Record<string, string> | null) => {
  cachedEasyAuthHeaders = headers;
};

// Add request interceptor to handle authentication and correlation ID
api.interceptors.request.use(
  (config) => {
    // Correlation ID for security event tracing
    if (!config.headers['X-Correlation-ID']) {
      config.headers['X-Correlation-ID'] = crypto.randomUUID?.() || `req-${Date.now()}`;
    }
    // Add cached Easy Auth headers to all requests
    if (cachedEasyAuthHeaders && config.headers) {
      Object.keys(cachedEasyAuthHeaders).forEach(key => {
        if (config.headers) {
          config.headers[key] = cachedEasyAuthHeaders![key];
        }
      });
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle authentication redirects
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // If we get a 302 redirect, it means we need to authenticate
    // Don't automatically redirect here, let the UI handle it
    return Promise.reject(error);
  }
);

// Types
export interface Product {
  id: string;
  title: string;
  price: number;
  originalPrice?: number;
  rating: number;
  reviewCount: number;
  image: string;
  category: string;
  inStock: boolean;
  description: string;
  isService?: boolean;
}

export interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

// Timestamp utility functions
export const parseTimestamp = (timestamp: string | Date | number): Date => {
  if (timestamp instanceof Date) {
    return timestamp;
  }
  
  if (typeof timestamp === 'number') {
    return new Date(timestamp);
  }
  
  if (typeof timestamp === 'string') {
    // Handle ISO strings - let Date constructor handle timezone conversion
    return new Date(timestamp);
  }
  
  return new Date();
};

export const formatTimestamp = (timestamp: Date): string => {
  // Use user's local timezone for display
  return timestamp.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
  });
};

export const createTimestamp = (): Date => {
  return new Date();
};

export interface CartItem {
  product: Product;
  quantity: number;
}

// Servicios OPTI - colores designados del branding
const DEMO_PRODUCTS: Product[] = [
  { id: 'OPT-SEC', title: 'Servicios de Ciberseguridad', price: 0, rating: 0, reviewCount: 0, image: 'https://placehold.co/400x400/1C4E60/ffffff?text=SEC', category: 'Ciberseguridad', inStock: true, description: 'Protección integral contra amenazas cibernéticas con reducción de riesgos, visibilidad centralizada y cumplimiento normativo.', isService: true },
  { id: 'OPT-ITSM', title: 'Servicios ITSM', price: 0, rating: 0, reviewCount: 0, image: 'https://placehold.co/400x400/D74A3D/ffffff?text=ITSM', category: 'Gestión IT', inStock: true, description: 'Gestión de servicios de TI para optimizar operaciones y entregar valor al negocio.', isService: true },
  { id: 'OPT-IA', title: 'Servicios de Inteligencia Artificial', price: 0, rating: 0, reviewCount: 0, image: 'https://placehold.co/400x400/F39C12/ffffff?text=IA', category: 'Inteligencia Artificial', inStock: true, description: 'Soluciones de IA para transformar procesos y tomar decisiones basadas en datos.', isService: true },
  { id: 'OPT-BRE', title: 'Boutique de Recursos Especializados', price: 0, rating: 0, reviewCount: 0, image: 'https://placehold.co/400x400/A15C1D/ffffff?text=BRE', category: 'Talento', inStock: true, description: 'Recursos especializados para proyectos tecnológicos de alto impacto.', isService: true },
  { id: 'OPT-CSP', title: 'Servicios CSP', price: 0, rating: 0, reviewCount: 0, image: 'https://placehold.co/400x400/F29C13/ffffff?text=CSP', category: 'Cloud', inStock: true, description: 'Soluciones de Cloud Solution Provider para maximizar el valor de Azure y Microsoft 365.', isService: true },
  { id: 'OPT-CD', title: 'Cloud and Data', price: 0, rating: 0, reviewCount: 0, image: 'https://placehold.co/400x400/81312E/ffffff?text=C%26D', category: 'Cloud y Datos', inStock: true, description: 'Infraestructura cloud y gestión de datos para entornos híbridos y multicloud.', isService: true },
  { id: 'OPT-ADM', title: 'Servicios Administrados', price: 0, rating: 0, reviewCount: 0, image: 'https://placehold.co/400x400/3D8C9B/ffffff?text=ADM', category: 'Managed Services', inStock: true, description: 'Gestión proactiva de infraestructura y operaciones IT para mayor disponibilidad.', isService: true },
  { id: 'OPT-SEG', title: 'Seguridad Integral basada en Microsoft', price: 0, rating: 0, reviewCount: 0, image: 'https://placehold.co/400x400/1C4E60/ffffff?text=SEG', category: 'Seguridad', inStock: true, description: 'Estrategia de seguridad integral basada en el ecosistema Microsoft. Reducción de riesgos cibernéticos, visibilidad centralizada de amenazas, cumplimiento normativo y respuesta proactiva ante incidentes.', isService: true },
];

// API Functions
export interface HealthStatus {
  status: string;
  content_safety: 'enabled' | 'disabled';
  database?: string;
  openai?: string;
  auth?: string;
}

export const getHealthStatus = async (): Promise<HealthStatus | null> => {
  try {
    const response = await api.get<HealthStatus>('/health');
    return response.data;
  } catch {
    return null;
  }
};

/** Content Safety: verificación REAL (llama a Azure, no solo config) */
export interface ContentSafetyDebug {
  configured: boolean;
  test_passed?: boolean;
  test_result?: string;
  error?: string;
  message?: string;
}

export const getContentSafetyDebug = async (): Promise<ContentSafetyDebug | null> => {
  try {
    const response = await api.get<ContentSafetyDebug>('/debug/content-safety');
    return response.data;
  } catch {
    return null;
  }
};

export const getProducts = async (): Promise<Product[]> => {
  try {
    const response = await api.get('/api/products/');
    
    // Check if response has data
    if (!response.data || !Array.isArray(response.data)) {
      throw new Error('Invalid response format from API');
    }
    
    // Transform the data to match frontend interface
    const transformedData = response.data.map((product: any) => ({
      id: product.id,
      title: product.title,
      price: product.price ?? 0,
      originalPrice: product.original_price || undefined,
      rating: product.rating ?? 0,
      reviewCount: product.review_count ?? 0,
      image: product.image || '/opti-logo.png',
      category: product.category,
      inStock: product.in_stock !== false,
      description: product.description || '',
      isService: product.is_service ?? product.isService ?? false
    }));
    
    return transformedData;
  } catch (error: any) {
    // Use demo data when API is unavailable (network error, 500, backend not running)
    const isNetworkError = error.message?.includes('Network Error') || 
      error.code === 'ERR_NETWORK' || 
      error.message?.includes('Failed to fetch');
    const isServerError = error.response?.status >= 500 || error.response?.status === 404;
    
    if (isNetworkError || isServerError) {
      return DEMO_PRODUCTS;
    }
    throw new Error(`Failed to fetch products: ${error.message || 'Unknown error'}`);
  }
};

export const getChatHistory = async (sessionId?: string): Promise<ChatMessage[]> => {
  try {
    if (sessionId) {
      const response = await api.get(`/api/chat/sessions/${sessionId}`);
      const messages = response.data.messages || [];
      
      return messages.map((msg: any) => ({
        id: msg.id,
        content: msg.content,
        sender: msg.sender || msg.message_type,
        timestamp: parseTimestamp(msg.timestamp || msg.created_at)
      }));
    } else {
      const response = await api.get('/api/chat/history');
      
      return response.data.map((msg: any) => ({
        id: msg.id,
        content: msg.content,
        sender: msg.sender || msg.message_type,
        timestamp: parseTimestamp(msg.timestamp || msg.created_at)
      }));
    }
  } catch (error: any) {
    return [];
  }
};

export const sendMessageToChat = async (message: string, sessionId?: string): Promise<ChatMessage> => {
  try {
    const payload: any = { content: message, message_type: 'user' };
    if (sessionId) {
      payload.session_id = sessionId;
    }
    const response = await api.post('/api/chat/message', payload);
    return {
      id: response.data.id,
      content: response.data.content,
      sender: response.data.sender || response.data.message_type,
      timestamp: parseTimestamp(response.data.timestamp || response.data.created_at)
    };
  } catch (error) {
    throw error;
  }
};

export const createNewChatSession = async (): Promise<{ session_id: string; session_name: string; created_at: string }> => {
  try {
    const response = await api.post('/api/chat/sessions/new');
    return response.data.data;
  } catch (error) {
    throw error;
  }
};

const CHAT_SESSION_KEY = 'current_chat_session_id';

export const saveCurrentSessionId = (sessionId: string): void => {
  try {
    localStorage.setItem(CHAT_SESSION_KEY, sessionId);
  } catch (error) {
    // Silently fail if localStorage is not available
  }
};

export const getCurrentSessionId = (): string | null => {
  try {
    return localStorage.getItem(CHAT_SESSION_KEY);
  } catch (error) {
    return null;
  }
};

export const clearCurrentSessionId = (): void => {
  try {
    localStorage.removeItem(CHAT_SESSION_KEY);
  } catch (error) {
    // Silently fail if localStorage is not available
  }
};


export const addToCart = async (productId: string, quantity: number = 1): Promise<void> => {
  try {
    await api.post('/api/cart/add', { product_id: productId, quantity });
  } catch (error) {
    throw error;
  }
};

export const getCart = async (): Promise<CartItem[]> => {
  try {
    const response = await api.get('/api/cart/');
    
    // Backend returns Cart object with items array, frontend expects CartItem array
    const cart = response.data;
    if (!cart || !cart.items) {
      return [];
    }
    
    // Transform backend CartItem format to frontend CartItem format
    const transformedItems = cart.items.map((item: any) => ({
      product: {
        id: item.product_id,
        title: item.product_title,
        price: item.product_price,
        image: item.product_image,
        // Add default values for missing fields
        originalPrice: undefined,
        rating: 4.0,
        reviewCount: 0,
        category: 'Unknown',
        inStock: true,
        description: ''
      },
      quantity: item.quantity
    }));
    
    return transformedItems;
  } catch (error) {
    return [];
  }
};

export const updateCartItem = async (productId: string, quantity: number): Promise<void> => {
  try {
    await api.put(`/api/cart/update?product_id=${productId}&quantity=${quantity}`);
  } catch (error) {
    throw error;
  }
};

export const removeFromCart = async (productId: string): Promise<void> => {
  try {
    await api.delete(`/api/cart/${productId}`);
  } catch (error) {
    throw error;
  }
};

export const checkoutCart = async (): Promise<{ order_id: string; order_number: string; total: number; status: string }> => {
  try {
    const response = await api.post('/api/cart/checkout');
    return response.data.data;
  } catch (error) {
    throw error;
  }
};

/** Oportunidades de cotización - se guardan en el backend (JSONL en /tmp/opportunities.jsonl por defecto) */
export interface OpportunityCreatePayload {
  phone: string;
  company: string;
  service: string;
  contact_name?: string;
  email?: string;
  session_id?: string;
  user_message_snippet?: string;
}

export const createOpportunity = async (payload: OpportunityCreatePayload): Promise<{ id: string; message: string }> => {
  const response = await api.post('/api/opportunities', payload);
  return response.data;
};

export const getOpportunitiesSummary = async (): Promise<{ total: number }> => {
  try {
    const response = await api.get('/api/opportunities/summary');
    return response.data;
  } catch {
    return { total: 0 };
  }
};