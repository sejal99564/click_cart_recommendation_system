'use client';

import { useState, type FormEvent } from 'react';
import type { Product } from '../catalog';

export default function CatalogEditor({ products }: { products: Product[] }) {
  const [items, setItems] = useState(products);
  const [selected, setSelected] = useState(products[0]?.id);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const product = items.find(item => item.id === selected);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!product) return;
    const data = new FormData(event.currentTarget);
    const changes = { id: product.id, price_inr: Number(data.get('price_inr')), description: String(data.get('description')).trim() };
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const response = await fetch('/api/account/admin', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(changes),
      });
      if (!response.ok) throw new Error();
      setItems(current => current.map(item => item.id === changes.id ? { ...item, ...changes } : item));
      setNotice('Demo listing saved.');
    } catch {
      setError('The listing could not be saved.');
    } finally {
      setBusy(false);
    }
  }

  return <section className="section">
    <h2>Demo catalog management</h2>
    {!product ? <p>No demo products available.</p> : <form key={product.id} className="account-form" onSubmit={save}>
      <label>Product<select value={selected} disabled={busy} onChange={event => { setSelected(Number(event.target.value)); setError(''); setNotice(''); }}>
        {items.map(item => <option value={item.id} key={item.id}>{item.title}</option>)}
      </select></label>
      <label>Illustrative price (INR)<input name="price_inr" type="number" min={0} max={10000000} defaultValue={product.price_inr} required /></label>
      <label>Description<textarea name="description" defaultValue={product.description} maxLength={1200} required /></label>
      <button className="primary" disabled={busy}>Save product</button>
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
    </form>}
  </section>;
}
