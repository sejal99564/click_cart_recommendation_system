import Link from 'next/link';
import { headers } from 'next/headers';
import { getProducts, type Product } from '../catalog';
import CatalogEditor from './catalog-editor';

const api = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const labels: Record<string, string> = {
  users: 'Registered users', verified_users: 'Verified users', catalog_products: 'Catalog products',
  collection_items: 'Collection activity', chat_turns: 'Completed assistant turns',
  input_tokens: 'Assistant input tokens', output_tokens: 'Assistant output tokens',
  price_snapshots: 'Demo price changes', catalog_audit_events: 'Catalog audit events',
  amazon: 'Amazon India connection', flipkart: 'Flipkart connection', database: 'Database',
  estimated_cost: 'Estimated assistant usage (USD)',
};

export default async function Admin() {
  let stats: Record<string, number | string> | null = null;
  let products: Product[] | null = null;
  let error = 'The admin dashboard is temporarily unavailable.';
  try {
    const cookie = (await headers()).get('cookie') || '';
    const result = await fetch(new URL('/api/auth/admin', api), {
      headers: { cookie }, cache: 'no-store', signal: AbortSignal.timeout(5000),
    });
    if (result.ok) [stats, products] = await Promise.all([result.json(), getProducts()]);
    if (result.status === 401 || result.status === 403) error = 'Sign in with an administrator account to view this page.';
  } catch {}
  return <main className="shell research-page">
    <Link className="text-link" href="/dashboard">Back to dashboard</Link>
    <h1>Administration</h1>
    {stats ? <><dl className="admin-stats">{Object.entries(stats).map(([key, value]) => <div key={key}>
      <dt>{labels[key] || key}</dt><dd>{value}</dd>
    </div>)}</dl>
      {products && <CatalogEditor products={products.filter(product => product.data_status === 'sample')} />}
    </> : <p role="alert">{error}</p>}
  </main>;
}
