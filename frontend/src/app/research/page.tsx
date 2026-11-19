import Link from 'next/link';
import { ArrowLeft, ShoppingBag } from 'lucide-react';

const results = [
  ['Logistic regression', 89.4, 88.7, 87.9, 88.3],
  ['Random forest', 93.1, 92.6, 92.2, 92.4],
  ['XGBoost', 95.0, 94.5, 94.1, 94.3],
  ['Proposed hybrid AI model', 96.7, 96.2, 95.9, 96.0],
] as const;

export default function Research() {
  return <>
    <header className="site-header"><div className="shell nav">
      <Link className="brand" href="/"><span><ShoppingBag size={19} /></span>Shopwise AI</Link>
    </div></header>
    <main className="shell research-page">
      <Link href="/" className="text-link"><ArrowLeft size={16} /> Back to catalog</Link>
      <h1>Retail AI research</h1>
      <p>The source paper combines personalized recommendations, conversational support, and dynamic pricing in one retail system.</p>
      <section className="section">
        <h2>Original paper results</h2>
        <div className="comparison-scroll"><table>
          <caption>Table I, page 5 of Artificial Intelligence in Retail and E-commerce: Transforming Customer Experience</caption>
          <thead><tr>{['Model', 'Accuracy', 'Precision', 'Recall', 'F1'].map(label => <th key={label} scope="col">{label}</th>)}</tr></thead>
          <tbody>{results.map(([model, ...metrics]) => <tr key={model}>
            <th scope="row">{model}</th>
            {metrics.map((metric, index) => <td key={index}>{metric.toFixed(1)}%</td>)}
          </tr>)}</tbody>
        </table></div>
      </section>
      <section className="section"><h2>Reproduced results</h2>
        <p>Reproduction is pending. The paper omits the dataset, label and split definitions, hybrid model configuration, and metric averaging rules.</p>
      </section>
      <section className="section"><h2>New experiments</h2>
        <p>Shopwise AI evaluated recommendation and pricing baselines on reproducible synthetic datasets.</p>
        <Link className="text-link" href="/ml-evaluation">View synthetic experiment results</Link>
      </section>
    </main>
  </>;
}
