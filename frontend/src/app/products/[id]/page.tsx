import Image from 'next/image';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { getProduct } from '../../catalog';
import RetailerLinks from '../../retailer-links';

const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });
const date = new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kolkata' });

export default async function CatalogProduct({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[1-9]\d{0,9}$/.test(id) || Number(id) > 2147483647) notFound();

  let result: Awaited<ReturnType<typeof getProduct>>;
  try {
    result = await getProduct(Number(id));
  } catch {
    return <main className="shell research-page">
      <Link className="text-link" href="/products#catalog">Back to catalog</Link>
      <h1>Product temporarily unavailable</h1>
      <p role="alert">The product catalog could not be reached.</p>
    </main>;
  }
  if (result === null) notFound();
  const { product, snapshots } = result;
  return <main className="shell research-page">
    <Link className="text-link" href="/products#catalog">Back to catalog</Link>
    <h1>{product.title}</h1>
    <p>{product.category} · {product.marketplace || 'Demo catalog'}</p>
    {product.data_status === 'sample' && product.id <= 4 && <div className="photo details-photo">
      <Image fill src={`/images/product-${product.id}.webp`} className="product-photo" alt="" sizes="(max-width: 450px) 90vw, 420px" />
    </div>}
    <p>{product.description}</p>
    <p className="price">{money.format(product.price_inr)} {product.data_status === 'sample' && <small>Illustrative price</small>}</p>
    <RetailerLinks title={product.title} />
    {Object.keys(product.specifications || {}).length > 0 && <section className="section">
      <h2>Specifications</h2>
      <dl className="admin-stats">{Object.entries(product.specifications || {}).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
    </section>}
    {snapshots.length > 0 && <section className="section">
      <h2>Demo price changes</h2>
      <ul>{snapshots.map((snapshot, i) => <li key={i}>
        <time dateTime={new Date(snapshot.recorded_at * 1000).toISOString()}>{date.format(new Date(snapshot.recorded_at * 1000))} IST</time> · {money.format(snapshot.price_inr)}
      </li>)}</ul>
    </section>}
  </main>;
}
