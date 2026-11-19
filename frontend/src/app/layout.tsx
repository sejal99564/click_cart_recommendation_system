import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Shopwise AI | Discover and compare tech',
  description: 'Browse tech by category and budget, save your favorites, and compare products side by side.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
