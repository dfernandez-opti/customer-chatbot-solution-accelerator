import React from 'react';
import { Product } from '@/lib/types';

interface ChatProductCardProps {
  product: Product;
  onRequestQuote?: (product: Product) => void;
}

export const ChatProductCard: React.FC<ChatProductCardProps> = ({
  product,
  onRequestQuote
}) => {
  return (
    <div 
      className="flex gap-4 p-4 bg-card border rounded-lg hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => onRequestQuote?.(product)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onRequestQuote?.(product)}
    >
      <div className="w-24 h-24 flex-shrink-0 rounded overflow-hidden bg-muted">
        <img
          src={product.image}
          alt={product.title}
          className="w-full h-full object-cover"
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.style.display = 'none';
            target.parentElement!.style.backgroundColor = '#e5e7eb';
          }}
        />
      </div>
      
      <div className="flex-1 min-w-0 flex flex-col justify-between">
        <div>
          <h3 className="font-semibold text-base text-foreground mb-1">
            {product.title}
          </h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {product.description}
          </p>
        </div>
        <div className="text-sm font-medium text-foreground mt-2">
          {product.isService || product.price === 0 ? 'Solicitar cotización' : `$${product.price.toFixed(2)} USD`}
        </div>
      </div>
    </div>
  );
};
