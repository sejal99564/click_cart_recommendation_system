import Link from 'next/link';

import MarketplaceList, { type Listing } from './marketplace-list';
type Result = { status: 'ready' | 'unavailable' | 'unconfigured'; listings: Listing[] };
type Matches = {
  providers: Record<string, Result['status']>;
  matches: { title: string; brand: string; amazon_url: string; flipkart_url: string }[];
};
const api = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const labels = { amazon: 'Amazon India', flipkart: 'Flipkart' };

export default async function Marketplaces({ searchParams }: { searchParams: Promise<{ q?: string; marketplace?: string }> }) {
  const { q, marketplace } = await searchParams;
  const query = typeof q === 'string' ? q.trim().slice(0, 120) : '';
  const provider = marketplace === 'flipkart' ? 'flipkart' : 'amazon';
  const matching = marketplace === 'matches';
  const label = labels[provider];
  let results: Record<string, Result> = {};
  let matches: Matches | null = null;
  let error = false;
  try {
    const endpoint = matching ? '/api/marketplaces/matches?' + new URLSearchParams({ q: query }) :
      '/api/marketplaces?' + new URLSearchParams({ q: query, provider });
    const response = await fetch(new URL(endpoint, api),
      { cache: 'no-store', signal: AbortSignal.timeout(17000) });
    if (!response.ok) throw new Error();
    if (matching) matches = await response.json();
    else results = await response.json();
  } catch {
    error = true;
  }
  const result = results[provider];
  return <main className="shell research-page">
    <Link className="text-link" href="/">Back to demo catalog</Link>
    <h1>Marketplace search</h1>
    <form className="account-form" role="search">
      <label>Marketplace<select name="marketplace" defaultValue={matching ? 'matches' : provider}>
        {Object.entries(labels).map(([value, name]) => <option key={value} value={value}>{name}</option>)}
        <option value="matches">Find matches on both</option>
      </select></label>
      <label>Product name<input name="q" maxLength={120} defaultValue={query} required /></label>
      <button className="primary">Search marketplaces</button>
    </form>
    {error ? <p role="alert">Marketplace search is temporarily unavailable.</p> : matches ?
      <section className="section">
        <h2>Listings with the same brand and title</h2>
        <p>Check the model and variant on each retailer’s page before buying.</p>
        {Object.values(matches.providers).includes('unconfigured') ? <p>Matching requires both authorized affiliate connections.</p>
          : Object.values(matches.providers).includes('unavailable') ? <p role="status">One of the marketplaces is temporarily unavailable.</p>
          : !query ? <p>Search by the product’s full title.</p>
          : matches.matches.length === 0 ? <p>No unambiguous matches found.</p>
          : <><p>As an Amazon Associate I earn from qualifying purchases.</p>
            <div className="chat-products">{matches.matches.map(item => <div key={item.amazon_url}>
              <h3>{item.title}</h3>
              <div className="recent">
                <a className="text-link" href={item.amazon_url} target="_blank" rel="sponsored noopener noreferrer">View on Amazon India</a>
                <a className="text-link" href={item.flipkart_url} target="_blank" rel="sponsored noopener noreferrer">View on Flipkart</a>
              </div>
            </div>)}</div>
          </>}
      </section> :
      <section className="section">
        <h2>{label}</h2>
        {!result || result.status === 'unconfigured' ? <p>This marketplace requires an authorized affiliate connection.</p>
          : result.status === 'unavailable' ? <p role="status">The marketplace couldn’t return listings. Try again later.</p>
          : !query ? <p>Search by product name to see available listings.</p>
          : !result.listings.length ? <p>No matching listings.</p>
          : <><p>Prices and availability may change. The retailer’s listing determines the terms at purchase.</p>
            {provider === 'amazon' && <p>As an Amazon Associate I earn from qualifying purchases.</p>}
          </>}
      </section>}
    <MarketplaceList listings={!error && !matching && result?.status === 'ready' ? result.listings : []} />
  </main>;
}
