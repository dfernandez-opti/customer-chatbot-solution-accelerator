import React from 'react';
import { Text } from '@fluentui/react-components';
import { ProductGrid } from '@/components/ProductGrid';
import { Product } from '@/lib/types';

interface MainContentProps {
  children?: React.ReactNode;
  products?: Product[];
  isLoading?: boolean;
  onRequestQuote?: (product: Product) => void;
}

export const MainContent: React.FC<MainContentProps> = ({
  children,
  products = [],
  isLoading = false,
  onRequestQuote
}) => {
  return (
    <div className="h-full flex flex-col min-h-0">
      {/* Products Header - Products title and result count */}
      <div className="p-4 pt-6">
        <div className="flex items-center justify-between">
          <Text size={500} weight="semibold">Nuestros Servicios</Text>
          <Text size={300} className="text-muted-foreground">
            Mostrando {products.length} servicios
          </Text>
        </div>
      </div>
      
      {/* Products Content - padding extra abajo para ver última fila de cards */}
      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-4 pt-0 pb-16">
        <div className="max-w-full pb-16">
          {children || (
            <ProductGrid
              products={products}
              isLoading={isLoading}
              onRequestQuote={onRequestQuote}
            />
          )}
        </div>
      </div>
    </div>
  );
};
