import Link from 'next/link';
import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import latest from '../../../public/experiment-results.json';

export const dynamic = 'force-dynamic';

const runDirectory = path.join(process.cwd(), 'public', 'experiment-runs');
const runFilename = /^\d{8}T\d{6}-[a-f0-9]{32}\.json$/;
type Report = typeof latest & { run_id?: string; completed_at?: string };
const date = new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'medium', timeZone: 'Asia/Kolkata' });

const rankingLabels = {
  precision: 'Precision@5', recall: 'Recall@5', f1: 'F1@5', ndcg: 'NDCG@5',
  map: 'MAP@5', coverage: 'Catalog coverage', diversity: 'Category diversity',
};

export default async function Evaluation({ searchParams }: { searchParams: Promise<{ run?: string | string[] }> }) {
  const { run } = await searchParams;
  const files = await readdir(runDirectory).catch((error: NodeJS.ErrnoException) => {
    if (error.code === 'ENOENT') return [];
    throw error;
  });
  const archive = await Promise.all(files.filter(name => runFilename.test(name)).sort().reverse().map(async name => {
    const report: Report = JSON.parse(await readFile(path.join(runDirectory, name), 'utf8'));
    return { name, report };
  }));
  const selected = typeof run === 'string' ? archive.find(entry => entry.report.run_id === run) : undefined;
  const report: Report = selected?.report ?? latest;
  const { recommendation, pricing } = report;
  return <main className="shell research-page">
    <Link href="/research" className="text-link">Back to research</Link>
    <h1>ML evaluation</h1>
    <p>Synthetic experiment {report.version} · Seed {report.seed} · scikit-learn {report.scikit_learn}</p>
    {run && !selected && <p role="status">That run could not be found. Showing the latest report.</p>}
    <div className="recent"><a className="outline" href={selected ? '/experiment-runs/' + selected.name : '/experiment-results.json'} download>Download results</a><Link className="outline" href="/pricing-lab">Open pricing lab</Link></div>
    {archive.length > 0 && <section className="section">
      <h2>Experiment history</h2>
      <ul>{archive.map(({ name, report: runReport }) => <li key={name}>
        <Link className="text-link" href={'/ml-evaluation?run=' + runReport.run_id} aria-current={report.run_id === runReport.run_id ? 'page' : undefined}>
          {runReport.completed_at ? date.format(new Date(runReport.completed_at)) + ' IST' : name} · Seed {runReport.seed}
        </Link>
      </li>)}</ul>
    </section>}
    <section className="section">
      <h2>Recommendation ranking</h2>
      <p>{recommendation.users} users, {recommendation.items} items, {recommendation.train_events} training events, and {recommendation.test_events} held-out events.</p>
      <p>{recommendation.split}.</p>
      <div className="comparison-scroll">
        <table>
          <thead><tr><th scope="col">Model</th>{Object.entries(rankingLabels).map(([key, label]) => <th key={key} scope="col">{label}</th>)}</tr></thead>
          <tbody>{Object.entries(recommendation.models).map(([name, metrics]) => <tr key={name}>
            <th scope="row">{name}</th>
            {(Object.keys(rankingLabels) as (keyof typeof rankingLabels)[]).map(key => <td key={key}>{metrics[key].toFixed(3)}</td>)}
          </tr>)}</tbody>
        </table>
      </div>
      <h3>NDCG@5 by model</h3>
      <div className="metric-bars">{Object.entries(recommendation.models).map(([name, metrics]) => <div key={name}>
        <label>{name} <meter min={0} max={1} value={metrics.ndcg} /> {metrics.ndcg.toFixed(3)}</label>
      </div>)}</div>
    </section>
    <section className="section">
      <h2>Merchant price prediction</h2>
      <p>{pricing.split}. Targets represent profit-maximizing prices under the synthetic demand model.</p>
      <div className="comparison-scroll">
        <table>
          <thead><tr>{['Model', 'MAE (INR)', 'MSE (INR²)', 'RMSE (INR)', 'R²', 'Mean profit (INR)'].map(label => <th key={label} scope="col">{label}</th>)}</tr></thead>
          <tbody>{Object.entries(pricing.models).map(([name, metrics]) => <tr key={name}>
            <th scope="row">{name}</th>
            {[metrics.mae, metrics.mse, metrics.rmse, metrics.r2, metrics.mean_simulated_profit].map((value, index) => <td key={index}>{value.toFixed(index === 3 ? 3 : 2)}</td>)}
          </tr>)}</tbody>
        </table>
      </div>
    </section>
  </main>;
}
