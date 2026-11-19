import { getProducts, type Product } from './catalog';
import Storefront from './storefront';

export default async function Home({ searchParams }: { searchParams: Promise<{ q?: string | string[] }> }) {
  const { q } = await searchParams;
  const query = (typeof q === 'string' ? q : '').slice(0, 120);
  let products: Product[] | null = null;
  let catalog: Product[] = [];
  try {
    if (query) {
      [products, catalog] = await Promise.all([getProducts(query), getProducts()]);
    } else {
      products = catalog = await getProducts();
    }
  } catch {
    // The storefront renders the catalog error and a retry link.
  }
  return <Storefront products={products} query={query} catalog={catalog} />;
}

