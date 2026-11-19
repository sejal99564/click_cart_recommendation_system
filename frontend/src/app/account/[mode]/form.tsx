'use client';

import Link from 'next/link';
import { useEffect, useState, type FormEvent } from 'react';
import { ArrowLeft, ShoppingBag } from 'lucide-react';

export type AccountMode = 'login' | 'register' | 'forgot' | 'reset' | 'profile';
type Profile = { email: string; name: string; verified: boolean; role: string };
type Preferences = { categories: string[]; budget_inr: number | null; keep_search_history: boolean };
type Action = 'register' | 'login' | 'logout' | 'forgot' | 'reset' | 'me' | 'password' | 'preferences';
const titles: Record<AccountMode, string> = {
  login: 'Sign in', register: 'Create an account',
  forgot: 'Reset your password', reset: 'Choose a new password', profile: 'Your account',
};

async function accountRequest(action: Action, method: string, data?: object) {
  const response = await fetch('/api/account/' + action, {
    method,
    headers: data ? { 'Content-Type': 'application/json' } : undefined,
    body: data && JSON.stringify(data),
    cache: 'no-store',
  });
  const result = response.status === 204 ? null : await response.json();
  if (!response.ok) throw new Error(typeof result?.detail === 'string' ? result.detail : 'Check the information you entered.');
  return result;
}

