export type Product = {
  id: number;
  title: string;
  category: string;
  price_inr: number;
  description: string;
  data_status: string;
  source_url: string | null;
  brand?: string;
  marketplace?: string;
  rating?: number;
  has_offer?: boolean;
  specifications?: Record<string, string>;
};

const api = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function catalogRequest(path: string) {
  return fetch(new URL('/api/products' + path, api), { cache: 'no-store', signal: AbortSignal.timeout(5000) });
}

export async function getProducts(q = ''): Promise<Product[]> {
  const response = await catalogRequest('?' + new URLSearchParams({ q: q.slice(0, 120) }));
  if (!response.ok) throw new Error('Catalog request failed');
  return response.json();
}

type Snapshot = { price_inr: number; recorded_at: number };

export async function getProduct(id: number): Promise<{ product: Product; snapshots: Snapshot[] } | null> {
  const response = await catalogRequest('/' + id);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error('Catalog request failed');
  const product: Product = await response.json();
  const history = await catalogRequest('/' + id + '/prices').catch(() => null);
  const snapshots = history?.ok ? (await history.json()).snapshots : [];
  return { product, snapshots };
}
