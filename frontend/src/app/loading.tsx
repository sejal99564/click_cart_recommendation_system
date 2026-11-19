export default function Loading() {
  return <main className="shell section" aria-busy="true">
    <p role="status">Loading products…</p>
    <div className="grid-products" aria-hidden="true">
      {[1, 2, 3, 4].map(id => <div className="photo" key={id} />)}
    </div>
  </main>;
}
