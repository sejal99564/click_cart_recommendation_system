'use client';

import Link from 'next/link';
import { useEffect, useState, type FormEvent } from 'react';
import type { Product } from '../catalog';
import RetailerLinks from '../retailer-links';

type Turn = { question: string; answer: string; products: Product[] };
type Conversation = { id: string; title: string };
type Update =
  | { type: 'status' | 'error'; message: string }
  | { type: 'delta'; text: string }
  | { type: 'complete'; id: string | null; products: Product[] };
const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });

export default function Assistant() {
  const [history, setHistory] = useState<Conversation[]>([]);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [id, setId] = useState<string>();
  const [draft, setDraft] = useState('');
  const [pending, setPending] = useState<Turn>();
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [authenticated, setAuthenticated] = useState<boolean>();

  useEffect(() => {
    const compare = new URLSearchParams(window.location.search).get('compare');
    if (compare && /^\d+(,\d+){1,3}$/.test(compare)) setDraft('Compare catalog products ' + compare + ' and explain their trade-offs.');
    fetch('/api/account/conversations', { cache: 'no-store' }).then(async response => {
      if (response.status === 401) {
        setAuthenticated(false);
        try {
          const saved: unknown = JSON.parse(sessionStorage.getItem('shopwise-guest-chat') || '[]');
          if (Array.isArray(saved)) setTurns(saved);
        } catch {}
        return;
      }
      if (!response.ok) throw new Error();
      setHistory(await response.json());
      setAuthenticated(true);
    }).catch(() => setError('Conversation history is temporarily unavailable. Refresh to retry.'));
  }, []);

  useEffect(() => {
    if (authenticated === false) {
      try { sessionStorage.setItem('shopwise-guest-chat', JSON.stringify(turns.slice(-20))); } catch {}
    }
  }, [authenticated, turns]);

  async function open(conversation: string) {
    setBusy(true);
    setError('');
    try {
      const response = await fetch('/api/account/conversations?id=' + encodeURIComponent(conversation), { cache: 'no-store' });
      if (!response.ok) throw new Error();
      setTurns(await response.json());
      setId(conversation);
    } catch {
      setError('Could not open the conversation.');
    } finally {
      setBusy(false);
    }
  }

  async function removeConversation() {
    if (!id || !window.confirm('Delete this conversation?')) return;
    setBusy(true);
    setError('');
    try {
      const result = await fetch('/api/account/conversations?id=' + encodeURIComponent(id), { method: 'DELETE' });
      if (!result.ok) throw new Error();
      setHistory(items => items.filter(item => item.id !== id));
      setTurns([]);
      setId(undefined);
    } catch {
      setError('Could not delete the conversation.');
    } finally {
      setBusy(false);
    }
  }

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !draft.trim()) return;
    const question = draft.trim();
    setBusy(true);
    setError('');
    setStatus('Connecting…');
    setPending({ question, answer: '', products: [] });
    try {
      const response = await fetch('/api/account/assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, conversation_id: id, previous_question: authenticated === false ? turns.at(-1)?.question : undefined }),
      });
      if (!response.ok) {
        const result = await response.json();
        throw new Error(typeof result.detail === 'string' ? result.detail : 'Assistant request failed.');
      }
      if (!response.body) throw new Error('The assistant response is unavailable.');
      const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
      let buffer = '';
      let answer = '';
      let complete = false;
      try {
        for (;;) {
          const part = await reader.read();
          if (part.done) break;
          buffer += part.value;
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          for (const line of lines) {
            const update: Update = JSON.parse(line);
            if (update.type === 'error') throw new Error(update.message);
            if (update.type === 'status') setStatus(update.message);
            if (update.type === 'delta') {
              answer += update.text;
              setPending({ question, answer, products: [] });
              setStatus('');
            }
            if (update.type === 'complete') {
              complete = true;
              setTurns(current => [...current, { question, answer, products: update.products }]);
              const conversation = update.id;
              if (conversation && !id) setHistory(current => [{ id: conversation, title: question }, ...current]);
              if (conversation) setId(conversation);
              setDraft('');
            }
          }
        }
      } finally {
        await reader.cancel();
      }
      if (!complete) throw new Error('The response ended early. Please try again.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The assistant is temporarily unavailable.');
    } finally {
      setPending(undefined);
      setStatus('');
      setBusy(false);
    }
  }

  return <main className="shell research-page">
    <Link className="text-link" href="/">Back to catalog</Link>
    <h1>Shopping assistant</h1>
    {authenticated === false && <p>Guest chat stays in this tab. <Link className="text-link" href="/account/login">Sign in to save conversations to your account</Link>.</p>}
    {error && <p role="alert" className="account-error">{error}</p>}
    {authenticated !== undefined && <div className="assistant-layout">
      <aside aria-label="Conversation history" className="account-form">
        <button className="outline" disabled={busy} onClick={() => { setId(undefined); setTurns([]); setDraft(''); setError(''); }}>New conversation</button>
        {history.map(item => <button className="text-link conversation-title" key={item.id} aria-pressed={id === item.id} disabled={busy} onClick={() => void open(item.id)}>{item.title}</button>)}
      </aside>
      <section aria-label="Shopping conversation">
        {id && <button className="text-link" disabled={busy} onClick={() => void removeConversation()}>Delete conversation</button>}
        {!turns.length && !pending && <div>
          <p>Ask for product suggestions, compare specifications, or look for tech within your budget.</p>
          <div className="recent">{['Wireless headphones under ₹6,000', 'Laptops under ₹75,000', 'Smartphones under ₹30,000'].map(prompt =>
            <button className="outline" key={prompt} type="button" onClick={() => setDraft(prompt)}>{prompt}</button>
          )}</div>
        </div>}
        {[...turns, ...(pending ? [pending] : [])].map((turn, index) => <article className="chat-turn" key={index}>
          <p className="chat-question">{turn.question}</p>
          {turn.answer && <p className="chat-answer">{turn.answer}</p>}
          <div className="chat-products">{turn.products.map(product => <div key={product.id}>
            <Link className="text-link" href={'/products/' + product.id}>{product.title}</Link>
            <RetailerLinks title={product.title} />
            <Link className="text-link" href={'/marketplaces?q=' + encodeURIComponent(product.title.replace(/^Sample\s+/i, ''))}>Find listings to compare</Link>
            <p>{money.format(product.price_inr)} · {product.data_status === 'sample' ? 'Illustrative price' : product.marketplace}</p>
            <p>{product.description}</p>
            {product.specifications && <p>{Object.entries(product.specifications).slice(0, 3).map(([name, value]) => name + ' ' + value).join(' · ')}</p>}
          </div>)}</div>
          {turn.products.length > 1 && <button className="outline" type="button" disabled={busy} onClick={() =>
            setDraft('Compare catalog products ' + turn.products.slice(0, 4).map(product => product.id).join(',') + ' for my needs.')}>Compare these options</button>}
        </article>)}
        {status && <p role="status">{status}</p>}
        <form className="account-form" onSubmit={send}>
          <label>Your question<textarea value={draft} onChange={event => setDraft(event.target.value)} maxLength={2000} required rows={3} /></label>
          <button className="primary" disabled={busy || !draft.trim()}>Send</button>
        </form>
      </section>
    </div>}
  </main>;
}
