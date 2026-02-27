import React from 'react';
import { ProductGrid } from '@/components/ProductGrid';
import { Product } from '@/lib/types';
import { useQuery } from '@tanstack/react-query';
import { getProducts } from '@/lib/api';
import { filterProducts, sortProducts } from '@/lib/data';
import { SortBy } from '@/lib/types';

interface CatalogViewProps {
  onRequestQuote?: (product: Product) => void;
}

export const CatalogView: React.FC<CatalogViewProps> = ({ onRequestQuote }) => {
  const { data: products = [], isLoading } = useQuery({
    queryKey: ['products'],
    queryFn: getProducts,
    staleTime: 5 * 60 * 1000,
  });

  const filtered = React.useMemo(() => {
    const filters = {
      category: 'All',
      minPrice: 0,
      maxPrice: 1000,
      minRating: 0,
      inStockOnly: false,
    };
    return sortProducts(
      filterProducts(products, '', filters),
      'name' as SortBy
    );
  }, [products]);

  return (
    <div className="p-6 space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-foreground">
          Service Catalog
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Servicios OPTI: SEC, ITSM, IA, BRE, CSP, Cloud and Data, ADM, SEG
        </p>
      </div>
      <ProductGrid
        products={filtered}
        isLoading={isLoading}
        onRequestQuote={onRequestQuote}
      />
    </div>
  );
};
