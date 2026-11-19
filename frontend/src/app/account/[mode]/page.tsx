import { notFound } from 'next/navigation';
import AccountForm, { type AccountMode } from './form';

export default async function AccountPage({ params }: { params: Promise<{ mode: string }> }) {
  const { mode } = await params;
  if (!["login", "register", "forgot", "reset", "profile"].includes(mode)) notFound();
  return <AccountForm key={mode} mode={mode as AccountMode} />;
}