export default function AccountForm({ mode }: { mode: AccountMode }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [token, setToken] = useState('');
  const [busy, setBusy] = useState(mode === 'profile');
  const [interactive, setInteractive] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    setInteractive(true);
    if (mode === 'reset') {
      const value = new URLSearchParams(window.location.hash.slice(1)).get('token') || '';
      if (value) {
        setToken(value);
        window.history.replaceState(null, '', window.location.pathname);
      }
    }
    if (mode === 'profile') {
      let active = true;
      Promise.all([accountRequest('me', 'GET'), accountRequest('preferences', 'GET')])
        .then(([user, saved]) => { if (active) { setProfile(user); setPreferences(saved); } })
        .catch(reason => { if (active) setError(reason.message); })
        .finally(() => { if (active) setBusy(false); });
      return () => { active = false; };
    }
  }, [mode]);

  async function submit(event: FormEvent<HTMLFormElement>, action: Action, method = 'POST') {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    if (action === 'reset') data.token = token;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const payload = action === 'preferences' ? {
        categories: new FormData(form).getAll('categories'),
        budget_inr: data.budget_inr ? Number(data.budget_inr) : null,
        keep_search_history: data.keep_search_history === 'on',
      } : data;
      const result = await accountRequest(action, method, payload);
      if (action === 'login') return window.location.assign('/account/profile');
      if (action === 'logout' || action === 'password' || method === 'DELETE') return window.location.assign('/account/login');
      if (action === 'me') setProfile(result);
      if (action === 'preferences') setPreferences(result);
      if (action === 'reset') form.reset();
      const messages: Partial<Record<Action, string>> = {
        register: 'Account created. You can now sign in.',
        forgot: 'If an eligible account exists, you’ll receive a reset link.',
        reset: 'Password updated. You can now sign in.',
        me: 'Profile saved.',
        preferences: 'Shopping preferences saved.',
      };
      setMessage(messages[action] || '');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The account request failed.');
    } finally {
      setBusy(false);
    }
  }

  return <>
    <header className="site-header"><div className="shell nav">
      <Link className="brand" href="/"><span><ShoppingBag size={19} /></span>Shopwise AI</Link>
    </div></header>
    <main className="shell account-page">
      <Link href="/" className="text-link"><ArrowLeft size={16} /> Back to catalog</Link>
      <h1>{titles[mode]}</h1>
      {error && <p className="account-error" role="alert">{error}</p>}
      {message && <p className="account-message" role="status">{message}</p>}
      {mode !== 'profile' ? <>
        {(mode !== 'reset' || token) && <form className="account-form" method="post" onSubmit={event => submit(event, mode)}>
          {mode === 'register' && <label>Name<input name="name" autoComplete="name" maxLength={100} required /></label>}
          {['register', 'login', 'forgot'].includes(mode) && <label>Email<input name="email" type="email" autoComplete="email" maxLength={254} required /></label>}
          {['register', 'login', 'reset'].includes(mode) && <label>{mode === 'reset' ? 'New password' : 'Password'}
            <input name="password" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={mode === 'login' ? 1 : 12} maxLength={128} required />
          </label>}
          {['register', 'reset'].includes(mode) && <p>Use at least 12 characters.</p>}
          <button className="primary" disabled={!interactive || busy} type="submit">{mode === 'forgot' ? 'Send reset link' : titles[mode]}</button>
        </form>}
        {mode === 'reset' && !token && <p>Open the link from your account email to continue.</p>}
        <div className="recent">
          {mode !== 'login' && <Link className="text-link" href="/account/login">Sign in</Link>}
          {mode === 'login' && <><Link className="text-link" href="/account/register">Create account</Link><Link className="text-link" href="/account/forgot">Forgot password?</Link></>}
        </div>
      </> : profile ? <>
        <p>{profile.email}</p>
        <form className="account-form" onSubmit={event => submit(event, 'me', 'PATCH')}>
          <label>Name<input name="name" autoComplete="name" required maxLength={100} defaultValue={profile.name} /></label>
          <button className="primary" disabled={busy}>Save profile</button>
        </form>
        <div className="recent"><Link className="text-link" href="/dashboard">Your dashboard</Link>
          {profile.role === 'admin' && <Link className="text-link" href="/admin">Administration</Link>}
        </div>
        {preferences && <form className="account-form" onSubmit={event => submit(event, 'preferences', 'PATCH')}>
          <h2>Shopping preferences</h2>
          <fieldset>
            <legend>Preferred categories</legend>
            {['Laptops', 'Phones', 'Audio'].map(category => <label className="checkbox-label" key={category}>
              <input type="checkbox" name="categories" value={category} defaultChecked={preferences.categories.includes(category)} />{category}
            </label>)}
          </fieldset>
          <label>Default budget (INR)<input name="budget_inr" type="number" min={0} max={10000000} defaultValue={preferences.budget_inr ?? ''} /></label>
          <label className="checkbox-label"><input name="keep_search_history" type="checkbox" defaultChecked={preferences.keep_search_history} />Keep my recent searches</label>
          <button className="outline" disabled={busy}>Save preferences</button>
        </form>}
        <form className="account-form" onSubmit={event => submit(event, 'password')}>
          <h2>Change password</h2>
          <label>Current password<input type="password" name="current_password" autoComplete="current-password" required maxLength={128} /></label>
          <label>New password<input type="password" name="password" autoComplete="new-password" required minLength={12} maxLength={128} /></label>
          <button className="outline" disabled={busy}>Change password</button>
        </form>
        <form className="account-form" onSubmit={event => submit(event, 'logout')}>
          <button className="outline" disabled={busy}>Sign out</button>
        </form>
        <details className="account-form">
          <summary>Delete account</summary>
          <form className="account-form" onSubmit={event => {
            if (window.confirm('Permanently delete your Shopwise AI account?')) void submit(event, 'me', 'DELETE');
            else event.preventDefault();
          }}>
            <label>Confirm your password<input type="password" name="current_password" autoComplete="current-password" required maxLength={128} /></label>
            <button className="outline" disabled={busy}>Delete account</button>
          </form>
        </details>
      </> : busy ? <p role="status">Loading account…</p> : <div className="recent"><Link className="text-link" href="/account/login">Sign in</Link><Link className="text-link" href="/account/register">Create account</Link></div>}
      {(!profile && !busy) && (mode === 'login' || mode === 'register' || mode === 'profile') && <div className="recent">
        <Link className="outline" href="/">Continue as guest</Link>
        <p>Browse, compare, and save products in this browser.</p>
      </div>}
    </main>
  </>;
}
