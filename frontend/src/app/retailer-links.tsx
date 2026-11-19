export default function RetailerLinks({ title }: { title: string }) {
  const query = title.replace(/^Sample\s+/i, '');
  const amazon = 'https://www.amazon.in/s?' + new URLSearchParams({ k: query });
  const flipkart = 'https://www.flipkart.com/search?' + new URLSearchParams({ q: query });
  return <div className="recent" aria-label="Retailer searches">
    <a className="text-link" href={amazon} target="_blank" rel="noopener noreferrer">Search Amazon India</a>
    <a className="text-link" href={flipkart} target="_blank" rel="noopener noreferrer">Search Flipkart</a>
  </div>;
}
