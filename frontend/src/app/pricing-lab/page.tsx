'use client';

import Link from 'next/link';
import { useState } from 'react';
import report from '../../../public/experiment-results.json';

const settings = [
  { label: 'Previous merchant price (INR)', value: 9100, min: 5000, max: 12000, step: 100 },
  { label: 'Demand index', value: 0.55, min: 0.15, max: 0.95, step: 0.05 },
  { label: 'Inventory units', value: 40, min: 8, max: 79, step: 1 },
  { label: 'Seasonal index', value: 0, min: -1, max: 1, step: 0.1 },
  { label: 'Simulated competitor price (INR)', value: 9100, min: 6000, max: 12000, step: 100 },
  { label: 'Unit cost (INR)', value: 3700, min: 3000, max: 4500, step: 100 },
];
const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });

export default function PricingLab() {
  const [values, setValues] = useState(settings.map(setting => setting.value));
  const { ridge } = report.pricing;
  const estimate = ridge.intercept + ridge.coefficients.reduce((sum, coefficient, index) => sum + coefficient * values[index], 0);
  const price = Math.min(ridge.maximum, Math.max(ridge.minimum, estimate));

  return <main className="shell research-page">
    <Link className="text-link" href="/ml-evaluation">Back to evaluation</Link>
    <h1>Pricing lab</h1>
    <p>Change the inputs to see a ridge regression estimate for a simulated merchant. The model was trained on synthetic price and demand scenarios.</p>
    <div className="admin-stats">
      <div><p>Simulated price estimate</p><output className="lab-price" aria-live="polite">{money.format(price)}</output></div>
    </div>
    <div className="account-form pricing-controls">
      {settings.map(({ label, min, max, step }, index) => <label key={label}>
        {label} <span>{values[index]}</span>
        <input type="range" min={min} max={max} step={step} value={values[index]} onChange={event => {
          const value = Number(event.target.value);
          setValues(current => current.map((existing, position) => position === index ? value : existing));
        }} />
      </label>)}
    </div>
  </main>;
}
