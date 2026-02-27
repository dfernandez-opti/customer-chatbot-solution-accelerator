import React, { memo } from 'react';
import { Product } from '@/lib/types';
import { Button } from '@/components/ui/button';

interface FigmaProductCardProps {
  product: Product;
  onRequestQuote?: (product: Product) => void;
}

export const FigmaProductCard = memo(({ product, onRequestQuote }: FigmaProductCardProps) => {
  // Servicios: price 0 o isService. Sin precios, solo botón Cotizar.
  const isService = product.isService === true || product.price === 0;
  return (
    <div className="group relative flex flex-col h-full min-h-0">
      <div className="relative aspect-square overflow-hidden rounded-lg bg-muted/30 flex-shrink-0">
        <img
          src={product.image}
          alt={`${product.title} - ${product.category}`}
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
          decoding="async"
        />
      </div>
      
      <div className="flex flex-col flex-1 min-h-0 pt-2">
        <h3 className="font-medium text-foreground text-sm leading-tight group-hover:text-primary transition-colors line-clamp-2">
          {product.title}
        </h3>
        
        <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2 flex-1 mt-1 min-h-[2.5rem]">
          {product.description || `${product.category.toLowerCase()}`}
        </p>
        
        {/* Botón alineado al fondo de la tarjeta */}
        <div className="pt-2 mt-auto">
          {onRequestQuote && (
            <Button
              size="sm"
              onClick={() => onRequestQuote(product)}
              className="w-full h-8 text-xs justify-center"
            >
              Solicitar cotización
            </Button>
          )}
        </div>
      </div>
    </div>
  );
});
