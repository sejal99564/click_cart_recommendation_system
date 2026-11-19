'use client';

import { useEffect, useState } from 'react';

export type Listing = {
  id: string; title: string; brand: string | null; category: string | null;
  price: number | null; currency: string | null; availability: string | null;
  marketplace: string; source_url: string; last_updated: string;
  description?: string | null; features?: string[]; in_stock?: boolean | null;
};

type Saved = Omit<Listing, 'price' | 'currency'>;
const key = 'shopwise-marketplace-list';
const maxAge = 15 * 60 * 1000;
const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' });

function current(items: Saved[]) {
  return items.filter(item => Date.now() - Date.parse(item.last_updated) < maxAge);
}

export default function MarketplaceList({ listings }: { listings: Listing[] }) {
  const [selected, setSelected] = useState<Saved[]>([]);
  const [ready, setReady] = useState(false);
  const [compare, setCompare] = useState(false);
  const [priority, setPriority] = useState('');

  useEffect(() => {
    try {
      const value = JSON.parse(sessionStorage.getItem(key) || '[]');
      if (Array.isArray(value)) setSelected(current(value));
    } catch {}
    setReady(true);
  }, []);
  useEffect(() => {
    if (ready) {
      try { sessionStorage.setItem(key, JSON.stringify(selected)); } catch {}
    }
  }, [ready, selected]);
  useEffect(() => {
    if (!selected.length) return;
    const expiry = Math.min(...selected.map(item => Date.parse(item.last_updated) + maxAge));
    const timeout = window.setTimeout(() => setSelected(current), Math.max(0, expiry - Date.now()));
    return () => window.clearTimeout(timeout);
  }, [selected]);

  function toggle(item: Listing | Saved) {
    setSelected(items => {
      const active = current(items);
      if (active.some(product => product.source_url === item.source_url)) return active.filter(product => product.source_url !== item.source_url);
      const picked: Saved = {
        id: item.id, title: item.title, brand: item.brand, category: item.category,
        availability: item.availability, marketplace: item.marketplace, source_url: item.source_url,
        last_updated: item.last_updated, description: item.description, features: item.features, in_stock: item.in_stock,
      };
      return active.length < 4 ? [...active, picked] : active;
    });
    setCompare(false);
  }

  const term = priority.trim().toLowerCase();
  const preferred = term
    ? selected.filter(item => (item.features || []).some(feature => feature.toLowerCase().includes(term)))
    : selected.filter(item => item.in_stock === true);
  const winner = preferred.length === 1 &&
    (term || selected.every(item => typeof item.in_stock === 'boolean')) ? preferred[0] : undefined;

  return <>
    {listings.length > 0 && <div className="chat-products">{listings.map(item => {
      const saved = selected.some(product => product.source_url === item.source_url);
      return <div key={item.source_url}>
        <h3>{item.title}</h3>
        <p>{[item.brand, item.price != null && item.currency === 'INR' ? money.format(item.price) : 'Price unavailable', item.availability].filter(Boolean).join(' · ')}</p>
        {item.description && <p>{item.description}</p>}
        {(item.features || []).length > 0 && <ul>{item.features?.map((feature, index) => <li key={index}>{feature}</li>)}</ul>}
        <p>Checked {new Date(item.last_updated).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })} IST</p>
        <div className="recent">
          <a className="text-link" href={item.source_url} target="_blank" rel="sponsored noopener noreferrer">View on {item.marketplace}</a>
          <a className="text-link" href={item.source_url} target="_blank" rel="sponsored noopener noreferrer">Reviews on {item.marketplace}</a>
          <button type="button" className="outline" aria-pressed={saved} disabled={!ready || (!saved && selected.length >= 4)} onClick={() => toggle(item)}>{saved ? 'Remove from shopping list' : 'Add to shopping list'}</button>
        </div>
      </div>;
    })}</div>}
    {ready && selected.length > 0 && <section className="section">
      <h2>Marketplace shopping list</h2>
      <p>Add up to four products. Retailer details stay in this tab for up to 15 minutes.</p>
      <ul>{selected.map(item => <li key={item.source_url}>{item.title} · {item.marketplace} <button type="button" className="text-link" onClick={() => toggle(item)}>Remove</button></li>)}</ul>
      <div className="account-form">
        <label>Feature you care about (optional)<input value={priority} onChange={event => setPriority(event.target.value)} placeholder="e.g. noise cancellation" /></label>
        <button type="button" className="primary" disabled={selected.length < 2} onClick={() => { setSelected(current); setCompare(true); }}>Compare saved listings</button>
      </div>
      {compare && selected.length >= 2 && <>
        <p role="status">{winner
          ? winner.title + (term ? ' is the only listing that explicitly mentions your chosen feature.' : ' is the only listing reported in stock.')
          : term ? 'The supplied features don’t identify one clear match. Check each product’s listing.'
            : 'The available details don’t identify a clear winner. Enter a feature to narrow your choice.'}</p>
        <div className="comparison-scroll"><table>
          <thead><tr><th scope="col">Listing</th>{selected.map(item => <th scope="col" key={item.source_url}>{item.title}</th>)}</tr></thead>
          <tbody>
            <tr><th scope="row">Retailer</th>{selected.map(item => <td key={item.source_url}><a className="text-link" href={item.source_url} target="_blank" rel="sponsored noopener noreferrer">{item.marketplace}</a></td>)}</tr>
            <tr><th scope="row">Availability</th>{selected.map(item => <td key={item.source_url}>{item.availability || 'Not provided'}</td>)}</tr>
            <tr><th scope="row">Listed features</th>{selected.map(item => <td key={item.source_url}>{item.features?.join(' · ') || 'Not provided'}</td>)}</tr>
          </tbody>
        </table></div>
      </>}
    </section>}
  </>;
}
