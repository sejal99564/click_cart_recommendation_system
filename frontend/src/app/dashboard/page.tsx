import Link from 'next/link';
import { headers } from 'next/headers';
import { getProducts } from '../catalog';

const api = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default async function Dashboard() {
  const cookie = (await headers()).get('cookie') || '';
  let collections: Record<string, number[]> = {};
  let products: Awaited<ReturnType<typeof getProducts>> = [];
  let saved = { categories: [] as string[], budget_inr: null as number | null, keep_search_history: false };
  let searches: string[] = [];
  let recommendations: Awaited<ReturnType<typeof getProducts>> = [];
  let error = '';
  try {
    const accountData = (route: string) => fetch(new URL('/api/auth/' + route, api), {
      headers: { cookie }, cache: 'no-store', signal: AbortSignal.timeout(5000),
    });
    const response = await accountData('collections');
    if (response.status === 401) return <main className="shell account-page"><h1>Your dashboard</h1><Link className="primary" href="/account/login">Sign in</Link></main>;
    if (!response.ok) throw new Error();
    const [preferences, history, suggested] = await Promise.all([accountData('preferences'), accountData('searches'), accountData('recommendations')]);
    if (!preferences.ok || !history.ok || !suggested.ok) throw new Error();
    [collections, products, saved, searches, recommendations] = await Promise.all([response.json(), getProducts(), preferences.json(), history.json(), suggested.json()]);
  } catch {
    error = 'Your collections are temporarily unavailable.';
  }
  const sections = { wishlist: 'Wishlist', saved: 'Saved items', recent: 'Recently viewed', compare: 'Comparison list' };
  return <main className="shell research-page">
    <Link className="text-link" href="/">Back to catalog</Link>
    <h1>Your dashboard</h1>
    <div className="recent"><Link className="outline" href="/account/profile">Profile</Link><Link className="outline" href="/assistant">Shopping conversations</Link></div>
    {error ? <p role="alert">{error}</p> : <>
      {Object.entries(sections).map(([key, label]) => <section className="section" key={key}>
        <h2>{label}</h2>
        {collections[key]?.length ? <ul>{collections[key].map(id => {
          const product = products.find(item => item.id === id);
          return product && <li key={id}><Link className="text-link" href={'/products?q=' + encodeURIComponent(product.title) + '#catalog'}>{product.title}</Link></li>;
        })}</ul> : <p>No products yet.</p>}
      </section>)}
      {recommendations.length > 0 && <section className="section">
        <h2>Recommended for you</h2>
        <ul>{recommendations.map(product => <li key={product.id}><Link className="text-link" href={'/products?q=' + encodeURIComponent(product.title) + '#catalog'}>{product.title}</Link></li>)}</ul>
      </section>}
      {saved.keep_search_history && <section className="section">
        <h2>Recent searches</h2>
        {searches.length ? <ul>{searches.map((query, index) => <li key={index}>
          <Link className="text-link" href={'/products?q=' + encodeURIComponent(query) + '#catalog'}>{query}</Link>
        </li>)}</ul> : <p>Your saved searches will appear here.</p>}
      </section>}
    </>}
  </main>;
}
