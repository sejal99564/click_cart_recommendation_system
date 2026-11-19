'use client';

import { ArrowDown, ArrowLeftRight, ArrowRight, Bookmark, ChevronDown, Heart, Headphones, Laptop, Search, ShoppingBag, SlidersHorizontal, Smartphone, UserRound, X } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import type { Product } from './catalog';
import RetailerLinks from './retailer-links';

const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });
const categories = [{ name: 'Laptops', Icon: Laptop }, { name: 'Phones', Icon: Smartphone }, { name: 'Audio', Icon: Headphones }];
const emptyFilters = { category: '', price: '', brand: '', rating: '', marketplace: '', offer: '', sort: '' };
type Filters = typeof emptyFilters;
type Collection = 'wishlist' | 'saved' | 'recent' | 'compare';
const emptyCollections: Record<Collection, number[]> = { wishlist: [], saved: [], recent: [], compare: [] };

function ProductPhoto({ product, sizes }: { product: Product; sizes: string }) {
  return product.data_status === 'sample' && product.id >= 1 && product.id <= 4
    ? <Image src={`/images/product-${product.id}.webp`} alt="" fill sizes={sizes} className="product-photo" />
    : <ShoppingBag size={42} aria-hidden="true" />;
}

export default function Storefront({ products, query, catalog }: { products: Product[] | null; query: string; catalog: Product[] }) {
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [showFilters, setShowFilters] = useState(true);
  const [collections, setCollections] = useState(emptyCollections);
  const [ready, setReady] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [collectionBusy, setCollectionBusy] = useState(false);
  const [collectionError, setCollectionError] = useState('');
  const [recommendations, setRecommendations] = useState<Product[]>([]);
  const [panel, setPanel] = useState<Collection | Product | null>(null);

  useEffect(() => {
    let active = true;
    const stored = { ...emptyCollections };
    try {
      const raw = JSON.parse(localStorage.getItem('shopwise-collections') || '{}');
      for (const key of Object.keys(stored) as Collection[]) {
        if (Array.isArray(raw?.[key])) stored[key] = raw[key].filter(Number.isSafeInteger);
      }
    } catch {
      // Private browsing and invalid browser data fall back to in-memory collections.
    }
    setCollections(stored);
    async function load() {
      try {
        const response = await fetch('/api/account/collections', { cache: 'no-store' });
        if (response.status === 401) return;
        if (!response.ok) throw new Error();
        let remote: typeof stored = await response.json();
        if (!active) return;
        setSignedIn(true);
        setCollections(remote);
        for (const key of Object.keys(stored) as Collection[]) {
          for (const id of [...stored[key]].reverse()) {
            if (!active) return;
            if (remote[key].includes(id) || key === 'compare' && remote.compare.length >= 4) continue;
            remote = await saveCollection(key, id, true);
            if (active) setCollections(remote);
          }
        }
        if (active) localStorage.removeItem('shopwise-collections');
      } catch {
        if (active) setCollectionError('Saved items could not be synced. Refresh to try again.');
      } finally {
        if (active) setReady(true);
      }
    }
    void load();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!ready || signedIn) return;
    try { localStorage.setItem('shopwise-collections', JSON.stringify(collections)); } catch {}
  }, [collections, ready, signedIn]);

  useEffect(() => {
    if (!ready || !signedIn || !query.trim()) return;
    void fetch('/api/account/searches', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    }).catch(() => {});
  }, [ready, signedIn, query]);

  useEffect(() => {
    if (!ready || !signedIn || query) return;
    const request = new AbortController();
    fetch('/api/account/recommendations', { signal: request.signal, cache: 'no-store' })
      .then(async response => { if (response.ok) setRecommendations(await response.json()); })
      .catch(() => {});
    return () => request.abort();
  }, [ready, signedIn, query, collections]);

  async function persist(key: Collection, id: number, selected: boolean) {
    setCollectionBusy(true);
    setCollectionError('');
    try {
      setCollections(await saveCollection(key, id, selected));
    } catch {
      setCollectionError('Could not update saved items. Refresh and try again.');
    } finally {
      setCollectionBusy(false);
    }
  }

  function toggle(key: Collection, id: number) {
    if (!ready || collectionBusy) return;
    if (signedIn) {
      void persist(key, id, !collections[key].includes(id));
      return;
    }
    setCollections(current => {
      const ids = current[key];
      if (ids.includes(id)) return { ...current, [key]: ids.filter(item => item !== id) };
      if (key === 'compare' && ids.length >= 4) return current;
      return { ...current, [key]: [id, ...ids] };
    });
  }

  function details(product: Product) {
    if (ready && !collectionBusy) {
      if (signedIn) void persist('recent', product.id, true);
      else setCollections(current => ({ ...current, recent: [product.id, ...current.recent.filter(id => id !== product.id)].slice(0, 12) }));
    }
    setPanel(product);
  }

  const marketplace = (product: Product) => product.marketplace || 'Demo catalog';
  const shown = (products || []).filter(product =>
    (!filters.category || product.category === filters.category) &&
    (!filters.price || product.price_inr <= Number(filters.price)) &&
    (!filters.brand || product.brand === filters.brand) &&
    (!filters.rating || (product.rating ?? 0) >= Number(filters.rating)) &&
    (!filters.marketplace || marketplace(product) === filters.marketplace) &&
    (!filters.offer || product.has_offer)
  );
  if (filters.sort === 'low') shown.sort((a, b) => a.price_inr - b.price_inr);
  if (filters.sort === 'high') shown.sort((a, b) => b.price_inr - a.price_inr);
  if (filters.sort === 'rating') shown.sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0));

  const collection = (key: Collection) => collections[key].flatMap(id => {
    const product = catalog.find(item => item.id === id);
    return product ? [product] : [];
  });

  const filterOptions: { key: keyof Filters; label: string; options: [string, string][] }[] = [
    { key: 'category', label: 'Category', options: categories.map(({ name }) => [name, name]) },
    { key: 'price', label: 'Price', options: [10000, 30000, 50000, 75000].map(price => [String(price), `Up to ${money.format(price)}`]) },
    { key: 'brand', label: 'Brand', options: Array.from(new Set(catalog.flatMap(product => product.brand ? [product.brand] : []))).map(brand => [brand, brand]) },
    { key: 'rating', label: 'Rating', options: [['4', '4 stars and up'], ['3', '3 stars and up']] },
    { key: 'marketplace', label: 'Marketplace', options: Array.from(new Set(catalog.map(marketplace))).map(name => [name, name]) },
    { key: 'offer', label: 'Offers', options: [['yes', 'With offers']] },
    { key: 'sort', label: 'Sort by', options: [['low', 'Lowest price'], ['high', 'Highest price'], ['rating', 'Highest rating']] },
  ];

  const panelProducts = typeof panel === 'string' ? collection(panel) : [];
  const specifications = Array.from(new Set(panelProducts.flatMap(product => Object.keys(product.specifications || {}))));

  return <>
    <div className="promo">Explore tech by category, price, and features.</div>
    <header className="site-header">
      <div className="shell nav">
        <Link href="/" className="brand"><span><ShoppingBag size={19} /></span>Shopwise AI</Link>
        <nav aria-label="Main navigation">
          <a href="#categories">Categories</a>
          <a href="#catalog">Products</a>
          <button onClick={() => setPanel('compare')}>Compare{collections.compare.length ? ` (${collections.compare.length})` : ''}</button>
          <Link href="/assistant">AI Assistant</Link>
        </nav>
        <form className="search" action="/products#catalog" role="search">
          <button aria-label="Search"><Search size={18} /></button>
          <input aria-label="Search products" name="q" defaultValue={query} maxLength={120} placeholder="Search for products" />
        </form>
        <div className="nav-actions">
          <Link className="icon-button" aria-label="Account" href="/account/profile"><UserRound size={20} /></Link>
          <button className="icon-button" aria-label="Wishlist" onClick={() => setPanel('wishlist')}><Heart size={20} /></button>
          <button className="icon-button" aria-label="Saved items" onClick={() => setPanel('saved')}><Bookmark size={20} /></button>
        </div>
      </div>
    </header>
    <main className="shell">
      <section className="hero">
        <div className="hero-copy">
          <h1>Find Your Perfect<br className="hero-break" /> Tech, Smarter.</h1>
          <p>Discover, compare, and shop confidently with AI-powered recommendations.</p>
          <a href="#catalog" className="primary">Explore Products <ArrowRight size={17} /></a>
        </div>
        <div className="hero-image"><Image src="/images/tech-hero.webp" alt="" fill priority sizes="(max-width: 760px) 100vw, 720px" /></div>
      </section>

      <section id="catalog" className="section">
        {collectionError && <p className="account-error" role="alert">{collectionError}</p>}
        <div className="filters">
          <button className="filter toggle-filters" aria-expanded={showFilters} aria-controls="product-filters" onClick={() => setShowFilters(!showFilters)}><SlidersHorizontal size={15} /> All filters</button>
          <div className="filter-options" id="product-filters" hidden={!showFilters}>
            {filterOptions.map(({ key, label, options }) => <label className="filter" key={key}>
              <select aria-label={label} value={filters[key]} disabled={!options.length} onChange={event => setFilters({ ...filters, [key]: event.target.value })}>
                <option value="">{label}</option>
                {options.map(([value, text]) => <option key={value} value={value}>{text}</option>)}
              </select>
              {key === 'sort' ? <ArrowDown size={13} /> : <ChevronDown size={13} />}
            </label>)}
          </div>
          {Object.values(filters).some(Boolean) && <button className="text-link" onClick={() => setFilters(emptyFilters)}>Clear filters</button>}
        </div>
        <div className="section-heading">
          <div><h2>{query ? `Results for “${query}”` : 'Explore products'}</h2><p>Demo catalog · Illustrative prices</p></div>
          {query && <Link className="text-link" href="/products#catalog">Clear search <X size={15} /></Link>}
        </div>

        {products === null ? <div className="empty" role="alert"><p>The catalog is temporarily unavailable.</p><a href="">Try again</a></div>
          : shown.length === 0 ? <div className="empty" role="status">No products match your search and filters.</div>
          : <div className="grid-products">{shown.map(product => <article className="product" key={product.id}>
            <div className="photo">
              <button className="photo-link" aria-label={`View ${product.title}`} onClick={() => details(product)}>
                <ProductPhoto product={product} sizes="(max-width: 560px) 45vw, (max-width: 900px) 45vw, 300px" />
              </button>
              <button className="heart icon-button" aria-label={`Wishlist: ${product.title}`} aria-pressed={collections.wishlist.includes(product.id)} disabled={!ready || collectionBusy} onClick={() => toggle('wishlist', product.id)}>
                <Heart size={17} fill={collections.wishlist.includes(product.id) ? 'currentColor' : 'none'} />
              </button>
            </div>
            <div className="product-meta">{product.brand ? `${product.brand} · ` : ''}{product.category} · {marketplace(product)}</div>
            <h3>{product.title.replace(/^Sample /, '')}</h3>
            <p className="price">{money.format(product.price_inr)} {product.rating != null && <small>{product.rating} / 5</small>}</p>
            <div className="product-actions">
              <button className="outline" onClick={() => details(product)}>View Details</button>
              <button className="icon-button outline" aria-label={`Compare: ${product.title}`} aria-pressed={collections.compare.includes(product.id)} disabled={!ready || collectionBusy || collections.compare.length >= 4 && !collections.compare.includes(product.id)} onClick={() => toggle('compare', product.id)}><ArrowLeftRight size={16} /></button>
            </div>
          </article>)}</div>}
      </section>
      <section id="categories" className="section">
        <h2>Shop by category</h2>
        <div className="category-grid">{categories.map(({ name, Icon }) => <a key={name} href="#catalog" onClick={() => { setFilters({ ...emptyFilters, category: name }); setShowFilters(true); }}><span><Icon size={24} /></span>{name}<ArrowRight size={18} /></a>)}</div>
      </section>
      {!query && recommendations.length > 0 && <section className="section">
        <h2>Recommended for you</h2>
        <div className="recent">{recommendations.map(product => <button className="outline" key={product.id} onClick={() => details(product)}>{product.title}</button>)}</div>
      </section>}
      {collection('recent').length > 0 && <section className="section">
        <h2>Recently viewed</h2>
        <div className="recent">{collection('recent').map(product => <button className="outline" key={product.id} onClick={() => details(product)}>{product.title}</button>)}</div>
      </section>}
    </main>
    <footer className="site-footer"><div className="shell"><Link href="/" className="brand"><span><ShoppingBag size={19} /></span>Shopwise AI</Link><Link href="/marketplaces">Marketplaces</Link><Link href="/dashboard">Your dashboard</Link><Link href="/research">Research results <ArrowRight size={15} /></Link></div></footer>
    {panel && <CatalogDialog close={() => setPanel(null)}>
      <h2 id="catalog-dialog-title">{typeof panel === 'object' ? panel.title : { wishlist: 'Wishlist', saved: 'Saved items', recent: 'Recently viewed', compare: 'Compare products' }[panel]}</h2>
      {typeof panel === 'object' ? <>
        <div className="photo details-photo"><ProductPhoto product={panel} sizes="480px" /></div>
        <p>{panel.description}</p><p className="price">{money.format(panel.price_inr)}</p>
        <p className="product-meta">{marketplace(panel)}{panel.data_status === 'sample' && ' · Illustrative price'}</p>
        <RetailerLinks title={panel.title} />
        <dl>{Object.entries(panel.specifications || {}).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl>
        <div className="recent">
          <button className="outline" aria-pressed={collections.saved.includes(panel.id)} disabled={!ready || collectionBusy} onClick={() => toggle('saved', panel.id)}>{collections.saved.includes(panel.id) ? 'Remove saved item' : 'Save item'}</button>
          <Link className="text-link" href={'/products/' + panel.id}>Open product page</Link>
          {panel.source_url && <a className="primary" href={panel.source_url} rel="noopener noreferrer" target="_blank">View on {marketplace(panel)} <ArrowRight size={16} /></a>}
        </div>
      </> : panel === 'compare' && panelProducts.length >= 2 ? <div className="comparison-scroll">
        <table><caption>Catalog data and illustrative prices</caption><thead><tr><th scope="col">Attribute</th>{panelProducts.map(product => <th scope="col" key={product.id}>{product.title}<button className="text-link" type="button" onClick={() => toggle('compare', product.id)}>Remove</button></th>)}</tr></thead>
          <tbody>{[
            ['Price', (product: Product) => money.format(product.price_inr)],
            ['Brand', (product: Product) => product.brand || 'Unavailable'],
            ['Category', (product: Product) => product.category],
            ['Description', (product: Product) => product.description],
            ['Rating', (product: Product) => product.rating == null ? 'Unavailable' : `${product.rating} / 5`],
            ['Marketplace', marketplace],
            ...specifications.map(name => [name, (product: Product) => product.specifications?.[name] || 'Unavailable'] as const),
          ].map(([label, value]) => <tr key={String(label)}><th scope="row">{String(label)}</th>{panelProducts.map(product => <td key={product.id}>{typeof value === 'function' && value(product)}</td>)}</tr>)}</tbody>
        </table>
        <Link className="text-link" href={'/assistant?compare=' + panelProducts.map(product => product.id).join(',')}>Ask the assistant to explain the trade-offs</Link>
      </div> : <>
        {panel === 'compare' && <p>Select two to four products using the compare button on each product card.</p>}
        {panel !== 'compare' && !panelProducts.length && <p>No products in this collection yet.</p>}
        {panelProducts.length > 0 && <ul className="collection">{panelProducts.map(product => <li key={product.id}><button className="text-link" onClick={() => details(product)}>{product.title}</button><button className="outline" onClick={() => toggle(panel, product.id)}>Remove</button></li>)}</ul>}
      </>}
    </CatalogDialog>}
  </>;
}

async function saveCollection(kind: Collection, product_id: number, selected: boolean): Promise<typeof emptyCollections> {
  const response = await fetch('/api/account/collections', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind, product_id, selected }),
  });
  if (!response.ok) throw new Error('Collection update failed');
  return response.json();
}

function CatalogDialog({ close, children }: { close: () => void; children: React.ReactNode }) {
  return <dialog className="catalog-dialog" aria-labelledby="catalog-dialog-title" ref={element => { if (element && !element.open) element.showModal(); }} onCancel={close}>
    <button className="icon-button dialog-close" onClick={close} aria-label="Close dialog"><X size={21} /></button>
    {children}
  </dialog>;
}
